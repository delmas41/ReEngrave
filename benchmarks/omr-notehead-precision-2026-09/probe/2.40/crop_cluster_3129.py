import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from tools.omr.staged import record_io
from tools.omr.preprocessing import render_page

PDF = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
REC = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a212d008990c6b49a/out/2.40/litolff-p3-evaluate-v4.json"
OUTDIR = Path("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a212d008990c6b49a/benchmarks/omr-notehead-precision-2026-09/out/print/same-side-second-v2-2.40")
OUTDIR.mkdir(parents=True, exist_ok=True)

d = record_io.load_record(REC)
rec = d["record"]
obs = rec["observations"]
verdicts = rec["verdicts"]
box_by_subj = {o["subject"]: o for o in obs if o["quantity"] == "glyph_box"}
staff_lines_by = {o["subject"]: o["value"] for o in obs if o["quantity"] == "staff_lines"}
cell_box_by = {o["subject"]: o["value"] for o in obs if o["quantity"] == "cell_box"}
nh_verdict = {v["subject"]: v for v in verdicts if v["quantity"] == "notehead_is_not_a_notehead"}

CELL = "cell/3/1/2/9"
STAFF = "staff/3/1/2"
SUBJECTS = ["glyph/3/1/2/9/1", "glyph/3/1/2/9/2", "glyph/3/1/2/9/3", "glyph/3/1/2/9/5"]
COLORS = {
    "glyph/3/1/2/9/1": (0, 140, 255),      # blue  -- different CLASS, role twin, untouched by this rule
    "glyph/3/1/2/9/2": (220, 20, 20),      # red   -- refused
    "glyph/3/1/2/9/3": (20, 170, 20),      # green -- the KEPT box
    "glyph/3/1/2/9/5": (230, 140, 0),      # orange -- refused (also lost its own same-side hop)
}

print("rendering page 3")
pi = render_page(PDF, 3, dpi=600)
arr = getattr(pi, "rgb", None)
if arr is None:
    arr = getattr(pi, "binary")
arr_np = np.asarray(arr)
base_rgb = np.stack([arr_np] * 3, axis=-1) if arr_np.ndim == 2 else arr_np
img_full = Image.fromarray(base_rgb.astype(np.uint8)).convert("RGB")

cell_box = cell_box_by[CELL]
line_ys = staff_lines_by.get(STAFF) or []
pad = 90
cx0 = max(0, int(cell_box[0] - pad)); cx1 = min(img_full.width, int(cell_box[2] + pad))
cy0 = max(0, int(cell_box[1] - pad)); cy1 = min(img_full.height, int(cell_box[3] + pad))
if line_ys:
    cy0 = min(cy0, int(min(line_ys) - 20))
    cy1 = max(cy1, int(max(line_ys) + 20))
crop = img_full.crop((cx0, cy0, cx1, cy1)).convert("RGB")

# Scale so the TALLEST box is >= 60 px.
heights = []
for s in SUBJECTS:
    b = box_by_subj[s]["detail"]["bbox_page_px"]
    heights.append(b[3] - b[1])
scale = max(4.0, 60.0 / min(heights))
crop = crop.resize((int(crop.width * scale), int(crop.height * scale)), Image.LANCZOS)
draw = ImageDraw.Draw(crop)


def to_crop(px, py):
    return ((px - cx0) * scale, (py - cy0) * scale)


for ly in line_ys:
    x0c, y0c = to_crop(cx0, ly); x1c, y1c = to_crop(cx1, ly)
    draw.line([(x0c, y0c), (x1c, y1c)], fill=(30, 110, 220), width=1)

legend = []
for s in SUBJECTS:
    o = box_by_subj[s]
    box = o["detail"]["bbox_page_px"]
    v = nh_verdict.get(s)
    refused = v.get("value") if v else None
    reason = (v or {}).get("reason")
    color = COLORS[s]
    bx0, by0 = to_crop(box[0], box[1]); bx1, by1 = to_crop(box[2], box[3])
    draw.rectangle([bx0, by0, bx1, by1], outline=color, width=4)
    short = s.split("/")[-1]
    label = f"#{short} {o['value'][0]} {'REFUSED:' + str(reason) if refused else 'STANDS'}"
    draw.text((bx0, max(0, by0 - 16)), label, fill=color)
    legend.append(f"#{short}={'refused(' + str(reason) + ')' if refused else 'stands'}")

draw.rectangle([0, 0, crop.width, 40], fill=(255, 255, 255))
draw.text((4, 4), f"cell/3/1/2/9  " + "  ".join(legend), fill=(0, 0, 0))
draw.text((4, 20), "MY RULE KEEPS #3 (noteheadHalfInSpace) for the {2,3,5} "
                  "cluster; #1 is a different class (role twin), untouched.",
         fill=(0, 0, 0))
fname = "V-CLUSTER-cell-3-1-2-9-clean.png"
crop.save(OUTDIR / fname)
print("wrote", fname, "scale", scale)
