"""Render overlays for missed truth boxes: truth box (green), chained strokes
(red), raw thin-mask components (blue) — into scratch dir for inspection."""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, ".")
from tools.omr import arc_detection as ad  # noqa: E402

B = Path("benchmarks/omr-queue-arcs-2026-09")
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/arc_overlays")
OUT.mkdir(parents=True, exist_ok=True)
ARC = {"tie", "slur"}


def iou(a, b):
    ix = max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    inter = ix * iy
    return inter / (a[2] * a[3] + b[2] * b[3] - inter) if inter else 0.0


mans = {e["cell_id"]: e for e in json.load(open(B / "cells.json"))}
wanted_cells = sys.argv[2:]
n_done = 0
for vf in sorted((B / "verdicts").glob("*.verdict.json")):
    v = json.loads(vf.read_text())
    cid = v["cell_id"]
    if wanted_cells and cid not in wanted_cells:
        continue
    tb = []
    for d in v.get("detections", []):
        cls = d.get("human_corrected_class") or d.get("model_predicted_class")
        bb = d.get("human_bbox") or d.get("model_bbox")
        if bb and d.get("verdict") in ("TP", "WRONG_CATEGORY", "WRONG_BBOX") and cls in ARC:
            tb.append((cls, (bb["x"], bb["y"], bb["w"], bb["h"])))
    for a in v.get("added_detections", []):
        if a.get("human_class") in ARC:
            bb = a["bbox"]
            tb.append((a["human_class"], (bb["x"], bb["y"], bb["w"], bb["h"])))
    if not tb:
        continue
    e = mans.get(cid)
    img_ns = cv2.imread(str(B / "cells" / f"{cid}_nostaff.png"), cv2.IMREAD_GRAYSCALE)
    if e is None or img_ns is None:
        continue
    ys = e.get("staff_line_ys_canonical") or []
    sp = (max(ys) - min(ys)) / 4.0 if len(ys) >= 2 else 84.0
    _, ink = cv2.threshold(img_ns, 180, 255, cv2.THRESH_BINARY_INV)
    thin = ad._thin_run_mask(ink, max(2, int(round(ad.ARC_THIN_RUN_MAX_SPACES * sp))))
    usable, cut = ad._extract_strokes(thin, sp, ad.ARC_EDGE_MARGIN_PX)
    chained = ad._chain_strokes(usable, sp)

    class _C:
        staff_line_ys_canonical = ys
        image = img_ns
        image_no_staff = img_ns
    dets = ad.detect_arcs(_C())
    preds = [(d.smufl_name, (d.x_canonical, d.y_canonical, d.width_canonical,
                             d.height_canonical)) for d in dets]
    # does any truth box miss?
    missed = []
    for cls, box in tb:
        if not any(iou(box, pb) >= 0.3 for _c, pb in preds):
            missed.append((cls, box))
    if not missed and not wanted_cells:
        continue
    vis = cv2.cvtColor(img_ns, cv2.COLOR_GRAY2BGR)
    vis[thin] = (255, 128, 0)
    for s in chained:
        have = ~np.isnan(s.mid)
        if not have.any():
            continue
        ms = s.mid[have]
        cv2.rectangle(vis, (s.x0, int(np.min(ms)) - 3),
                      (s.x1, int(np.max(ms)) + 3), (0, 0, 255), 2)
    for _c, pb in preds:
        cv2.rectangle(vis, (pb[0], pb[1]), (pb[0] + pb[2], pb[1] + pb[3]),
                      (255, 0, 255), 3)
    for cls, box in tb:
        col = (0, 200, 0) if (cls, box) not in missed else (0, 255, 255)
        cv2.rectangle(vis, (box[0], box[1]), (box[0] + box[2], box[1] + box[3]),
                      col, 2)
        cv2.putText(vis, cls, (box[0], max(12, box[1] - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 2)
    cv2.imwrite(str(OUT / f"{cid}.png"), vis)
    n_done += 1
    if n_done >= 12 and not wanted_cells:
        break
print("wrote", n_done, "overlays to", OUT)
