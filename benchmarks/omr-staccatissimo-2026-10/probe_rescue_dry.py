"""2.138 dry run: page 24 only; production detections, then gather_wedge_rescue, printing what it keeps / refuses. STAGED GATHER.
python3 probe_rescue_dry.py OUT.json [cell filter like 24/0/1/4 ...]"""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import gather as G
from tools.omr.staged.pipeline import prepare_pages
from tools.omr.staged.record import Log
from tools.omr.staged import weight_routing as WR
from tools.omr.yolo_detector import YoloDetector
PDF = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"
t0 = time.time()
w, _, _ = WR.resolve_staged_weights(PDF, [24], weights="auto", route_weights=True)
det = YoloDetector(w)
prep = prepare_pages(PDF, [24], dpi=600)
(pws, cells), = prep
log = Log()
local = G.gather_geometry(log, pws)
dets = G.gather_detections(log, cells, local, detector=det, conf_threshold=0.25, imgsz=None)
print("detect", round(time.time() - t0), flush=True)
want = set(sys.argv[2:])
cells_all = list(cells)
if want:
    cells = [c for c in cells if any(("%d/%d/%d/%d" % (c.page_index, *local[c.staff_index], c.measure_index)) == w_ for w_ in want)]
n0 = {k: len(v) for k, v in dets.items()}
G.gather_wedge_rescue(log, cells, local, dets, detector=det, progress=True)
out = {"kept": [], "refused": []}
for o in log.observations if hasattr(log, "observations") else []:
    pass
for k, v in dets.items():
    for gi in range(n0.get(k, 0), len(v)):
        d = v[gi]
        cc = next(c for c in cells_all if "cell/%d/%d/%d/%d" % (c.page_index, *local[c.staff_index], c.measure_index) == k)
        out["kept"].append([k, gi, d.smufl_name, round(float(d.confidence), 3), [round(x, 1) for x in G._page_box(cc, d)]])
for a in list(log._abs.values()):
    if a.reader == "yolo_rescue_wedge":
        out["refused"].append([a.subject.to_key(), a.reason, a.detail])
json.dump(out, open(sys.argv[1], "w"), default=str)
print("kept", len(out["kept"]), "refused", len(out["refused"]), round(time.time() - t0))
for r in out["kept"]: print(r)
