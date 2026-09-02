"""What the classical-CV beam detector emitted, component by component.

`probe_beam_levels.py` reads the shipped JSON, which carries only the YOLO
beams — the CV beams that actually drive the level count are computed inside
`transcribe` and never serialised. This one re-runs phase 1 and
`line_detection.detect_beams` on the same PDF and prints, per component:

  * the raw connected component (box, fill, aspect)
  * `_stacked_bar_count`'s answer, and the per-column run counts it took a
    median over
  * the sub-beams that were then emitted, and the gaps between their centres
  * the clustering tolerance in `rhythm` those gaps are compared against

    python3 benchmarks/omr-corpus-widening-2026-09/probe_cv_beams.py \
        --work mozart-sym41-mvt1 --staff 1 --measure 0

`--survey` instead walks every cell of every work given and emits one row per
BEAM COMPONENT — the distribution the constant has to sit in.

Host Python; needs cv2 + numpy (already required by the pipeline).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.line_detection import (  # noqa: E402
    _binary_ink, _staff_line_spacing, _attached_stem_count, _stacked_bar_count,
    detect_stems,
)
from tools.omr.measure_extractor import detect_barlines, extract_measures  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.staff_line_removal import remove_staff_lines  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def cells_for(pdf: Path, page: int, dpi: int):
    pg = render_page(pdf, page, dpi=dpi)
    pws = detect_staves(pg)
    detect_barlines(pws)
    cells = extract_measures(pws)
    remove_staff_lines(cells)      # transcribe.py:3669 — must match the real run
    return cells


def beam_components(cell, *, verbose=False):
    """Re-run detect_beams' pipeline, yielding the per-component evidence."""
    src = (cell.image_no_staff
           if getattr(cell, "image_no_staff", None) is not None else cell.image)
    if src is None or src.size == 0:
        return []
    sp = _staff_line_spacing(cell)
    if sp <= 1.0:
        return []
    stems = detect_stems(cell)
    ink = _binary_ink(src)
    kernel_w = max(3, int(round(sp * 1.5)))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_w, 1))
    opened = cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel)
    num, labels, stats, _ = cv2.connectedComponentsWithStats(opened, connectivity=8)

    min_w = int(round(sp * 1.5))
    min_h = max(2, int(round(sp * 0.10)))
    max_h = max(3, int(round(sp * 2.5)))
    tolerance = sp * 1.0
    end_reach = sp * 2.5
    anchors = [s for s in stems if s.height_canonical >= sp * 2.8]

    rows = []
    for i in range(1, num):
        x, y, w, h, area = stats[i]
        if w < min_w or h < min_h or h > max_h:
            continue
        if area < max(6, sp):
            continue
        if w / max(1, h) < 2.0:
            continue
        attached = _attached_stem_count(
            labels, i, anchors, x, y, w, h, sp, tolerance, end_reach)
        if attached < 2:
            continue
        n_bars = _stacked_bar_count(labels, i, x, y, w, h)
        # the column run-counts the median was taken over
        roi = labels[y:y + h, x:x + w] == i
        step = max(1, roi.shape[1] // 48)
        cols = roi[:, ::step]
        above = np.vstack([np.zeros((1, cols.shape[1]), dtype=bool), cols[:-1]])
        counts = (cols & ~above).sum(axis=0)
        counts = counts[counts > 0]
        rows.append(dict(
            spacing=sp, x=int(x), y=int(y), w=int(w), h=int(h),
            area=int(area), fill=area / max(1, w * h),
            attached=attached, n_bars=n_bars,
            col_counts=Counter(counts.tolist()),
            n_stems=len(stems), n_anchors=len(anchors),
            sub_gap=(h / n_bars) if n_bars else 0.0,
            h_spaces=h / sp,
        ))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work")
    ap.add_argument("--works", nargs="+")
    ap.add_argument("--fixtures", type=Path, default=FIXTURES)
    ap.add_argument("--staff", type=int)
    ap.add_argument("--measure", type=int)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--survey", action="store_true")
    ap.add_argument("--csv", type=Path)
    args = ap.parse_args()

    works = args.works or ([args.work] if args.work else [])
    out_rows = []
    for work in works:
        pdf = args.fixtures / f"{work}.pdf"
        cells = cells_for(pdf, 0, args.dpi)
        for cell in cells:
            si = getattr(cell, "staff_index", None)
            mi = getattr(cell, "measure_index", None)
            if args.staff is not None and si != args.staff:
                continue
            if args.measure is not None and mi != args.measure:
                continue
            rows = beam_components(cell)
            if not rows:
                continue
            if not args.survey:
                print(f"\n=== {work} staff {si} m{mi}  spacing={rows[0]['spacing']:.1f} "
                      f" rhythm tol=0.35*sp={rows[0]['spacing'] * 0.35:.1f}"
                      f"  stems={rows[0]['n_stems']} anchors={rows[0]['n_anchors']}")
            for r in rows:
                r.update(work=work, staff=si, measure=mi)
                out_rows.append(r)
                if not args.survey:
                    print(f"  COMP x={r['x']:5d}..{r['x'] + r['w']:5d} "
                          f"y={r['y']:5d}..{r['y'] + r['h']:5d} h={r['h']:4d} "
                          f"({r['h_spaces']:.2f} sp) fill={r['fill']:.2f} "
                          f"stems={r['attached']} -> n_bars={r['n_bars']} "
                          f"sub_gap={r['sub_gap']:.1f}px "
                          f"({r['sub_gap'] / r['spacing']:.2f} sp)  "
                          f"cols={dict(sorted(r['col_counts'].items()))}")

    if args.survey:
        print(f"\n{len(out_rows)} beam components over {len(works)} works")
        by_bars = Counter(r["n_bars"] for r in out_rows)
        print("  n_bars:", dict(sorted(by_bars.items())))
    if args.csv:
        import csv
        with open(args.csv, "w", newline="") as fh:
            wtr = csv.writer(fh)
            wtr.writerow(["work", "staff", "measure", "spacing", "x", "y", "w", "h",
                          "h_spaces", "fill", "attached", "n_bars", "sub_gap_sp",
                          "col_counts"])
            for r in out_rows:
                wtr.writerow([r["work"], r["staff"], r["measure"],
                              f"{r['spacing']:.2f}", r["x"], r["y"], r["w"], r["h"],
                              f"{r['h_spaces']:.4f}", f"{r['fill']:.4f}",
                              r["attached"], r["n_bars"],
                              f"{r['sub_gap'] / r['spacing']:.4f}",
                              ";".join(f"{k}:{v}" for k, v in
                                       sorted(r["col_counts"].items()))])
        print(f"wrote {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
