#!/usr/bin/env python3
"""Score a measure cell by how much it looks like it contains GRACE NOTES —
the survey's Row 2 selector (SURVEY_DESIGN.md §4 named the signal; this is it).

A grace note is a SMALL filled notehead standing near a full-sized one: the
DSv2 classes (`graceNote*`, `notehead*Small`) render at roughly 0.6x the
normal head, and every one of them has ZERO labeled boxes — a total blind
spot. So the signal is two ink populations in one cell:

    full head:   a solid oval about 1.0 staff space tall
    grace head:  the same oval at about 0.5-0.75 of a space, within a few
                 spaces of a full head (grace notes attach to a host)

Like `hollow_score.py`, this is a RANKER, not a detector: one plausible
grace-sized head is enough to make a cell worth a human's minute, and the
candidate boxes it draws are audit aids, never labels.

Stems are snapped off with a morphological opening (an ellipse a quarter of a
staff space across removes 0.06-0.12-space stem strokes while keeping head
mass), then connected components are filtered by fill, aspect and height in
STAFF SPACES — every threshold is expressed in the cell's own measured
spacing, never pixels.

    # 1. does a grace-sized population exist in this pool at all?
    python3 grace_score.py --measure --repo <pixel-root> M1/cells.json M2/cells.json ...

    # 2. rank cells (TSV to stdout), and render the top N for a visual audit
    python3 grace_score.py --repo <pixel-root> --annotate-top 8 --out-dir /tmp/audit M/cells.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

# Head-shaped ink, in staff spaces (the measurement band is deliberately
# wider than the decision bands so --measure can SEE both populations).
#
# CALIBRATED 2026-09-03 against the first 30 labeled grace heads
# (benchmarks/omr-labeling-grace2-2026-09, Mahler 5 / Peters): the ink
# components under Sean's boxes measure h 0.56-1.34 spaces (the >1.0 tail is
# beamed grace RUNS — the opening cannot detach a small head from its thin
# grace stem, so a run arrives as ONE component), aspect 0.54-1.44 (mostly
# BELOW 1: taller than wide, same merging), fill 0.53-0.85. The original
# convention bands (0.45-0.78 / aspect >= 0.95) passed only 2 of the 30.
# Chosen by cell-level confusion against those labels (variant A of three
# measured): GRACE_H (0.50, 0.95) + aspect >= 0.50 scores RECALL 1.00 (all
# 15 labeled grace cells fire) at precision 0.19; the original convention
# bands scored recall 0.53. Widening past 0.95 only adds false positives —
# cells holding a merged run always also hold a <= 0.95 component.
FILL_MIN = 0.50          # measured min 0.53
ASPECT_MIN, ASPECT_MAX = 0.50, 2.4   # merged head+stem is taller than wide
MEASURE_H = (0.30, 1.60)
GRACE_H = (0.50, 0.95)   # single grace heads measure 0.56-0.94 here
FULL_H = (0.85, 1.30)
HOST_MAX_SPACES = 3.0    # a grace head must stand near a full head


def staff_space(cell: dict) -> float:
    ys = cell.get("staff_line_ys_canonical") or []
    diffs = [b - a for a, b in zip(ys, ys[1:]) if b > a]
    return float(np.median(diffs)) if diffs else 100.0


def head_blobs(img: np.ndarray, sp: float) -> list[tuple[float, float, float, int, int, int, int]]:
    """(height_spaces, cx, cy, x, y, w, h) for every head-shaped component."""
    ink = (img < 128).astype(np.uint8)
    d = max(3, int(round(0.25 * sp)))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d, d))
    opened = cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel)
    n, _, stats, centroids = cv2.connectedComponentsWithStats(opened, connectivity=8)
    out = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if h == 0 or w == 0:
            continue
        h_sp = h / sp
        if not (MEASURE_H[0] <= h_sp <= MEASURE_H[1]):
            continue
        if not (ASPECT_MIN <= w / h <= ASPECT_MAX):
            continue
        if area / (w * h) < FILL_MIN:
            continue
        out.append((h_sp, centroids[i][0], centroids[i][1], x, y, w, h))
    return out


def score_cell(cell: dict, pixel_root: Path):
    """(n_grace_candidates_near_a_host, grace_boxes, full_boxes, all_heights)."""
    rel = cell.get("nostaff_png_path") or cell.get("cell_png_path")
    img = cv2.imread(str(pixel_root / rel), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return 0, [], [], []
    sp = staff_space(cell)
    blobs = head_blobs(img, sp)
    fulls = [b for b in blobs if FULL_H[0] <= b[0] <= FULL_H[1]]
    graces = []
    for b in blobs:
        if not (GRACE_H[0] <= b[0] <= GRACE_H[1]):
            continue
        near = any(
            ((b[1] - f[1]) ** 2 + (b[2] - f[2]) ** 2) ** 0.5 <= HOST_MAX_SPACES * sp
            for f in fulls)
        if near:
            graces.append(b)
    return (len(graces),
            [b[3:7] for b in graces],
            [b[3:7] for b in fulls],
            [b[0] for b in blobs])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifests", nargs="+", type=Path)
    ap.add_argument("--repo", type=Path, required=True,
                    help="root the manifests' png paths resolve against "
                         "(the checkout where the gitignored cell PNGs exist)")
    ap.add_argument("--measure", action="store_true",
                    help="print the head-height histogram instead of ranking")
    ap.add_argument("--annotate-top", type=int, default=0)
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args()

    cells = []
    for mp in args.manifests:
        for cell in json.loads(mp.read_text()):
            cells.append(cell)

    if args.measure:
        heights: list[float] = []
        for cell in cells:
            heights.extend(score_cell(cell, args.repo)[3])
        if not heights:
            print("no head-shaped ink found at all")
            return
        heights.sort()
        print(f"{len(heights)} head-shaped blobs over {len(cells)} cells")
        lo, hi, step = 0.30, 1.40, 0.05
        edges = [round(lo + i * step, 2) for i in range(int((hi - lo) / step) + 1)]
        for a, b in zip(edges, edges[1:]):
            n = sum(1 for h in heights if a <= h < b)
            marker = " <- GRACE band" if GRACE_H[0] <= a < GRACE_H[1] else (
                     " <- FULL band" if FULL_H[0] <= a < FULL_H[1] else "")
            print(f"  {a:.2f}-{b:.2f}  {n:5d}  {'#' * min(n, 60)}{marker}")
        return

    ranked = []
    for cell in cells:
        n, graces, fulls, _ = score_cell(cell, args.repo)
        ranked.append((n, len(fulls), cell, graces))
    ranked.sort(key=lambda r: -r[0])

    print("grace_candidates\tfull_heads\tcell_id")
    for n, nf, cell, _ in ranked:
        if n:
            print(f"{n}\t{nf}\t{cell['cell_id']}")
    n_hit = sum(1 for r in ranked if r[0])
    print(f"# {n_hit}/{len(cells)} cells carry any grace candidate")

    if args.annotate_top and args.out_dir:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        for n, nf, cell, graces in ranked[:args.annotate_top]:
            if n == 0:
                break
            rel = cell.get("nostaff_png_path") or cell.get("cell_png_path")
            img = cv2.imread(str(args.repo / rel))
            for x, y, w, h in graces:
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 3)
            out = args.out_dir / f"{n:02d}_{cell['cell_id']}.png"
            cv2.imwrite(str(out), img)
            print(f"# wrote {out}")


if __name__ == "__main__":
    main()
