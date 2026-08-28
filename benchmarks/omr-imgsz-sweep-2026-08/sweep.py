#!/usr/bin/env python3
"""How much does `imgsz` change detection, and is the real variable cell SIZE?

The whole-pipeline rerun (benchmarks/omr-real-world/RESULTS-2026-08-28.md) found
`imgsz` swinging noteheads 11x on handel-reduction p20 — 246 at 1280 against
2799 at 2048 — where six cells counted by eye give 2.7 noteheads/cell, matching
1280 and refuting 2048. The hypothesis is that cells are canonically rescaled
before detection, so `imgsz` sets an **upscale ratio**, not an absolute size: a
narrow cell blown up to 2048 makes the detector fire on texture.

This tests it against real ground truth — the 161 hand-labeled cells in
`data/user-labeled/` — rather than against a count by eye.

Matching is by CENTRE, not IoU: notehead boxes are a few pixels across and box
regression is loose, so IoU understates agreement that a human would call
correct. A prediction matches a ground-truth box when its centre lies inside
that box (grown by `--tol` of its own size), one-to-one, nearest first.

Usage:
    python3 benchmarks/omr-imgsz-sweep-2026-08/sweep.py
    python3 benchmarks/omr-imgsz-sweep-2026-08/sweep.py --sizes 1280 2048 --limit 40
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

ROOT = Path("/Users/seanjohnson/Desktop/ReEngrave")
LABELED = ROOT / "data" / "user-labeled"
WEIGHTS = ROOT / "omr-weights" / "deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt"
VERSIONS = ("v1-2026-05-18-orchestral", "v2-2026-06-08-beet5",
            "v3-2026-06-09-mahler5", "v4-2026-06-10-la-mer")

# Production settings from tools/omr/transcribe.py, so only imgsz varies.
CONF, IOU, AGNOSTIC = 0.25, 0.5, True


def load_cells(limit: int | None) -> list[tuple[str, Path, Path]]:
    out = []
    for version in VERSIONS:
        images, labels = LABELED / version / "images", LABELED / version / "labels"
        if not images.is_dir():
            continue
        for img in sorted(images.iterdir()):
            lab = labels / (img.stem + ".txt")
            if img.exists() and lab.exists():
                out.append((version, img, lab))
    return out[:limit] if limit else out


def read_labels(path: Path, w: int, h: int, notehead_ids: set[int]):
    """Ground-truth boxes in pixels: [(x0, y0, x1, y1, is_notehead)]."""
    boxes = []
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) != 5:
            continue
        cid = int(parts[0])
        cx, cy, bw, bh = (float(p) for p in parts[1:])
        boxes.append((
            (cx - bw / 2) * w, (cy - bh / 2) * h,
            (cx + bw / 2) * w, (cy + bh / 2) * h,
            cid in notehead_ids,
        ))
    return boxes


def match(preds, truth, tol: float):
    """One-to-one centre matching, nearest first. Returns (tp, fp, fn)."""
    used = set()
    tp = 0
    pairs = []
    for pi, (px, py) in enumerate(preds):
        for ti, (x0, y0, x1, y1, _nh) in enumerate(truth):
            gw, gh = x1 - x0, y1 - y0
            if (x0 - gw * tol <= px <= x1 + gw * tol
                    and y0 - gh * tol <= py <= y1 + gh * tol):
                cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                pairs.append((abs(px - cx) + abs(py - cy), pi, ti))
    pairs.sort()
    matched_p = set()
    for _d, pi, ti in pairs:
        if pi in matched_p or ti in used:
            continue
        matched_p.add(pi)
        used.add(ti)
        tp += 1
    return tp, len(preds) - tp, len(truth) - tp


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", type=int, nargs="+",
                    default=[640, 960, 1280, 1600, 2048])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--tol", type=float, default=0.5)
    ap.add_argument("--out", default=str(Path(__file__).parent / "results.json"))
    args = ap.parse_args()

    import yaml
    from ultralytics import YOLO

    names = yaml.safe_load((LABELED / "catalog.yaml").read_text())["names"]
    notehead_ids = {i for i, n in enumerate(names)
                    if isinstance(n, str) and n.lower().startswith("notehead")}

    cells = load_cells(args.limit)
    print(f"{len(cells)} hand-labeled cells, weights={WEIGHTS.name}")
    print(f"conf={CONF} iou={IOU} agnostic_nms={AGNOSTIC}, centre-match tol={args.tol}\n")

    model = YOLO(str(WEIGHTS))
    from PIL import Image

    rows, per_cell = [], []
    for imgsz in args.sizes:
        TP = FP = FN = 0
        gt_total = 0
        for _version, img_path, lab_path in cells:
            with Image.open(img_path) as im:
                w, h = im.size
            truth = [b for b in read_labels(lab_path, w, h, notehead_ids) if b[4]]
            gt_total += len(truth)
            res = model.predict(str(img_path), conf=CONF, iou=IOU,
                                agnostic_nms=AGNOSTIC, imgsz=imgsz, verbose=False)[0]
            preds = []
            for b, c in zip(res.boxes.xyxy.tolist(), res.boxes.cls.tolist()):
                if int(c) in notehead_ids:
                    preds.append(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2))
            tp, fp, fn = match(preds, truth, args.tol)
            TP += tp; FP += fp; FN += fn
            per_cell.append({"imgsz": imgsz, "cell": img_path.name,
                             "cell_w": w, "cell_h": h,
                             "upscale": round(imgsz / max(w, h), 2),
                             "tp": tp, "fp": fp, "fn": fn, "gt": len(truth)})
        prec = TP / (TP + FP) if TP + FP else 0.0
        rec = TP / (TP + FN) if TP + FN else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        rows.append({"imgsz": imgsz, "tp": TP, "fp": FP, "fn": FN,
                     "gt": gt_total, "precision": round(prec, 3),
                     "recall": round(rec, 3), "f1": round(f1, 3)})
        print(f"  imgsz {imgsz:5d}: P {prec:.3f}  R {rec:.3f}  F1 {f1:.3f}   "
              f"TP {TP:5d}  FP {FP:6d}  FN {FN:5d}   (GT {gt_total})")

    Path(args.out).write_text(json.dumps(
        {"summary": rows, "per_cell": per_cell}, indent=2))

    # Is the real variable the UPSCALE RATIO rather than imgsz?
    print("\nfalse positives per cell, bucketed by upscale ratio (imgsz / cell long edge):")
    buckets: dict[str, list[int]] = {}
    for r in per_cell:
        u = r["upscale"]
        key = ("<=1" if u <= 1 else "1-2" if u <= 2 else "2-4" if u <= 4 else ">4")
        buckets.setdefault(key, []).append(r["fp"])
    for key in ("<=1", "1-2", "2-4", ">4"):
        vals = buckets.get(key)
        if vals:
            print(f"   upscale {key:4s}: median FP/cell {statistics.median(vals):6.1f}   "
                  f"mean {statistics.mean(vals):7.1f}   (n={len(vals)})")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
