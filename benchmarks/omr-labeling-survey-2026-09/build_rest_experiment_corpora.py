"""Build the four rest corpora for the collapse experiment (arms A/B/C; D and
E reuse A/B's machinery -- see REST_SPECIALIST_EXPERIMENT.md for the design
and the decision table).

Step 0 -- HELD-OUT SPLIT (once, before any corpus is built): a fixed, seeded
sample of rest-positive cells from the existing `data/specialist-rests`
corpus (built by build_specialist_versions.py, unchanged) is set aside as
`held_out_rests.json` and excluded from every arm's TRAINING corpus below.
Held out once, reused by every arm, so the eval is comparable across arms --
building a separate split per arm would let an arm "get lucky" on an easier
val set.

Arm A (control, --arm baseline): the existing family-filtered rests corpus,
minus the held-out cells. This should reproduce round 6's collapse -- it is
round 6's exact corpus (data/specialist-rests) with only the eval cells
removed.

Arm B (--arm completed): arm A's cells, PLUS a label line for every teacher
rest detection that is unmatched to any human box, is not restWhole/restHBar
(the audit's documented false-positive mode), and scores >= 0.5 confidence
(rest_experiment_lib.genuine_addition -- an automated proxy for "genuine",
not Sean's own adjudication of these specific boxes). No rest is left as
background: every cell in the corpus that the teacher says holds a
high-confidence, non-FP-mode rest now has a label there.

Arm C (--arm painted): arm A's cells and labels UNCHANGED, but every
unmatched teacher rest detection (any class, any confidence -- the point is
removing ambiguity, not curating it) has its bbox painted to the cell's own
paper color. That ink is now neither a label nor a background example; the
model never sees it.

    python3 .../build_rest_experiment_corpora.py --select-held-out --n-held-out 90
    python3 .../build_rest_experiment_corpora.py --arm baseline  --out data/rest-exp-A-baseline
    python3 .../build_rest_experiment_corpora.py --arm completed --out data/rest-exp-B-completed
    python3 .../build_rest_experiment_corpora.py --arm painted   --out data/rest-exp-C-painted
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
from pathlib import Path

import cv2
import numpy as np

from rest_experiment_lib import (
    load_full_labels, run_teacher, match_detections, genuine_addition,
    is_fp_mode_class, load_manifest_staff_lines, Det,
)

REPO = Path.cwd()
SURVEY = REPO / "benchmarks" / "omr-labeling-survey-2026-09"
CLASS_NAMES_JSON = REPO / "tools" / "omr" / "training" / "deepscoresv2_208_classes.json"
SOURCE = REPO / "data" / "specialist-rests"   # round 6's own corpus, built by build_specialist_versions.py
HELD_OUT_MANIFEST = SURVEY / "held_out_rests.json"
REST_CLASSES = {"restWhole", "restHalf", "restQuarter", "rest8th", "rest16th", "restHBar"}
PROD_WEIGHTS = "/Users/seanjohnson/Desktop/ReEngrave/omr-weights/deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt"


def _versions() -> list[str]:
    return [l.strip() for l in (SOURCE / "catalog-versions.txt").read_text().splitlines()
            if l.strip()]


def _all_cells() -> list[tuple[str, str]]:
    """(version, cell_id) for every cell in data/specialist-rests."""
    out = []
    for v in _versions():
        for lab in sorted((SOURCE / v / "labels").glob("*.txt")):
            out.append((v, lab.stem))
    return out


def select_held_out(n: int, seed: int = 20260929) -> None:
    """Pick N cells that hold at least one rest box (per data/specialist-rests'
    own filtered labels -- i.e. round 6's own positive population), fixed by
    seed, and write the manifest every arm below reads."""
    names = json.loads(CLASS_NAMES_JSON.read_text())
    positives = []
    for v, cid in _all_cells():
        lab = SOURCE / v / "labels" / f"{cid}.txt"
        if any(len(ln.split()) == 5 for ln in lab.read_text().splitlines() if ln.strip()):
            positives.append((v, cid))
    rng = random.Random(seed)
    rng.shuffle(positives)
    n = min(n, len(positives))
    chosen = sorted(positives[:n])
    HELD_OUT_MANIFEST.write_text(json.dumps(
        {"seed": seed, "source": str(SOURCE), "n_positive_pool": len(positives),
         "n_held_out": len(chosen), "cells": [{"version": v, "cell_id": c} for v, c in chosen]},
        indent=1) + "\n")
    print(f"held out {len(chosen)} of {len(positives)} rest-positive cells "
          f"-> {HELD_OUT_MANIFEST}")


def _held_out_ids() -> set[str]:
    if not HELD_OUT_MANIFEST.exists():
        raise SystemExit(f"run --select-held-out first ({HELD_OUT_MANIFEST} missing)")
    d = json.loads(HELD_OUT_MANIFEST.read_text())
    return {e["cell_id"] for e in d["cells"]}


def _write_cell(out_root: Path, v: str, cid: str, label_lines: list[str], img):
    od = out_root / v
    (od / "labels").mkdir(parents=True, exist_ok=True)
    (od / "images").mkdir(parents=True, exist_ok=True)
    (od / "labels" / f"{cid}.txt").write_text(
        "\n".join(label_lines) + ("\n" if label_lines else ""))
    cv2.imwrite(str(od / "images" / f"{cid}.png"), img)


def build_baseline(out: Path, held_out: set[str]) -> dict:
    versions = _versions()
    n_cells = n_pos = 0
    for v in versions:
        for lab in sorted((SOURCE / v / "labels").glob("*.txt")):
            cid = lab.stem
            if cid in held_out:
                continue
            lines = [ln for ln in lab.read_text().splitlines() if ln.strip()]
            img = cv2.imread(str(SOURCE / v / "images" / f"{cid}.png"))
            if img is None:
                continue
            _write_cell(out, v, cid, lines, img)
            n_cells += 1
            n_pos += len(lines)
    return {"cells": n_cells, "positive_boxes": n_pos}


def build_completed(out: Path, held_out: set[str], device: str) -> dict:
    names = json.loads(CLASS_NAMES_JSON.read_text())
    class_to_id = {n: i for i, n in enumerate(names) if n in REST_CLASSES}
    versions = _versions()
    n_cells = n_pos_orig = n_added = 0
    added_by_class = {}
    additions_log = []   # for the visual-check sheet -- every box actually added, with its bbox+conf
    for v in versions:
        for lab in sorted((SOURCE / v / "labels").glob("*.txt")):
            cid = lab.stem
            if cid in held_out:
                continue
            img = cv2.imread(str(SOURCE / v / "images" / f"{cid}.png"))
            if img is None:
                continue
            H, W = img.shape[:2]
            lines = [ln for ln in lab.read_text().splitlines() if ln.strip()]
            n_pos_orig += len(lines)

            full_human = load_full_labels(cid, versions, names)
            hum_px = [(c, cx * W, cy * H, w * W, h * H) for (c, cx, cy, w, h) in full_human]
            ys = load_manifest_staff_lines(cid)
            dets = run_teacher(img, ys, REST_CLASSES, PROD_WEIGHTS, device=device)
            matches = match_detections(dets, hum_px)
            for mr in matches:
                if genuine_addition(mr):
                    d = mr.det
                    cx, cy, w, h = d.cx / W, d.cy / H, d.w / W, d.h / H
                    lines.append(f"{class_to_id[d.cls]} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
                    n_added += 1
                    added_by_class[d.cls] = added_by_class.get(d.cls, 0) + 1
                    additions_log.append({
                        "version": v, "cell_id": cid,
                        "image_path": str(SOURCE / v / "images" / f"{cid}.png"),
                        "cls": d.cls, "conf": d.conf,
                        "bbox_px": [d.cx - d.w / 2, d.cy - d.h / 2, d.cx + d.w / 2, d.cy + d.h / 2],
                    })
            _write_cell(out, v, cid, lines, img)
            n_cells += 1
    (out / "additions.json").write_text(json.dumps(additions_log, indent=1) + "\n")
    return {"cells": n_cells, "positive_boxes_original": n_pos_orig,
            "positive_boxes_added": n_added, "added_by_class": added_by_class,
            "positive_boxes_total": n_pos_orig + n_added}


def _paper_color(img, bbox) -> tuple:
    """Estimate the local paper color from a ring just outside the bbox --
    cheaper and more honest than a global white, since scans are not pure
    white and lighting varies across a cell."""
    H, W = img.shape[:2]
    x0, y0, x1, y1 = bbox
    pad = max(4, int(0.15 * max(x1 - x0, y1 - y0)))
    rx0, ry0 = max(0, int(x0) - pad), max(0, int(y0) - pad)
    rx1, ry1 = min(W, int(x1) + pad), min(H, int(y1) + pad)
    ring = img[ry0:ry1, rx0:rx1].copy()
    inner_x0, inner_y0 = int(x0) - rx0, int(y0) - ry0
    inner_x1, inner_y1 = int(x1) - rx0, int(y1) - ry0
    mask = np.ones(ring.shape[:2], dtype=bool)
    mask[max(0, inner_y0):inner_y1, max(0, inner_x0):inner_x1] = False
    if mask.sum() < 10:
        return tuple(int(v) for v in np.median(img.reshape(-1, img.shape[2]), axis=0))
    vals = ring[mask]
    # brightest quartile of the ring == paper, not ink -- a ring that
    # partially overlaps a staff line or beam would otherwise pull the
    # estimate dark.
    gray = vals.mean(axis=1) if vals.ndim > 1 else vals
    thr = np.percentile(gray, 75)
    bright = vals[gray >= thr]
    if len(bright) == 0:
        bright = vals
    return tuple(int(v) for v in np.median(bright, axis=0))


def build_painted(out: Path, held_out: set[str], device: str) -> dict:
    names = json.loads(CLASS_NAMES_JSON.read_text())
    versions = _versions()
    n_cells = n_painted = 0
    painted_by_class = {}
    painted_log = []   # for the visual-check sheet
    for v in versions:
        for lab in sorted((SOURCE / v / "labels").glob("*.txt")):
            cid = lab.stem
            if cid in held_out:
                continue
            img = cv2.imread(str(SOURCE / v / "images" / f"{cid}.png"))
            if img is None:
                continue
            H, W = img.shape[:2]
            lines = [ln for ln in lab.read_text().splitlines() if ln.strip()]

            full_human = load_full_labels(cid, versions, names)
            hum_px = [(c, cx * W, cy * H, w * W, h * H) for (c, cx, cy, w, h) in full_human]
            ys = load_manifest_staff_lines(cid)
            dets = run_teacher(img, ys, REST_CLASSES, PROD_WEIGHTS, device=device)
            matches = match_detections(dets, hum_px)
            painted = img.copy()
            for mr in matches:
                if mr.matched_cls is not None:
                    continue  # already a labeled box of SOME class -- leave the ink alone
                x0, y0, x1, y1 = mr.det.bbox
                color = _paper_color(img, (x0, y0, x1, y1))
                cv2.rectangle(painted, (int(x0), int(y0)), (int(x1), int(y1)),
                              color, thickness=-1)
                n_painted += 1
                painted_by_class[mr.det.cls] = painted_by_class.get(mr.det.cls, 0) + 1
                painted_log.append({
                    "version": v, "cell_id": cid,
                    "orig_image_path": str(SOURCE / v / "images" / f"{cid}.png"),
                    "painted_image_path": str(out / v / "images" / f"{cid}.png"),
                    "cls": mr.det.cls, "conf": mr.det.conf,
                    "bbox_px": [x0, y0, x1, y1],
                })
            _write_cell(out, v, cid, lines, painted)
            n_cells += 1
    (out / "painted.json").write_text(json.dumps(painted_log, indent=1) + "\n")
    return {"cells": n_cells, "regions_painted": n_painted, "painted_by_class": painted_by_class}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--select-held-out", action="store_true")
    ap.add_argument("--n-held-out", type=int, default=90)
    ap.add_argument("--arm", choices=["baseline", "completed", "painted"])
    ap.add_argument("--out", type=Path)
    ap.add_argument("--device", default="mps")
    a = ap.parse_args()

    if a.select_held_out:
        select_held_out(a.n_held_out)
        return 0

    if not a.arm or not a.out:
        print("need --arm and --out (or --select-held-out first)")
        return 2

    held_out = _held_out_ids()
    if a.out.exists():
        shutil.rmtree(a.out)
    if a.arm == "baseline":
        stats = build_baseline(a.out, held_out)
    elif a.arm == "completed":
        stats = build_completed(a.out, held_out, a.device)
    else:
        stats = build_painted(a.out, held_out, a.device)

    versions_present = sorted({v for v, cid in _all_cells() if cid not in held_out})
    (a.out / "catalog-versions.txt").write_text("\n".join(versions_present) + "\n")
    stats["arm"] = a.arm
    stats["held_out_excluded"] = len(held_out)
    (a.out / "specialist.json").write_text(json.dumps(stats, indent=1) + "\n")
    print(f"wrote {a.arm} -> {a.out}: {json.dumps(stats, indent=1)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
