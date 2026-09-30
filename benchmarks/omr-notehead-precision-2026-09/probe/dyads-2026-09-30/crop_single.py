import json, pickle, sys
from pathlib import Path
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a0af1ab57763853aa")
import numpy as np
from PIL import Image, ImageDraw

from tools.omr.preprocessing import render_page

PDF = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
PAGE_IDX = 3
OUTDIR = Path("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a0af1ab57763853aa/out/print/dyads")
OUTDIR.mkdir(parents=True, exist_ok=True)

PKL = "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-acceptance-measure-notehead-box-e75821/2c34bf69-0e00-4748-a821-6f4862e751be/scratchpad/page3.pkl"
d = pickle.load(open(PKL, "rb"))
gbox = {o["subject"]: o for o in d["by_q_page"]["glyph_box"]}
staff_lines = {o["subject"]: o["value"] for o in d["by_q_page"]["staff_lines"]}
staff_spacing = {o["subject"]: o["value"] for o in d["by_q_page"]["staff_spacing"]}

def staff_of(cell_key):
    parts = cell_key.split("/")
    return "/".join(["staff"] + parts[1:4])

print("rendering page", PAGE_IDX)
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

def row_ink_profile(px0, py0, px1, py1, pad=0):
    x0, y0 = int(px0), int(py0 - pad)
    x1, y1 = int(px1), int(py1 + pad)
    x0 = max(0, x0); y0 = max(0, y0)
    x1 = min(gray.shape[1], x1); y1 = min(gray.shape[0], y1)
    region = gray[y0:y1, x0:x1]
    dark_frac_per_row = (region < 150).mean(axis=1)
    return dark_frac_per_row.tolist()

def crop_single(subj, out_name, annotate_text):
    box = gbox[subj]["detail"]["bbox_page_px"]
    cellkey = "/".join(["cell"] + subj.split("/")[1:5])
    stkey = staff_of(cellkey)
    line_ys = staff_lines.get(stkey)
    ss_page = staff_spacing.get(stkey, 60.0)
    pad_x = 3.0 * ss_page
    pad_y = 2.0 * ss_page
    cx0 = max(0, int(box[0] - pad_x)); cx1 = min(img_full.width, int(box[2] + pad_x))
    cy0 = max(0, int(box[1] - pad_y)); cy1 = min(img_full.height, int(box[3] + pad_y))
    if line_ys:
        cy0 = min(cy0, int(min(line_ys) - 10))
        cy1 = max(cy1, int(max(line_ys) + 10))
    crop = img_full.crop((cx0, cy0, cx1, cy1)).convert("RGB")
    headw = box[2] - box[0]
    scale = max(1.0, 70.0 / max(1.0, headw))
    if scale > 1.0:
        crop = crop.resize((int(crop.width*scale), int(crop.height*scale)), Image.LANCZOS)
    draw = ImageDraw.Draw(crop)
    def to_crop(px, py):
        return ((px - cx0) * scale, (py - cy0) * scale)
    if line_ys:
        for ly in line_ys:
            x0c, y0c = to_crop(cx0, ly)
            x1c, y1c = to_crop(cx1, ly)
            draw.line([(x0c, y0c), (x1c, y1c)], fill=(30, 110, 220), width=1)
    bx0, by0 = to_crop(box[0], box[1]); bx1, by1 = to_crop(box[2], box[3])
    draw.rectangle([bx0, by0, bx1, by1], outline=(220, 20, 20), width=2)
    L = max(8.0, 0.2*(bx1-bx0))
    for (x, y, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1), (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
        draw.line([(x, y), (x + dx * L, y)], fill=(220, 20, 20), width=3)
        draw.line([(x, y), (x, y + dy * L)], fill=(220, 20, 20), width=3)

    profile = row_ink_profile(*box)
    ink_pct = float(np.mean(profile)) * 100 if profile else None
    # detect a "waist": a local minimum row of dark-frac well below the
    # neighbourhood max, inside the box -- evidence of two lobes.
    waist = None
    if profile and len(profile) > 6:
        arrp = np.array(profile)
        mid = arrp[len(arrp)//4: 3*len(arrp)//4]
        if len(mid) > 2:
            waist = float(mid.min())
    draw.rectangle([0, 0, crop.width, 20], fill=(255, 255, 255))
    draw.text((4, 4), f"{annotate_text} ink%={ink_pct:.0f} waist={waist}", fill=(0, 0, 0))
    crop.save(OUTDIR / out_name)
    return dict(ink_pct=ink_pct, waist=waist, profile=profile)

if __name__ == "__main__":
    cands = json.load(open("/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-acceptance-measure-notehead-box-e75821/2c34bf69-0e00-4748-a821-6f4862e751be/scratchpad/pop_b.json"))
    cands.sort(key=lambda c: -c["height_sp"])
    sample = cands[:20]
    out = []
    for i, c in enumerate(sample):
        tag = f"B{i+1:02d}"
        fname = f"{tag}-{c['subject'].replace('/','-')}.png"
        text = f"{tag} {c['cls']} h={c['height_sp']:.2f}sp {'REFUSED:'+str(c['reason']) if c['refused'] else 'stands'}"
        r = crop_single(c["subject"], fname, text)
        out.append(dict(tag=tag, file=fname, **c, **{k: v for k, v in r.items() if k != 'profile'}))
        print(tag, fname, r["ink_pct"], r["waist"])
    json.dump(out, open(OUTDIR / "manifest-b.json", "w"), indent=1, default=str)
