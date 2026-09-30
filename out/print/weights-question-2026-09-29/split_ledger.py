"""Split the pre-hollow-only ledgerLine boxes on scan cells by geometry: a ledger
line lies OUTSIDE the five staff lines by definition, so an unmatched box whose
centre is inside the staff (top line - 0.3 sp .. bottom line + 0.3 sp) is a
staff line boxed as a ledger. Same the other way for production-only boxes."""
import json, sys, os, cv2
sys.path.insert(0, os.getcwd())
from pathlib import Path
from tools.omr.yolo_detector import YoloDetector, imgsz_for_cell
M = Path("/Users/seanjohnson/Desktop/ReEngrave"); W = M/"omr-weights"; B = M/"benchmarks/omr-labeling-breitkopf-2026-09"
class C:
    def __init__(s, ys, im): s.staff_line_ys_canonical = ys; s.image = im
cells = [(e["cell_id"], C(e["staff_line_ys_canonical"], cv2.imread(str(B/"cells"/f"{e['cell_id']}.png"))))
         for e in json.loads((B/"cells.json").read_text()) if (B/"cells"/f"{e['cell_id']}.png").exists()]
def boxes(path):
    d = YoloDetector(str(path), device="mps")
    return {cid: [(x.x_canonical, x.y_canonical, x.x_canonical+x.width_canonical, x.y_canonical+x.height_canonical)
                  for x in d.detect(c, conf_threshold=0.25, imgsz=imgsz_for_cell(c)) if x.smufl_name == "ledgerLine"]
            for cid, c in cells}
def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    u = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - ix*iy
    return ix*iy/u if u else 0
P = boxes(W/"deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt")
R = boxes(W/"deepscoresv2-yolov8l-imgsz2048-ft-30ep.PRE-HOLLOW-2026-09-03.pt")
res = {"both": 0, "pre_only_outside": 0, "pre_only_inside": 0, "prod_only_outside": 0, "prod_only_inside": 0}
for cid, c in cells:
    ys = sorted(c.staff_line_ys_canonical); sp = (ys[-1]-ys[0])/4; lo, hi = ys[0]-0.3*sp, ys[-1]+0.3*sp
    for mine, other, tag in ((R[cid], P[cid], "pre_only"), (P[cid], R[cid], "prod_only")):
        for b in mine:
            if any(iou(b, o) >= 0.3 for o in other):
                if tag == "pre_only": res["both"] += 1
                continue
            yc = (b[1]+b[3])/2
            res[tag + ("_inside" if lo <= yc <= hi else "_outside")] += 1
print(len(cells), "cells", res)
json.dump(res, open("out/print/weights-question-2026-09-29/breitkopf_ledger_split.json", "w"), indent=1)
