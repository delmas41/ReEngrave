import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

from tools.omr.preprocessing import render_page

PDF = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
PAGE_IDX = 3
OUTDIR = Path("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a212d008990c6b49a/benchmarks/omr-notehead-precision-2026-09/out/print/missed-dyads-2.40")
OUTDIR.mkdir(parents=True, exist_ok=True)

cands = json.load(open("/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-acceptance-measure-notehead-box-e75821/2c34bf69-0e00-4748-a821-6f4862e751be/scratchpad/candidates_extracted.json"))

print("rendering page", PAGE_IDX)
pi = render_page(PDF, PAGE_IDX, dpi=600)
arr = getattr(pi, "rgb", None)
if arr is None:
    arr = getattr(pi, "binary")
arr_np = np.asarray(arr)
if arr_np.ndim == 2:
    base_rgb = np.stack([arr_np] * 3, axis=-1)
else:
    base_rgb = arr_np
img_full = Image.fromarray(base_rgb.astype(np.uint8)).convert("RGB")

manifest = []
for i, c in enumerate(cands):
    tag = f"M{i+1:02d}"
    cell_box = c["cell_box_page"]
    if cell_box is None:
        continue
    line_ys = c["staff_lines"] or []
    ss = c["staff_spacing"] or 60.0
    pad_x = 1.0 * ss
    pad_y = 1.5 * ss
    cx0 = max(0, int(cell_box[0] - pad_x))
    cx1 = min(img_full.width, int(cell_box[2] + pad_x))
    cy0 = max(0, int(cell_box[1] - pad_y))
    cy1 = min(img_full.height, int(cell_box[3] + pad_y))
    if line_ys:
        cy0 = min(cy0, int(min(line_ys) - 15))
        cy1 = max(cy1, int(max(line_ys) + 15))
    crop = img_full.crop((cx0, cy0, cx1, cy1)).convert("RGB")
    scale = 2.0
    crop = crop.resize((int(crop.width * scale), int(crop.height * scale)), Image.LANCZOS)
    draw = ImageDraw.Draw(crop)

    def to_crop(px, py):
        return ((px - cx0) * scale, (py - cy0) * scale)

    for ly in line_ys:
        x0c, y0c = to_crop(cx0, ly)
        x1c, y1c = to_crop(cx1, ly)
        draw.line([(x0c, y0c), (x1c, y1c)], fill=(30, 110, 220), width=1)

    n_notehead = 0
    for g in c["glyphs"]:
        if not str(g["cls"]).lower().startswith("notehead"):
            continue
        n_notehead += 1
        box = g["box_page"]
        if not box:
            continue
        bx0, by0 = to_crop(box[0], box[1])
        bx1, by1 = to_crop(box[2], box[3])
        color = (220, 20, 20) if g["refused"] else (20, 160, 20)
        draw.rectangle([bx0, by0, bx1, by1], outline=color, width=3)
        draw.text((bx0, max(0, by0 - 14)),
                  f"{g['cls']}{' REFUSED:' + str(g['reason']) if g['refused'] else ''}",
                  fill=color)

    draw.rectangle([0, 0, crop.width, 22], fill=(255, 255, 255))
    draw.text((4, 4),
              f"{tag} {c['family']} bar {c['bar']} (cell {c['system']}/{c['staff']}/{c['cell']}) "
              f"notehead_boxes={n_notehead}", fill=(0, 0, 0))
    fname = f"{tag}-{c['family']}-bar{c['bar']}.png"
    crop.save(OUTDIR / fname)
    manifest.append(dict(tag=tag, file=fname, family=c["family"], bar=c["bar"],
                         n_notehead_boxes=n_notehead,
                         glyphs=[{k: v for k, v in g.items() if k != "box_canon"}
                                for g in c["glyphs"] if str(g["cls"]).lower().startswith("notehead")]))
    print(tag, fname, "n_notehead=", n_notehead)

json.dump(manifest, open(OUTDIR / "manifest.json", "w"), indent=1, default=str)
