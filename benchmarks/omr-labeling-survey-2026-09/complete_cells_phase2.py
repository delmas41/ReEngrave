"""Completion detector for the Phase-2 hollow-notehead batches (hollow3).

Adapts complete_cells.py (round 2 / v8) to the four Phase-2 missing-tradition
batches. For each cell carrying a human hollow box, run the CURRENT PRODUCTION
detector (deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt, per-cell imgsz rule,
conf>=0.50) to recover the NON-hollow, density-prior-critical content (BLACK
noteheads + augmentation dots) so training does not treat those symbols as
background. Filters + dedupes, drops anything overlapping a human hollow box.

Writes:
  <batch>/completion/candidates/<cell>.json   kept model detections (to audit)
  <batch>/completion/overlays/<cell>.png       hollow (green) + model (red) overlay
  <survey>/completion_summary_phase2.json       aggregate counts

NOTHING here writes to verdicts/ (human record). The audited/merged verdicts are
produced by build_phase2_versions.py after these overlays are reviewed.

Run from the isolated worktree root:
  python3 benchmarks/omr-labeling-survey-2026-09/complete_cells_phase2.py [--device cpu|mps]
"""
from __future__ import annotations
import argparse, json, sys, glob, os
from pathlib import Path
import cv2
import numpy as np

sys.path.insert(0, str(Path.cwd()))
from tools.omr.yolo_detector import YoloDetector
from tools.omr.annotate.build_template import _load_cell_from_manifest
from tools.omr.transcribe import _drop_clipped_notehead_fragments

# CURRENT production weights (the hollow fine-tune shipped 2026-09-03). Absolute
# path to the MAIN checkout: the weights are gitignored and do not exist in a
# fresh worktree. They survive the main checkout's branch switches (git checkout
# never touches ignored files).
WEIGHTS = "/Users/seanjohnson/Desktop/ReEngrave/omr-weights/deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt"
CONF = 0.50

# Completion scope (gate-appropriate, identical to v8): keep only the
# density-prior-critical classes — BLACK noteheads + augmentation dots. Model
# rests/accidentals/flags are FP-prone on this domain and add no needed positive
# signal (richly covered by v1-v4 + DSv2), so they are DROPPED and documented as
# unlabeled background. Hollow noteheads are HUMAN-labeled, so the model's hollow
# detections are dropped too.
KEEP_NAMES = {"noteheadblackonline", "noteheadblackinspace", "augmentationdot"}
HOLLOW_KEYS = ("noteheadhalf", "noteheadwhole", "noteheaddoublewhole")

# audit-driven systematic FP culls (populated AFTER reviewing the overlays):
#  - a bass/F-clef's two dots read as augmentationDot sit in the clef/key-sig
#    zone (cx < 18% of the cell); cull augmentationDot there.
CLEF_DOT_CX_FRAC = 0.18
#  - explicit (cell, class, bbox) culls for one-off FPs seen in the audit.
EXPLICIT_CULL: list[tuple] = [
    # (cell_id, class, cx_min, cx_max, cy_min, cy_max)  in canonical px
    # Audit 2026-09-03: a solid black block flush against the cell's TOP edge
    # (y=0, h=86) — bleed from the staff above, not this measure's notehead.
    # _drop_clipped_notehead_fragments did not catch it; not_lr_edge only guards
    # left/right. Cull the single candidate at cx~178, cy~43.
    ("mahler1-p4-sys0-s4-m7", "noteheadBlackInSpace", 150, 210, 0, 90),
]


def _norm(name: str) -> str:
    return "".join(ch for ch in (name or "").lower() if ch.isalnum())

def _is_hollow(name: str) -> bool:
    k = _norm(name)
    return any(k.startswith(h) or h in k for h in HOLLOW_KEYS)

def _iou(a, b) -> float:
    ax0, ay0, aw, ah = a; ax1, ay1 = ax0+aw, ay0+ah
    bx0, by0, bw, bh = b; bx1, by1 = bx0+bw, by0+bh
    iw = max(0, min(ax1,bx1)-max(ax0,bx0)); ih = max(0, min(ay1,by1)-max(ay0,by0))
    inter = iw*ih
    if inter <= 0: return 0.0
    ua = aw*ah + bw*bh - inter
    return inter/ua if ua>0 else 0.0

def _center_in(inner, outer) -> bool:
    ix, iy, iw, ih = inner
    cx, cy = ix+iw/2, iy+ih/2
    ox, oy, ow, oh = outer
    return ox <= cx <= ox+ow and oy <= cy <= oy+oh

def keep_det(d) -> bool:
    nm = _norm(getattr(d, "smufl_name", ""))
    if _is_hollow(getattr(d, "smufl_name", "")):
        return False
    return nm in KEEP_NAMES

def is_clef_dot(d, W) -> bool:
    if _norm(getattr(d, "smufl_name", "")) != "augmentationdot":
        return False
    cx = d.x_canonical + d.width_canonical / 2
    return cx < CLEF_DOT_CX_FRAC * W

