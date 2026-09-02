"""Where is the ink above the first staff, and can a distance tell a tempo
mark from a title?

This is the probe that decided `direction_text.BandConfig.above_spaces` — and,
more usefully, decided that no value of it would do the job on its own. It
prints every contiguous run of ink above the topmost staff of a page, measured
in staff spaces above that staff's top line, and the answer is that the runs
for `Allegro con brio` and for `Symphonie No. 5` overlap.

    python3 -m benchmarks.omr-direction-text-2026-09.probe_direction_bands
    python3 benchmarks/omr-direction-text-2026-09/probe_direction_bands.py \\
        benchmarks/omr-orchestral-e2e/fixtures/brahms-sym1-mvt1.pdf

It also reports the same for the gap BELOW each staff, which is the band that
does work — bounded on both sides by staves, and therefore not a question of
how far to reach.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.omr.preprocessing import render_page          # noqa: E402
from tools.omr.staff_detector import detect_staves       # noqa: E402

FIXTURES = ROOT / "benchmarks" / "omr-orchestral-e2e" / "fixtures"
DEFAULT_PDFS = ("brahms-sym1-mvt1", "beethoven-sym5-mvt1", "mahler-sym5-mvt1")

#: Ink runs closer together than this are reported as one — a printed line of
#: text has interior gaps between its ascenders and its body.
MERGE_GAP_PX = 4


def ink_runs(mask: np.ndarray) -> list[tuple[int, int, int]]:
    """`(y_start, y_end, widest_row)` for each contiguous band of inked rows."""
    rows = (mask > 0).sum(axis=1)
    runs, start = [], None
    for y in range(len(rows) + 1):
        inked = y < len(rows) and rows[y] > 0
        if inked and start is None:
            start = y
        elif not inked and start is not None:
            runs.append((start, y - 1, int(rows[start:y].max())))
            start = None
    merged: list[tuple[int, int, int]] = []
    for run in runs:
        if merged and run[0] - merged[-1][1] <= MERGE_GAP_PX:
            previous = merged.pop()
            merged.append((previous[0], run[1], max(previous[2], run[2])))
        else:
            merged.append(run)
    return merged


def report(pdf: Path, dpi: int, reach_spaces: float) -> None:
    page = render_page(pdf, 0, dpi=dpi)
    pws = detect_staves(page)
    if not pws.staves:
        print(f"{pdf.name}: no staves")
        return
    staves = sorted(pws.staves, key=lambda s: s.top_y)
    gray = (cv2.cvtColor(page.rgb, cv2.COLOR_BGR2GRAY)
            if page.rgb.ndim == 3 else page.rgb)
    _, mask = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)

    top = staves[0]
    spacing = top.line_spacing_px
    print(f"\n=== {pdf.name}  {len(staves)} staves  spacing {spacing:.1f} px")
    print(f"  above staff 0 (top line y={top.top_y}), x {top.x_start}-{top.x_end}:")
    for y0, y1, widest in ink_runs(mask[:top.top_y, top.x_start:top.x_end]):
        print(f"    {(top.top_y - y1) / spacing:6.1f} to "
              f"{(top.top_y - y0) / spacing:5.1f} spaces above   "
              f"widest row {widest:5d} px")
    print(f"  (a reach of {reach_spaces} spaces takes everything under "
          f"{reach_spaces:.1f})")

    print("  below each staff, gap to the next:")
    for a, b in zip(staves, staves[1:]):
        gap = (b.top_y - a.bottom_y) / a.line_spacing_px
        print(f"    staff {a.staff_index:2d} -> {b.staff_index:2d}: "
              f"{gap:5.2f} spaces")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdfs", nargs="*", type=Path,
                    default=[FIXTURES / f"{name}.pdf" for name in DEFAULT_PDFS])
    ap.add_argument("--dpi", type=int, default=600,
                    help="must match the pipeline's, or the spaces do not "
                         "correspond to what the reader sees")
    ap.add_argument("--reach", type=float, default=8.0,
                    help="the above_spaces value to annotate the report with")
    args = ap.parse_args(argv)
    for pdf in args.pdfs:
        if not pdf.is_file():
            print(f"missing: {pdf}", file=sys.stderr)
            continue
        report(pdf, args.dpi, args.reach)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
