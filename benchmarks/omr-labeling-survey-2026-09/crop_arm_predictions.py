"""Visual-check sheet #2 (Sean, 2026-09-29): after training, one contact
sheet per arm, ~12 held-out cells, full-cell crops (>= 1200 px wide, staff
shaded as a band, legend on the image, one plain question with Y/N codes at
the top -- see crop_common.py) with every rest box drawn:

    GREEN  = a checkpoint detection matched to one of Sean's boxes (SAME
             class, within the audit's own match radius)
    RED    = a checkpoint detection with no matching Sean box nearby
             (a candidate false positive)
    BLUE   = one of Sean's boxes with no matching detection nearby
             (a candidate miss)

Reads held_out_truth.json (Sean's own boxes only, truth_sean -- the arm's
grade against the audit-corrected set is a separate number in
rest_experiment_results.json, not drawn here) and runs the given checkpoint
at conf 0.25. Cells are picked to prioritize ones that HOLD at least one of
Sean's rest boxes, so the sheet is not mostly-empty crops.

    python3 .../crop_arm_predictions.py --weights <ckpt.pt> --tag A-baseline-epoch0 [--n 12]
Writes benchmarks/omr-labeling-survey-2026-09/out/rest-experiment/crop-preds-<tag>/
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cv2

from crop_common import render_cell
from rest_experiment_lib import run_teacher, match_detections, load_manifest_staff_lines

REPO = Path.cwd()
SURVEY = REPO / "benchmarks" / "omr-labeling-survey-2026-09"
TRUTH = SURVEY / "held_out_truth.json"
OUT_ROOT = SURVEY / "out" / "rest-experiment"
REST_CLASSES = {"restWhole", "restHalf", "restQuarter", "rest8th", "rest16th", "restHBar"}

GREEN = (0, 150, 40)
RED = (220, 30, 20)
BLUE = (30, 90, 220)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--device", default="mps")
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--n", type=int, default=12)
    a = ap.parse_args()

    if not TRUTH.exists():
        print(f"missing {TRUTH} -- run build_held_out_truth.py first")
        return 2
    truth = json.loads(TRUTH.read_text())

    with_truth = [cid for cid, e in truth.items() if e["sean"]]
    without = [cid for cid, e in truth.items() if not e["sean"]]
    order = sorted(with_truth) + sorted(without)
    cells = order[:a.n]

    out_dir = OUT_ROOT / f"crop-preds-{a.tag}"
    manifest = []
    legend = [(GREEN, "detection matched a Sean box (same class)"),
              (RED, "detection, NO matching Sean box nearby (candidate false positive)"),
              (BLUE, "Sean box, NO matching detection nearby (candidate miss)")]
    for i, cid in enumerate(cells, 1):
        e = truth[cid]
        img = cv2.imread(e["image_path"])
        if img is None:
            continue
        ys = load_manifest_staff_lines(cid)
        dets = run_teacher(img, ys, REST_CLASSES, a.weights, device=a.device, conf=a.conf)
        human_px = [(b["cls"], b["cx"], b["cy"], b["w"], b["h"]) for b in e["sean"]]
        matches = match_detections(dets, human_px, same_class=True)
        matched_dets = [m.det for m in matches if m.matched_cls is not None]
        unmatched_dets = [m.det for m in matches if m.matched_cls is None]

        # which Sean boxes got claimed -- redo the same greedy same-class pass
        # to get the complementary (unmatched TRUTH) side; match_detections()
        # doesn't return truth-side indices.
        used = [False] * len(human_px)
        for d in sorted(dets, key=lambda x: -x.conf):
            best_i, best_dist = -1, 1e9
            for j, (c, cx, cy, w, h) in enumerate(human_px):
                if used[j] or c != d.cls:
                    continue
                dist = math.hypot(d.cx - cx, d.cy - cy)
                diag = math.hypot((d.w + w) / 2, (d.h + h) / 2)
                norm = dist / max(diag, 1.0)
                if norm <= 0.6 and norm < best_dist:
                    best_dist, best_i = norm, j
            if best_i >= 0:
                used[best_i] = True
        unmatched_truth = [b for j, b in enumerate(e["sean"]) if not used[j]]

        boxes = []
        for d in matched_dets:
            boxes.append((*d.bbox, GREEN, f"{d.cls} {d.conf:.2f}"))
        for d in unmatched_dets:
            boxes.append((*d.bbox, RED, f"{d.cls} {d.conf:.2f}"))
        for b in unmatched_truth:
            x0, y0 = b["cx"] - b["w"] / 2, b["cy"] - b["h"] / 2
            x1, y1 = b["cx"] + b["w"] / 2, b["cy"] + b["h"] / 2
            boxes.append((x0, y0, x1, y1, BLUE, f"{b['cls']} (missed)"))

        name = f"{a.tag}-{i:02d}.png"
        title = f"{name}   cell {cid}   weights={Path(a.weights).name}   conf {a.conf}"
        question = ("For each RED box: is it a real rest we should have boxed?  "
                    "Y = yes (a real miss)   N = no (false detection).  "
                    "For each BLUE box: was Sean's box a mistake?  "
                    "Y = yes, mistake   N = no, box is correct, model just missed it")
        ok = render_cell(e["image_path"], ys, boxes, title, question, legend, out_dir / name)
        if not ok:
            continue
        manifest.append({
            "n": i, "file": name, "cell_id": cid, "tag": a.tag,
            "n_matched": len(matched_dets), "n_fp_candidates": len(unmatched_dets),
            "n_missed": len(unmatched_truth),
            "question": question,
            "answer_codes": {"RED_Y": "real miss, should be boxed",
                             "RED_N": "false detection",
                             "BLUE_Y": "Sean's box was a mistake",
                             "BLUE_N": "box correct, model missed it"},
            "VERDICT_none_yet": None,
        })

    (out_dir / "manifest.json").write_text(json.dumps({
        "sheet": f"arm {a.tag} -- held-out rest detections vs Sean's boxes",
        "weights": a.weights, "conf": a.conf, "n": len(manifest), "crops": manifest,
    }, indent=2))
    print(f"wrote {len(manifest)} crops -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
