import json
from pathlib import Path
from collections import defaultdict
import numpy as np
from PIL import Image, ImageDraw
from tools.omr.staged import record_io
from tools.omr.preprocessing import render_page

PDF = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
REC = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a212d008990c6b49a/out/2.40/litolff-p3-evaluate-v2.json"
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

same_side = [v for v in verdicts if v["quantity"] == "notehead_is_not_a_notehead"
            and v.get("reason") == "same_side_second"]

# group by cell so a cell with >1 refusal gets ONE crop showing all its boxes
by_cell = defaultdict(set)
for v in same_side:
    subj = v["subject"]
    cell = "/".join(["cell"] + subj.split("/")[1:5])
    by_cell[cell].add(subj)
    dup = (v.get("detail") or {}).get("duplicate_of")
    if dup:
        for o in obs:
            if o.get("id") == dup and o["quantity"] == "glyph_box":
                by_cell[cell].add(o["subject"])
                break

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
for i, (cell, subjs) in enumerate(sorted(by_cell.items())):
    tag = f"V{i+1:02d}"
    cell_box = cell_box_by.get(cell)
    st = staff_of_cell(cell)
    line_ys = staff_lines_by.get(st) or []
    if cell_box is None:
        print("NO CELL BOX", cell)
        continue
    pad = 70
    cx0 = max(0, int(cell_box[0] - pad)); cx1 = min(img_full.width, int(cell_box[2] + pad))
    cy0 = max(0, int(cell_box[1] - pad)); cy1 = min(img_full.height, int(cell_box[3] + pad))
    if line_ys:
        cy0 = min(cy0, int(min(line_ys) - 20))
        cy1 = max(cy1, int(max(line_ys) + 20))
    crop = img_full.crop((cx0, cy0, cx1, cy1)).convert("RGB")
    scale = 3.0
    crop = crop.resize((int(crop.width * scale), int(crop.height * scale)), Image.LANCZOS)
    draw = ImageDraw.Draw(crop)

    def to_crop(px, py):
        return ((px - cx0) * scale, (py - cy0) * scale)

    for ly in line_ys:
        x0c, y0c = to_crop(cx0, ly); x1c, y1c = to_crop(cx1, ly)
        draw.line([(x0c, y0c), (x1c, y1c)], fill=(30, 110, 220), width=1)

    labels = []
    for s in sorted(subjs):
        o = box_by_subj.get(s)
        if o is None:
            continue
        box = o["detail"].get("bbox_page_px")
        if not box:
            continue
        v = nh_verdict.get(s)
        refused = v.get("value") if v else None
        det = (v or {}).get("detail") or {}
        ink = det.get("same_side_this_ink")
        color = (220, 20, 20) if refused else (20, 160, 20)
        bx0, by0 = to_crop(box[0], box[1]); bx1, by1 = to_crop(box[2], box[3])
        draw.rectangle([bx0, by0, bx1, by1], outline=color, width=3)
        short = s.split("/")[-1]
        label = f"#{short} {'REFUSED' if refused else 'stands'} ink={ink}"
        draw.text((bx0, max(0, by0 - 14)), label, fill=color)
        labels.append(label)

    draw.rectangle([0, 0, crop.width, 20], fill=(255, 255, 255))
    draw.text((4, 4), f"{tag} {cell}", fill=(0, 0, 0))
    fname = f"{tag}-{cell.replace('/', '-')}.png"
    crop.save(OUTDIR / fname)
    manifest.append(dict(tag=tag, cell=cell, file=fname, subjects=sorted(subjs), labels=labels))
    print(tag, fname, labels)

json.dump(manifest, open(OUTDIR / "manifest.json", "w"), indent=1)
