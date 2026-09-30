import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from tools.omr.staged import record_io
from tools.omr.preprocessing import render_page

PDF = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
REC = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a212d008990c6b49a/out/2.40/litolff-p3-evaluate.json"
OUTDIR = Path("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a212d008990c6b49a/benchmarks/omr-notehead-precision-2026-09/out/print/same-side-second-survey-2.40")
OUTDIR.mkdir(parents=True, exist_ok=True)

d = record_io.load_record(REC)
rec = d["record"]
obs = rec["observations"]
box_by_subj = {o["subject"]: o for o in obs if o["quantity"] == "glyph_box"}
staff_lines_by = {o["subject"]: o["value"] for o in obs if o["quantity"] == "staff_lines"}
cell_box_by = {o["subject"]: o["value"] for o in obs if o["quantity"] == "cell_box"}

SAMPLES = [
    ("S1", "cell/3/0/0/2", ["glyph/3/0/0/2/4", "glyph/3/0/0/2/9"]),
    ("S2", "cell/3/0/9/0", ["glyph/3/0/9/0/7", "glyph/3/0/9/0/9", "glyph/3/0/9/0/12"]),
    ("S3", "cell/3/1/2/9", ["glyph/3/1/2/9/2", "glyph/3/1/2/9/3", "glyph/3/1/2/9/5"]),
    ("S4", "cell/3/1/4/12", ["glyph/3/1/4/12/2", "glyph/3/1/4/12/3"]),
    ("S5", "cell/3/1/7/17", ["glyph/3/1/7/17/3", "glyph/3/1/7/17/5", "glyph/3/1/7/17/6"]),
    ("S6", "cell/3/0/8/7", ["glyph/3/0/8/7/8", "glyph/3/0/8/7/9"]),
]

nh_verdict = {v["subject"]: v for v in rec["verdicts"] if v["quantity"] == "notehead_is_not_a_notehead"}
pitch_v = {v["subject"]: v for v in rec["verdicts"] if v["quantity"] == "pitch"}

print("rendering page 3")
pi = render_page(PDF, 3, dpi=600)
arr = getattr(pi, "rgb", None)
if arr is None:
    arr = getattr(pi, "binary")
arr_np = np.asarray(arr)
base_rgb = np.stack([arr_np] * 3, axis=-1) if arr_np.ndim == 2 else arr_np
img_full = Image.fromarray(base_rgb.astype(np.uint8)).convert("RGB")

def staff_of_cell(cell_key):
    parts = cell_key.split("/")
    return "/".join(["staff"] + parts[1:4])

manifest = []
for tag, cell, subjs in SAMPLES:
    cell_box = cell_box_by.get(cell)
    st = staff_of_cell(cell)
    line_ys = staff_lines_by.get(st) or []
    if cell_box is None:
        print("NO CELL BOX", cell)
        continue
    pad = 60
    cx0 = max(0, int(cell_box[0] - pad)); cx1 = min(img_full.width, int(cell_box[2] + pad))
    cy0 = max(0, int(cell_box[1] - pad)); cy1 = min(img_full.height, int(cell_box[3] + pad))
    if line_ys:
        cy0 = min(cy0, int(min(line_ys) - 20))
        cy1 = max(cy1, int(max(line_ys) + 20))
    crop = img_full.crop((cx0, cy0, cx1, cy1)).convert("RGB")
    scale = 2.0
    crop = crop.resize((int(crop.width * scale), int(crop.height * scale)), Image.LANCZOS)
    draw = ImageDraw.Draw(crop)

    def to_crop(px, py):
        return ((px - cx0) * scale, (py - cy0) * scale)

    for ly in line_ys:
        x0c, y0c = to_crop(cx0, ly); x1c, y1c = to_crop(cx1, ly)
        draw.line([(x0c, y0c), (x1c, y1c)], fill=(30, 110, 220), width=1)

    labels = []
    for s in subjs:
        o = box_by_subj.get(s)
        if o is None:
            continue
        box = o["detail"].get("bbox_page_px")
        if not box:
            continue
        v = nh_verdict.get(s)
        refused = v.get("value") if v else None
        reason = (v or {}).get("reason")
        p = pitch_v.get(s)
        pitch = p["value"] if p else "?"
        color = (220, 20, 20) if refused else (20, 160, 20)
        bx0, by0 = to_crop(box[0], box[1]); bx1, by1 = to_crop(box[2], box[3])
        draw.rectangle([bx0, by0, bx1, by1], outline=color, width=3)
        label = f"{pitch}{' REFUSED:' + str(reason) if refused else ''}"
        draw.text((bx0, max(0, by0 - 14)), label, fill=color)
        labels.append(label)

    draw.rectangle([0, 0, crop.width, 20], fill=(255, 255, 255))
    draw.text((4, 4), f"{tag} {cell} " + " | ".join(labels), fill=(0, 0, 0))
    fname = f"{tag}-{cell.replace('/', '-')}.png"
    crop.save(OUTDIR / fname)
    manifest.append(dict(tag=tag, cell=cell, file=fname, subjects=subjs))
    print(tag, fname)

json.dump(manifest, open(OUTDIR / "manifest.json", "w"), indent=1)
