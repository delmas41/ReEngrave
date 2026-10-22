"""Crop sheet: ledgerLine boxes, production vs pre-hollow, on the 30 held-out
cells probe_class_inventory.py uses. Truth = the print (the cell image itself).
Also: production's beam/tie boxes on one cell, where distill25-raw reads none."""
import json, sys, os, cv2, numpy as np
sys.path.insert(0, os.getcwd())
from pathlib import Path
from tools.omr.yolo_detector import YoloDetector, imgsz_for_cell
M = Path("/Users/seanjohnson/Desktop/ReEngrave"); W = M / "omr-weights"
BENCH = sys.argv[1] if len(sys.argv) > 1 else "benchmarks/omr-phase2.5"
TAG = sys.argv[2] if len(sys.argv) > 2 else "wtc"
man = {e["cell_id"]: e for e in json.loads((M/BENCH/"cells.json").read_text())}
class C:
    def __init__(s, ys, im): s.staff_line_ys_canonical = ys; s.image = im
cells = []
for cid, e in sorted(man.items()):
    p = M/BENCH/"cells"/f"{cid}.png"
    if p.exists(): cells.append((cid, C(e.get("staff_line_ys_canonical") or [], cv2.imread(str(p)))))
dets = {}
for tag, f in [("prod", W/"deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt"),
               ("pre", W/"deepscoresv2-yolov8l-imgsz2048-ft-30ep.PRE-HOLLOW-2026-09-03.pt"),
               ("raw", W/"round5-sweep/distill25/epoch0.pt")]:
    d = YoloDetector(str(f), device="mps")
    dets[tag] = {cid: d.detect(c, conf_threshold=0.25, imgsz=imgsz_for_cell(c)) for cid, c in cells}
def box(im, dd, name, col, th=2):
    for x in dd:
        if x.smufl_name == name:
            b = [x.x_canonical, x.y_canonical, x.x_canonical + x.width_canonical, x.y_canonical + x.height_canonical]
            cv2.rectangle(im, (b[0], b[1]), (b[2], b[3]), col, th)
out = Path("out/print/weights-question-2026-09-29"); rows = []
diff = sorted(cells, key=lambda t: -(sum(x.smufl_name=="ledgerLine" for x in dets["pre"][t[0]]) - sum(x.smufl_name=="ledgerLine" for x in dets["prod"][t[0]])))
summary = {}
for cid, c in cells:
    summary[cid] = {t: sum(x.smufl_name=="ledgerLine" for x in dets[t][cid]) for t in dets}
for cid, c in diff[:4]:
    a = c.image.copy(); b = c.image.copy()
    box(a, dets["prod"][cid], "ledgerLine", (0,0,255)); box(b, dets["pre"][cid], "ledgerLine", (255,0,0))
    for im, lab in ((a, f"{cid}  PRODUCTION ledgerLine (red) n={summary[cid]['prod']}"), (b, f"PRE-HOLLOW ledgerLine (blue) n={summary[cid]['pre']}")):
        cv2.putText(im, lab, (5, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,120,0), 1)
    rows.append(np.hstack([a, b]))
h = max(r.shape[1] for r in rows)
rows = [cv2.copyMakeBorder(r, 0, 6, 0, h - r.shape[1], cv2.BORDER_CONSTANT, value=(255,255,255)) for r in rows]
cv2.imwrite(str(out/f"{TAG}_ledger_prod_vs_prehollow.png"), np.vstack(rows))
bt = max(cells, key=lambda t: sum(x.smufl_name in ("beam","tie") for x in dets["prod"][t[0]]))
cid, c = bt; a = c.image.copy(); b = c.image.copy()
for n, col in (("beam",(0,0,255)),("tie",(0,160,255)),("accidentalSharp",(255,0,255)),("augmentationDot",(0,200,0))):
    box(a, dets["prod"][cid], n, col); box(b, dets["raw"][cid], n, col)
cv2.putText(a, f"{cid} PRODUCTION: beam red, tie orange, sharp magenta, dot green", (5,18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0,120,0), 1)
cv2.putText(b, "distill25 RAW (same features, own class rows)", (5,18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0,120,0), 1)
cv2.imwrite(str(out/f"{TAG}_beams_prod_vs_raw.png"), np.hstack([a, b]))
json.dump(summary, open(out/f"{TAG}_ledger_counts.json","w"), indent=1)
print(TAG, len(cells), 'cells', {t: sum(v[t] for v in summary.values()) for t in dets})
