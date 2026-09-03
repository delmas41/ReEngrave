"""How much detected ink in the training cells is still UNLABELED BACKGROUND?

The measurement that opened this round and has to close it. Before the round it
was run by CLASS — is this class covered by any pass — and found 41.2% of
detections (377 of 916) in classes nothing had ever boxed, dominated by
dynamics 165 and slurs 99 rather than the rests+accidentals the plan named.

This version asks the stronger question, per BOX rather than per class: for each
cell that emits a YOLO label, run the production detector and ask whether each
detection is actually covered by a box in the merged verdict — human or audited
model. A detection with no box over it trains the model to suppress that ink.

⚠️ Detector output is not truth, in either direction. An uncovered detection may
be a false positive that SHOULD be background (a letter of `sempre` read as a
dynamic is the worked example from this round's audit). So this is an upper
bound on the residue, and it is read as a before/after delta on one fixed
detector, never as an absolute defect count.

    python3 .../residual_background.py --merged benchmarks/omr-labeling-survey-2026-09/phase3-merged
    python3 .../residual_background.py --human-only     # the pre-round baseline
"""
from __future__ import annotations
import argparse, json, glob, os, sys, collections
from pathlib import Path
sys.path.insert(0, os.getcwd())
from tools.omr.yolo_detector import YoloDetector
from tools.omr.annotate.build_template import _load_cell_from_manifest
from tools.omr.transcribe import _drop_clipped_notehead_fragments

W = ("/Users/seanjohnson/Desktop/ReEngrave/omr-weights/"
     "deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt")
# stem/beam/staff are found by classical CV upstream and MUST train as
# background — project policy, not an oversight. They are excluded from the
# residue rather than counted as a gap.
CV_CLASSES = {"stem", "beam", "staff", "staffline", "legerline", "ledgerline"}

def iou(a, b):
    ax0, ay0, aw, ah = a; bx0, by0, bw, bh = b
    ix = max(0, min(ax0+aw, bx0+bw) - max(ax0, bx0))
    iy = max(0, min(ay0+ah, by0+bh) - max(ay0, by0))
    inter = ix*iy
    if inter <= 0: return 0.0
    return inter / (aw*ah + bw*bh - inter)

def covered(d, boxes):
    db = (d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical)
    cx, cy = db[0]+db[2]/2, db[1]+db[3]/2
    for b in boxes:
        if iou(db, b) > 0.20: return True
        if b[0] <= cx <= b[0]+b[2] and b[1] <= cy <= b[1]+b[3]: return True
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--merged", default="benchmarks/omr-labeling-survey-2026-09/phase3-merged")
    ap.add_argument("--human-only", action="store_true",
                    help="count only human boxes — reproduces the pre-round baseline")
    ap.add_argument("--conf", type=float, default=0.50)
    ap.add_argument("--device", default="mps")
    a = ap.parse_args()
    det = YoloDetector(W, device=a.device); root = Path.cwd()
    tot = unc = ncell = 0
    by_class = collections.Counter()
    for cj in sorted(glob.glob(os.path.join(a.merged, "*", "*-cells.json"))):
        tag = Path(cj).parent.name
        vdir = Path(cj).parent / "verdicts"
        man = {e["cell_id"]: e for e in json.loads(Path(cj).read_text())}
        t = u = 0
        for cid, e in man.items():
            vp = vdir / f"{cid}.verdict.json"
            if not vp.exists(): continue
            v = json.loads(vp.read_text())
            boxes = [(b["bbox"]["x"], b["bbox"]["y"], b["bbox"]["w"], b["bbox"]["h"])
                     for b in (v.get("added_detections") or [])]
            if not a.human_only:
                boxes += [(b["bbox"]["x"], b["bbox"]["y"], b["bbox"]["w"], b["bbox"]["h"])
                          for b in (v.get("detections") or []) if b.get("verdict") == "TP"]
            try:
                cell = _load_cell_from_manifest(e, root)
                dets = det.detect(cell, conf_threshold=a.conf, imgsz=None)
                dets, _ = _drop_clipped_notehead_fragments(dets, cell)
            except Exception:
                continue
            ncell += 1
            for d in dets:
                nm = getattr(d, "smufl_name", "") or ""
                if "".join(c for c in nm.lower() if c.isalnum()) in CV_CLASSES: continue
                t += 1
                if not covered(d, boxes):
                    u += 1; by_class[nm] += 1
        print(f"  {tag:18s} cells={len(man):3d} detections={t:5d} uncovered={u:5d} "
              f"({100*u/max(t,1):5.1f}%)")
        tot += t; unc += u
    print(f"\n{ncell} cells · {tot} detections · UNCOVERED {unc} = {100*unc/max(tot,1):.1f}%")
    print("\ntop uncovered classes:")
    for n, k in by_class.most_common(20): print(f"    {n:34s} {k:5d}")
    json.dump({"cells": ncell, "detections": tot, "uncovered": unc,
               "by_class": dict(by_class), "human_only": a.human_only},
              open("/tmp/residual_after.json", "w"), indent=1)

if __name__ == "__main__":
    main()
