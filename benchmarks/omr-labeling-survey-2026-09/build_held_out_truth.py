"""Compute the two truth sets for the held-out rest cells (held_out_rests.json),
once, so every arm's eval reads the SAME truth rather than recomputing it (and
so a training run never touches these cells' images differently across arms --
this script only reads from data/specialist-rests and data/user-labeled).

  truth_sean:      exactly Sean's boxes -- the rest-class rows in the FULL
                   (unfiltered) human label file for each held-out cell.
  truth_corrected: truth_sean UNION every teacher (production) rest detection
                   that is unmatched, not restWhole/restHBar, conf >= 0.5 --
                   the SAME rest_experiment_lib.genuine_addition criterion arm
                   B uses to add labels. This is an AUTOMATED PROXY for "what
                   UNBOXED-AUDIT.md's eyeball sample called genuine", not a
                   re-adjudication by Sean of these specific 90 cells -- said
                   again here because this file's output is exactly the
                   number the decision table reads.

Writes held_out_truth.json: {cell_id: {"sean": [...], "corrected": [...]}},
boxes as {"cls", "cx", "cy", "w", "h"} in PIXEL coordinates.

    python3 .../build_held_out_truth.py
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2

from rest_experiment_lib import (
    load_full_labels, run_teacher, match_detections, genuine_addition,
    load_manifest_staff_lines,
)

REPO = Path.cwd()
SURVEY = REPO / "benchmarks" / "omr-labeling-survey-2026-09"
CLASS_NAMES_JSON = REPO / "tools" / "omr" / "training" / "deepscoresv2_208_classes.json"
SOURCE = REPO / "data" / "specialist-rests"
HELD_OUT_MANIFEST = SURVEY / "held_out_rests.json"
OUT = SURVEY / "held_out_truth.json"
REST_CLASSES = {"restWhole", "restHalf", "restQuarter", "rest8th", "rest16th", "restHBar"}
PROD_WEIGHTS = "/Users/seanjohnson/Desktop/ReEngrave/omr-weights/deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt"


def main() -> int:
    if not HELD_OUT_MANIFEST.exists():
        print(f"missing {HELD_OUT_MANIFEST} -- run "
              f"build_rest_experiment_corpora.py --select-held-out first")
        return 2
    manifest = json.loads(HELD_OUT_MANIFEST.read_text())
    names = json.loads(CLASS_NAMES_JSON.read_text())
    versions = [l.strip() for l in (SOURCE / "catalog-versions.txt").read_text().splitlines()
                if l.strip()]

    out = {}
    n_sean = n_added = 0
    for e in manifest["cells"]:
        v, cid = e["version"], e["cell_id"]
        img_path = SOURCE / v / "images" / f"{cid}.png"
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"  !! missing image {img_path}")
            continue
        H, W = img.shape[:2]

        full_human = load_full_labels(cid, versions, names)
        sean = [{"cls": c, "cx": cx * W, "cy": cy * H, "w": w * W, "h": h * H}
                for (c, cx, cy, w, h) in full_human if c in REST_CLASSES]
        n_sean += len(sean)

        hum_px = [(c, cx * W, cy * H, w * W, h * H) for (c, cx, cy, w, h) in full_human]
        ys = load_manifest_staff_lines(cid)
        dets = run_teacher(img, ys, REST_CLASSES, PROD_WEIGHTS, device="mps")
        matches = match_detections(dets, hum_px)
        corrected = list(sean)
        for mr in matches:
            if genuine_addition(mr):
                d = mr.det
                corrected.append({"cls": d.cls, "cx": d.cx, "cy": d.cy, "w": d.w, "h": d.h})
                n_added += 1
        out[cid] = {"version": v, "sean": sean, "corrected": corrected,
                    "image_path": str(img_path)}
        print(f"  {cid}: sean={len(sean)} corrected={len(corrected)}")

    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {OUT}: {len(out)} cells, {n_sean} Sean boxes, "
          f"+{n_added} corrected-truth additions ({n_sean + n_added} total)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