def is_explicit_cull(d, cid) -> bool:
    cx = d.x_canonical + d.width_canonical / 2
    cy = d.y_canonical + d.height_canonical / 2
    for (c, cls, x0, x1, y0, y1) in EXPLICIT_CULL:
        if c == cid and getattr(d, "smufl_name", "") == cls and x0 <= cx <= x1 and y0 <= cy <= y1:
            return True
    return False

def not_lr_edge(d, W, tol=8) -> bool:
    return d.x_canonical > tol and (d.x_canonical + d.width_canonical) < W - tol

def cross_class_nms(dets, iou_thr=0.45):
    dets = sorted(dets, key=lambda d: -d.confidence)
    out = []
    for d in dets:
        db = (d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical)
        if any(_iou(db, (o.x_canonical,o.y_canonical,o.width_canonical,o.height_canonical)) > iou_thr for o in out):
            continue
        out.append(d)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cpu", choices=["cpu", "mps"])
    ap.add_argument("--weights", default=WEIGHTS)
    args = ap.parse_args()

    batches = sorted(glob.glob("benchmarks/omr-labeling-hollow3-2026-09-*"))
    detector = YoloDetector(args.weights, device=args.device)
    root = Path.cwd()
    summary = {"weights": args.weights, "conf": CONF, "device": args.device, "batches": {}}
    grand_kept = {}
    grand_cells = 0
    for b in batches:
        name = os.path.basename(b)
        manifest = {e["cell_id"]: e for e in json.loads(Path(b, "cells.json").read_text())}
        comp = Path(b, "completion")
        (comp/"candidates").mkdir(parents=True, exist_ok=True)
        (comp/"overlays").mkdir(parents=True, exist_ok=True)
        vfiles = sorted(glob.glob(os.path.join(b, "verdicts", "*.verdict.json")))
        per_cell = {}
        bkept = {}
        for vf in vfiles:
            v = json.loads(Path(vf).read_text())
            hollow = v.get("added_detections", [])
            if not hollow:
                continue
            cid = v["cell_id"]
            entry = manifest.get(cid)
            if entry is None:
                continue
            cell = _load_cell_from_manifest(entry, root)
            H, W = cell.image.shape[:2]
            dets = detector.detect(cell, conf_threshold=CONF, imgsz=None)
            dets, _ = _drop_clipped_notehead_fragments(dets, cell)
            dets = [d for d in dets if keep_det(d) and not_lr_edge(d, W)]
            hboxes = [(h["bbox"]["x"], h["bbox"]["y"], h["bbox"]["w"], h["bbox"]["h"]) for h in hollow]
            filt = []
            for d in dets:
                db = (d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical)
                if any(_iou(db, hb) > 0.25 or _center_in(db, hb) for hb in hboxes):
                    continue
                filt.append(d)
            filt = cross_class_nms(filt)
            filt = [d for d in filt if not is_clef_dot(d, W) and not is_explicit_cull(d, cid)]
            grand_cells += 1
            cand = [{
                "smufl_name": d.smufl_name, "category": d.category,
                "bbox": {"x": d.x_canonical, "y": d.y_canonical, "w": d.width_canonical, "h": d.height_canonical},
                "confidence": round(float(d.confidence), 4),
            } for d in filt]
            Path(comp/"candidates"/f"{cid}.json").write_text(json.dumps(
                {"cell_id": cid, "n_hollow": len(hollow), "candidates": cand}, indent=2))
            per_cell[cid] = {"n_hollow": len(hollow), "n_candidates": len(cand),
                             "classes": sorted({c["smufl_name"] for c in cand})}
            for c in cand:
                bkept[c["smufl_name"]] = bkept.get(c["smufl_name"], 0) + 1
                grand_kept[c["smufl_name"]] = grand_kept.get(c["smufl_name"], 0) + 1
            img = cell.image
            canvas = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            for hb in hboxes:
                x,y,w,h = [int(t) for t in hb]
                cv2.rectangle(canvas, (x,y), (x+w,y+h), (0,200,0), 4)
            for d in filt:
                x,y,w,h = d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical
                cv2.rectangle(canvas, (x,y), (x+w,y+h), (0,0,255), 3)
                cv2.putText(canvas, f"{d.smufl_name} {d.confidence:.2f}", (x, max(0,y-6)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,255), 2)
            cv2.imwrite(str(comp/"overlays"/f"{cid}.png"), canvas)
        summary["batches"][name] = {
            "cells_completed": len(per_cell),
            "kept_by_class": bkept,
            "total_kept": sum(v["n_candidates"] for v in per_cell.values()),
            "per_cell": per_cell,
        }
        print(f"{name:52s} cells={len(per_cell):3d} kept={sum(v['n_candidates'] for v in per_cell.values()):4d} {bkept}")
    summary["grand_kept_by_class"] = grand_kept
    summary["grand_cells"] = grand_cells
    summary["grand_total_kept"] = sum(grand_kept.values())
    Path("benchmarks/omr-labeling-survey-2026-09/completion_summary_phase2.json").write_text(json.dumps(summary, indent=2))
    print("="*90)
    print(f"TOTAL cells={grand_cells} kept={sum(grand_kept.values())}")
    print("by class:", dict(sorted(grand_kept.items(), key=lambda kv:-kv[1])))

if __name__ == "__main__":
    main()
