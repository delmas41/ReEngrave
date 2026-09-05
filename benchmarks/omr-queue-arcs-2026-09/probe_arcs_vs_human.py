"""Score tie/slur detections against the adjudicated human boxes, per checkpoint."""
import json, sys, glob
from pathlib import Path
sys.path.insert(0, ".")
import cv2
from tools.omr.yolo_detector import YoloDetector, imgsz_for_cell

BATCH = Path("benchmarks/omr-queue-arcs-2026-09")
names_want = {"tie", "slur"}

def iou(a, b):
    ix = max(0, min(a[0]+a[2], b[0]+b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[1]+a[3], b[1]+b[3]) - max(a[1], b[1]))
    inter = ix*iy
    return inter/(a[2]*a[3]+b[2]*b[3]-inter) if inter else 0.0

class _Cell:
    def __init__(s, ys, im): s.staff_line_ys_canonical, s.image = ys, im

# human truth: decided boxes from the adjudicated batch
truth = {}
mans = {e["cell_id"]: e for e in json.load(open(BATCH/"cells.json"))}
for vf in sorted(BATCH.glob("verdicts/*.verdict.json")):
    v = json.loads(vf.read_text())
    boxes = []
    for d in v.get("detections", []):
        if d.get("verdict") in ("TP","WRONG_CATEGORY","WRONG_BBOX"):
            cls = d.get("human_corrected_class") or d.get("model_predicted_class")
            b = d.get("human_bbox") or d.get("model_bbox")
            if cls in names_want and b: boxes.append((cls,(b["x"],b["y"],b["w"],b["h"])))
    for a in v.get("added_detections", []):
        if a.get("human_class") in names_want:
            b=a["bbox"]; boxes.append((a["human_class"],(b["x"],b["y"],b["w"],b["h"])))
    truth[v["cell_id"]] = boxes

results = {}
for tag, wpath in [a.split("=",1) for a in sys.argv[1:]]:
    det = YoloDetector(wpath, device="mps")
    tp=fp=fn=0; kind_ok=0; n_det=0
    for cid, tb in truth.items():
        e = mans.get(cid);  img = cv2.imread(str(BATCH/"cells"/f"{cid}.png"))
        if e is None or img is None: continue
        cell = _Cell(e.get("staff_line_ys_canonical") or [], img)
        preds = [(d.smufl_name,(d.x_canonical,d.y_canonical,d.width_canonical,d.height_canonical),d.confidence)
                 for d in det.detect(cell, conf_threshold=0.25, imgsz=imgsz_for_cell(cell))
                 if d.smufl_name in names_want]
        n_det += len(preds)
        used=set()
        for cls,b in tb:
            best=None
            for j,(pc,pb,pcf) in enumerate(preds):
                if j in used: continue
                o=iou(b,pb)
                if o>=0.3 and (best is None or o>best[0]): best=(o,j,pc)
            if best: used.add(best[1]); tp+=1; kind_ok += (best[2]==cls)
            else: fn+=1
        fp += len(preds)-len(used)
    nt = sum(len(v) for v in truth.values())
    results[tag]=dict(dets=n_det, tp=tp, fp=fp, fn=fn,
                      recall=round(tp/nt,3), precision=round(tp/max(1,tp+fp),3),
                      kind_acc=round(kind_ok/max(1,tp),3))
    print(tag, results[tag], flush=True)
json.dump(results, open("/tmp/probe_arcs.json","w"), indent=1)
