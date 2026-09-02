"""Score a measure cell by how much it looks like it contains a HOLLOW notehead.

A half or whole notehead is an ink ring with an enclosed white counter. So:
binarize the staff-line-removed crop, find the white connected components that
do NOT touch the border, and keep the ones whose size and shape match a
notehead counter at that cell's own staff spacing.

⚠️ This is NOT a detector and must not be used as one. `benchmarks/
omr-first-run-2026-08/DURATIONS.md` already measured that route: as a way of
PROPOSING boxes it gave 662 candidates for 68 real half notes and was
abandoned. What is being asked here is far weaker — *does this cell contain
any* — and one hole in the right size band is enough to make a cell worth a
human's minute even if two of three such cells turn out to hold a `p`, an `8`
or a slur crossing.

Validated in `validate_hollow_score.py` against the first round's 48 cells,
where Sean's own verdicts say which 25 hold a hollow head.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

#: A counter's area, as a fraction of one staff space SQUARED. A half-note
#: counter is roughly 0.55 x 0.35 staff spaces = 0.19; the band is wide because
#: bled ink shrinks it and a whole note's is larger than a half's.
MIN_HOLE_AREA_SPACES2 = 0.015
MAX_HOLE_AREA_SPACES2 = 0.60

#: A counter is wider than it is tall (the ring is slanted, the hole is a
#: lens). Rejects the tall thin gaps inside a bled `ff` or a bracket.
MIN_ASPECT = 0.55
MAX_ASPECT = 6.0


def staff_space(cell: dict) -> float:
    ys = cell.get("staff_line_ys_canonical") or []
    if len(ys) < 2:
        return 100.0
    diffs = [b - a for a, b in zip(ys, ys[1:]) if b > a]
    return float(np.median(diffs)) if diffs else 100.0


def score_cell(cell: dict, repo_root: Path) -> tuple[int, list[tuple[int, int, int, int]]]:
    """Return (n_candidate_counters, their bounding boxes)."""
    rel = cell.get("nostaff_png_path") or cell.get("cell_png_path")
    img = cv2.imread(str(repo_root / rel), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return 0, []
    sp = staff_space(cell)
    lo = MIN_HOLE_AREA_SPACES2 * sp * sp
    hi = MAX_HOLE_AREA_SPACES2 * sp * sp

    ink = (img < 128).astype(np.uint8)
    # Close small gaps so a counter that leaks through a hairline still counts
    # as enclosed. The kernel is a fraction of a staff space, not a fixed size,
    # because these editions differ 2x in scale.
    k = max(2, int(round(sp * 0.06)))
    ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))

    white = 1 - ink
    n, labels, stats, _ = cv2.connectedComponentsWithStats(white, connectivity=4)
    h, w = white.shape
    border = set(labels[0, :]) | set(labels[-1, :]) | set(labels[:, 0]) | set(labels[:, -1])

    boxes = []
    for i in range(1, n):
        if i in border:
            continue
        area = stats[i, cv2.CC_STAT_AREA]
        if not (lo <= area <= hi):
            continue
        bw = stats[i, cv2.CC_STAT_WIDTH]
        bh = stats[i, cv2.CC_STAT_HEIGHT]
        if bh == 0:
            continue
        ar = bw / bh
        if not (MIN_ASPECT <= ar <= MAX_ASPECT):
            continue
        # A counter is a fairly solid lens, not a ragged sliver.
        if area < 0.30 * bw * bh:
            continue
        boxes.append((int(stats[i, cv2.CC_STAT_LEFT]), int(stats[i, cv2.CC_STAT_TOP]),
                      int(bw), int(bh)))
    return len(boxes), boxes


def score_manifest(batch_dir: Path, repo_root: Path) -> list[dict]:
    cells = json.loads((batch_dir / "cells.json").read_text())
    out = []
    for c in cells:
        n, boxes = score_cell(c, repo_root)
        out.append({**c, "hollow_candidates": n, "hollow_boxes": boxes})
    return out
