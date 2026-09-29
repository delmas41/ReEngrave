"""Score one checkpoint's rest detections on the held-out rest-positive cells
against BOTH truth sets (held_out_truth.json), at conf 0.25 -- the pipeline's
own threshold, per CLAUDE.md flags table.

Reports precision/recall/F1 overall AND split into {restWhole, restHBar} vs
the other four rest classes, because UNBOXED-AUDIT.md found those two behave
nothing like the rest of the family (near-100% false-positive on unmatched
ink) -- a pooled number here would hide exactly the distinction the audit
exists to make.

    python3 .../eval_rest_arm.py --weights <ckpt.pt> --tag A-baseline-frz-e0 [--device mps]
Appends a row to rest_experiment_results.json (one file, all arms, so the
driver script's final table reads one thing).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2

from rest_experiment_lib import run_teacher, match_detections, load_manifest_staff_lines

REPO = Path.cwd()
SURVEY = REPO / "benchmarks" / "omr-labeling-survey-2026-09"
TRUTH = SURVEY / "held_out_truth.json"
RESULTS = SURVEY / "rest_experiment_results.json"
REST_CLASSES = {"restWhole", "restHalf", "restQuarter", "rest8th", "rest16th", "restHBar"}


def prf(tp: int, n_pred: int, n_truth: int):
    p = tp / n_pred if n_pred else 0.0
    r = tp / n_truth if n_truth else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return {"tp": tp, "n_pred": n_pred, "n_truth": n_truth, "precision": p, "recall": r, "f1": f1}


def score_against(dets_by_cell: dict, truth: dict, truth_key: str, class_filter=None):
    tp = n_pred = n_truth = 0
    for cid, dets in dets_by_cell.items():
        t = truth[cid][truth_key]
        if class_filter is not None:
            t = [b for b in t if b["cls"] in class_filter]
            dets = [d for d in dets if d.cls in class_filter]
        n_truth += len(t)
        n_pred += len(dets)
        human_px = [(b["cls"], b["cx"], b["cy"], b["w"], b["h"]) for b in t]
        matches = match_detections(dets, human_px, same_class=True)
        tp += sum(1 for m in matches if m.matched_cls is not None)
    return prf(tp, n_pred, n_truth)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--device", default="mps")
    ap.add_argument("--conf", type=float, default=0.25)
    a = ap.parse_args()

    if not TRUTH.exists():
        print(f"missing {TRUTH} -- run build_held_out_truth.py first")
        return 2
    truth = json.loads(TRUTH.read_text())

    dets_by_cell = {}
    for cid, e in truth.items():
        img = cv2.imread(e["image_path"])
        if img is None:
            print(f"  !! missing image {e['image_path']}")
            continue
        ys = load_manifest_staff_lines(cid)
        dets_by_cell[cid] = run_teacher(img, ys, REST_CLASSES, a.weights,
                                        device=a.device, conf=a.conf)

    fp_mode = {"restWhole", "restHBar"}
    other = REST_CLASSES - fp_mode
    result = {
        "tag": a.tag, "weights": a.weights, "conf": a.conf,
        "n_cells": len(dets_by_cell),
        "n_detections_total": sum(len(v) for v in dets_by_cell.values()),
        "vs_sean_all": score_against(dets_by_cell, truth, "sean"),
        "vs_corrected_all": score_against(dets_by_cell, truth, "corrected"),
        "vs_sean_fp_mode_classes": score_against(dets_by_cell, truth, "sean", fp_mode),
        "vs_corrected_fp_mode_classes": score_against(dets_by_cell, truth, "corrected", fp_mode),
        "vs_sean_other_classes": score_against(dets_by_cell, truth, "sean", other),
        "vs_corrected_other_classes": score_against(dets_by_cell, truth, "corrected", other),
    }
    print(json.dumps(result, indent=1))

    rows = json.loads(RESULTS.read_text()) if RESULTS.exists() else []
    rows = [r for r in rows if r["tag"] != a.tag] + [result]
    RESULTS.write_text(json.dumps(rows, indent=1) + "\n")
    print(f"wrote/updated {a.tag} in {RESULTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
