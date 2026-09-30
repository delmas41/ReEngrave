"""Render print crops for a list of judged pairs: staff lines drawn, each
detector box in its own colour, corner brackets on both subjects, and a
numeric ink-percent measured inside each box before any verdict is written.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a0af1ab57763853aa")
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from tools.omr.preprocessing import render_page

PDF = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
PAGE_IDX = 3  # pdf index used throughout the record's subject keys
OUTDIR = Path("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a0af1ab57763853aa/out/print/dyads")
OUTDIR.mkdir(parents=True, exist_ok=True)

import pickle
PKL = "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-acceptance-measure-notehead-box-e75821/2c34bf69-0e00-4748-a821-6f4862e751be/scratchpad/page3.pkl"
d = pickle.load(open(PKL, "rb"))
gbox = {o["subject"]: o for o in d["by_q_page"]["glyph_box"]}
staff_lines = {o["subject"]: o["value"] for o in d["by_q_page"]["staff_lines"]}
staff_spacing = {o["subject"]: o["value"] for o in d["by_q_page"]["staff_spacing"]}
cell_ss = {o["subject"]: o["value"] for o in d["by_q_page"]["cell_staff_space"]}
cellbox = {o["subject"]: o["value"] for o in d["by_q_page"]["cell_box"]}
from collections import defaultdict as _dd
stems_by_cell_canon = _dd(list)
for o in d["by_q_page"]["stem"]:
    stems_by_cell_canon[o["subject"]].append(o["value"])  # [x,y,w,h] canonical

def staff_of(cell_key):
    parts = cell_key.split("/")  # cell,page,sys,staff,cell
    return "/".join(["staff"] + parts[1:4])

# Fit per-cell canonical->page affine (up, x0_page, y0_page) from every
# glyph_box row we already have in that cell (least-squares over all of
# them, robust to any one glyph's rounding).
_cell_affine_cache = {}
def cell_affine(cellkey):
    if cellkey in _cell_affine_cache:
        return _cell_affine_cache[cellkey]
    xs_canon, xs_page, ys_canon, ys_page = [], [], [], []
    prefix = cellkey + "/"
    for subj, o in gbox.items():
        if not subj.startswith(prefix):
            continue
        _, xc, yc, wc, hc = o["value"]
        bpp = o["detail"].get("bbox_page_px")
        if not bpp:
            continue
        xs_canon.append(xc); xs_page.append(bpp[0])
        ys_canon.append(yc); ys_page.append(bpp[1])
    if len(xs_canon) < 2:
        _cell_affine_cache[cellkey] = None
        return None
    import numpy as _np
    # page_x = x0 + xc/up  =>  page_x = x0 + xc*(1/up); linear fit
    A = _np.vstack([_np.array(xs_canon), _np.ones(len(xs_canon))]).T
    (inv_up_x, x0p), *_ = _np.linalg.lstsq(A, _np.array(xs_page), rcond=None)
    A2 = _np.vstack([_np.array(ys_canon), _np.ones(len(ys_canon))]).T
    (inv_up_y, y0p), *_ = _np.linalg.lstsq(A2, _np.array(ys_page), rcond=None)
    result = dict(inv_up_x=float(inv_up_x), x0p=float(x0p),
                  inv_up_y=float(inv_up_y), y0p=float(y0p))
    _cell_affine_cache[cellkey] = result
    return result

def stem_boxes_page(cellkey):
    aff = cell_affine(cellkey)
    if aff is None:
        return []
    out = []
    for (x, y, w, h) in stems_by_cell_canon.get(cellkey, []):
        px0 = aff["x0p"] + x * aff["inv_up_x"]
        px1 = aff["x0p"] + (x + w) * aff["inv_up_x"]
        py0 = aff["y0p"] + y * aff["inv_up_y"]
        py1 = aff["y0p"] + (y + h) * aff["inv_up_y"]
        out.append((px0, py0, px1, py1))
    return out

print("rendering page", PAGE_IDX, "at 600dpi ...")
pi = render_page(PDF, PAGE_IDX, dpi=600)
arr = getattr(pi, "rgb", None)
if arr is None:
    arr = getattr(pi, "binary")
arr_np = np.asarray(arr)
if arr_np.ndim == 2:
    gray = arr_np.astype(float)
    base_rgb = np.stack([arr_np]*3, axis=-1)
else:
    gray = arr_np.mean(axis=2)
    base_rgb = arr_np
img_full = Image.fromarray(base_rgb.astype(np.uint8)).convert("RGB")
print("page size", img_full.size)

def ink_pct(px0, py0, px1, py1):
    x0, y0, x1, y1 = int(px0), int(py0), int(px1), int(py1)
    x0 = max(0, x0); y0 = max(0, y0)
    x1 = min(gray.shape[1], x1); y1 = min(gray.shape[0], y1)
    if x1 <= x0 or y1 <= y0:
        return None
    region = gray[y0:y1, x0:x1]
    # "dark" = below 128 on a 0-255 grayscale (bitonal-ish scan)
    dark = (region < 150).mean()
    return float(dark) * 100.0

def draw_corner_bracket(draw, box, color, L=None, width=3):
    x0, y0, x1, y1 = box
    if L is None:
        L = max(8.0, 0.22 * (x1 - x0))
    for (x, y, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1),
                           (x0, y1, 1, -1), (x1, y1, -1, -1)):
        draw.line([(x, y), (x + dx * L, y)], fill=color, width=width)
        draw.line([(x, y), (x, y + dy * L)], fill=color, width=width)

def crop_pair(rec, out_name, subject1, subject2, annotate_text):
    s1_box = gbox[subject1]["detail"]["bbox_page_px"]
    s2_box = gbox[subject2]["detail"]["bbox_page_px"]
    cellkey = rec["cell"]
    stkey = staff_of(cellkey)
    line_ys = staff_lines.get(stkey)
    ss_page = staff_spacing.get(stkey, 60.0)
    all_x = [s1_box[0], s1_box[2], s2_box[0], s2_box[2]]
    all_y = [s1_box[1], s1_box[3], s2_box[1], s2_box[3]]
    pad_x = 3.0 * ss_page
    pad_y = 3.0 * ss_page
    cx0 = max(0, int(min(all_x) - pad_x))
    cx1 = min(img_full.width, int(max(all_x) + pad_x))
    cy0 = max(0, int(min(all_y) - pad_y))
    cy1 = min(img_full.height, int(max(all_y) + pad_y))
    if line_ys:
        cy0 = min(cy0, int(min(line_ys) - 10))
        cy1 = max(cy1, int(max(line_ys) + 10))
    crop = img_full.crop((cx0, cy0, cx1, cy1)).convert("RGB")
    # upscale so a head is >=60px wide
    headw = s1_box[2] - s1_box[0]
    scale = max(1.0, 70.0 / max(1.0, headw))
    if scale > 1.0:
        crop = crop.resize((int(crop.width*scale), int(crop.height*scale)), Image.LANCZOS)
    draw = ImageDraw.Draw(crop)

    def to_crop(px, py):
        return ((px - cx0) * scale, (py - cy0) * scale)

    # staff lines, blue
    if line_ys:
        for ly in line_ys:
            x0c, y0c = to_crop(cx0, ly)
            x1c, y1c = to_crop(cx1, ly)
            draw.line([(x0c, y0c), (x1c, y1c)], fill=(30, 110, 220), width=1)

    # stems, purple/orange dashed-ish (drawn as thin rectangles)
    for (spx0, spy0, spx1, spy1) in stem_boxes_page(cellkey):
        bx0, by0 = to_crop(spx0, spy0)
        bx1, by1 = to_crop(spx1, spy1)
        draw.rectangle([bx0, by0, bx1, by1], outline=(160, 0, 200), width=2)

    colors = {subject1: (220, 20, 20), subject2: (20, 160, 60)}
    ink_pcts = {}
    for subj, box in ((subject1, s1_box), (subject2, s2_box)):
        ink_pcts[subj] = ink_pct(*box)
        bx0, by0 = to_crop(box[0], box[1])
        bx1, by1 = to_crop(box[2], box[3])
        draw.rectangle([bx0, by0, bx1, by1], outline=colors[subj], width=2)
        draw_corner_bracket(draw, (bx0, by0, bx1, by1), colors[subj])

    label = f"{annotate_text} | ink%: red={ink_pcts[subject1]:.0f} green={ink_pcts[subject2]:.0f} | stem=purple"
    draw.rectangle([0, 0, crop.width, 20], fill=(255, 255, 255))
    draw.text((4, 4), label, fill=(0, 0, 0))
    crop.save(OUTDIR / out_name)
    return ink_pcts

if __name__ == "__main__":
    sample = json.load(open("/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-acceptance-measure-notehead-box-e75821/2c34bf69-0e00-4748-a821-6f4862e751be/scratchpad/sample_a.json"))
    results = []
    for i, p in enumerate(sample):
        tag = f"A{i+1:02d}"
        fname = f"{tag}-{p['cell'].replace('/','-')}-{p['g1'].split('/')[-1]}-{p['g2'].split('/')[-1]}.png"
        text = f"{tag} {p['cls']} dy={p['dy_spaces']:.2f}sp {'overlap' if p['has_overlap'] else 'no_overlap'} side={p['stem_side']} {'REFUSED' if (p['refused1'] or p['refused2']) else 'stands'}"
        ink = crop_pair(p, fname, p["g1"], p["g2"], text)
        results.append(dict(tag=tag, file=fname, ink=ink, **p))
        print(tag, fname, ink)
    json.dump(results, open(OUTDIR / "manifest-a.json", "w"), indent=1, default=str)
