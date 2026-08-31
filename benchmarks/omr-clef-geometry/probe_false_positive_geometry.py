"""Where does the ink a false positive is made of actually SIT?

The false positives this layer has left are not one failure. Scored against the
two sweep corpora they split cleanly in two, and only one of them is about
whether a glyph looks like a C clef:

  * a real clef misread — an F clef, or a fragment of a G clef, that survives
    the shape gates. This is the veto's problem, and symmetry is the axis
    everything has tried to separate it on.
  * ink that is not a clef at all. Edition Peters prints the stacked instrument
    numbers (1/2, 1/2/3) and the brace's curl to the LEFT of the system's
    bracket, close enough to fall inside the header window; a stack of two or
    three numerals is glyph-sized and vertically symmetric, and the locator
    takes the leftmost glyph-sized cluster, so it takes those.

No symmetry threshold can tell the second family apart, because the numerals
really are symmetric. But their POSITION is decisive in a way their shape is
not: a clef is printed ON the staff, and those numerals are printed before the
staff begins. This probe measures that, per corpus, for the reads that are real
C clefs against the reads that are not.

    python3 benchmarks/omr-clef-geometry/probe_false_positive_geometry.py

"Before the staff" is measured against where the staff's own five lines start
inside the header cell — the leftmost column that survives an opening with a
wide, one-pixel-tall kernel, the same operator `header_ink.strip_horizontal_
rules` uses to find the lines. It reads NO shape gate and proposes no change;
it says how much of the problem a position rule could reach.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from tools.omr.clef_locator import locate_clef  # noqa: E402
from tools.omr.header_ink import staff_metrics  # noqa: E402
from tools.omr.measure_extractor import (  # noqa: E402
    detect_barlines,
    extract_measures,
    resegment_fused_measures,
)
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.staff_header import header_cells_for_page  # noqa: E402
from tools.omr.staff_line_removal import remove_staff_lines  # noqa: E402
from tools.omr.types import MeasureCell  # noqa: E402

DEFAULT_SPECS = ("beethoven5-clef-sweep.json", "mahler5-clef-sweep.json")


def staff_left_column(cell: MeasureCell, spacing: float) -> int | None:
    """The column where this staff's printed lines begin, in cell pixels.

    Deliberately taken from `cell.image` and not `image_no_staff`: the lines
    ARE the measurement here, and on the prints this locator exists for the
    removal leaves most of them behind anyway.
    """
    img = cell.image
    if img is None or img.size == 0:
        return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    _, mask = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
    k = max(3, int(round(1.5 * spacing)))
    horiz = cv2.morphologyEx(
        mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (k, 1))
    )
    # Not the leftmost horizontal ink — the leftmost STAFF LINE. Those differ,
    # and the difference is the whole measurement: at the canonical scale a
    # bold serif's crossbar clears a 1.5-space opening, so the instrument name
    # and the stacked numerals leave fragments at the very left of the window
    # and the first measurement said every staff began at column 0. A staff
    # line is the one horizontal that runs the width of the cell, so length is
    # what identifies it.
    n, _labels, stats, _c = cv2.connectedComponentsWithStats(horiz, connectivity=8)
    lines = [stats[i, cv2.CC_STAT_LEFT] for i in range(1, n)
             if stats[i, cv2.CC_STAT_WIDTH] >= 4 * spacing]
    return int(min(lines)) if lines else None


def resolve_pdf(spec: dict) -> Path:
    path = Path(spec["pdf"]).expanduser()
    return path if path.is_absolute() else (REPO / path)


def report(spec_path: Path, dpi: int, verbose: bool) -> None:
    spec = json.loads(spec_path.read_text())
    pdf = resolve_pdf(spec)
    print(f"\n{spec_path.name} — {spec['source']}")
    if not pdf.exists():
        print(f"  skipped, no score at {pdf}")
        return

    by_page: dict[int, list[dict]] = defaultdict(list)
    for row in spec["staves"]:
        by_page[row["page"]].append(row)

    # "real" / "misread" -> list of (gap in staff spaces, label)
    gaps: dict[str, list[tuple[float, str]]] = {"real": [], "misread": []}
    for page_index in sorted(by_page):
        page = render_page(pdf, page_index, dpi=dpi)
        pws = detect_barlines(detect_staves(page))
        remove_staff_lines(resegment_fused_measures(pws, extract_measures(pws)))
        cells = header_cells_for_page(pws)
        for row in by_page[page_index]:
            cell = cells.get(row["staff"])
            if cell is None:
                continue
            found = locate_clef(cell)
            if found is None:
                continue
            metrics = staff_metrics(cell)
            if metrics is None:
                continue
            spacing = metrics[0]
            left = staff_left_column(cell, spacing)
            if left is None:
                continue
            x, _y, w, _h = found.bbox
            # Positive: the whole cluster ends before the staff's lines start.
            gap = (left - (x + w)) / spacing
            bucket = "real" if row["c_clef"] else "misread"
            gaps[bucket].append((gap, f"p{row['page']} s{row['staff']}"))
            if verbose:
                print(f"    {'C   ' if row['c_clef'] else 'NOT '}"
                      f"p{page_index:>3} s{row['staff']:<3} "
                      f"gap {gap:+.2f} spaces  {found.read.name}")

    for bucket in ("real", "misread"):
        vals = sorted(g for g, _ in gaps[bucket])
        if not vals:
            print(f"  {bucket:<8} none")
            continue
        before = [g for g in vals if g > 0]
        print(f"  {bucket:<8} {len(vals):>3} reads   "
              f"median {np.median(vals):+.2f}  range [{vals[0]:+.2f}, {vals[-1]:+.2f}]"
              f"   ENTIRELY BEFORE the staff: {len(before)}")
    real_before = sum(1 for g, _ in gaps["real"] if g > 0)
    bad_before = sum(1 for g, _ in gaps["misread"] if g > 0)
    if gaps["misread"]:
        print(f"  a rule refusing ink that ends before the staff would remove "
              f"{bad_before} of {len(gaps['misread'])} false positives "
              f"and cost {real_before} of {len(gaps['real'])} real clefs")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--spec", type=Path, action="append",
                    help="sweep corpus JSON; repeatable. Default: every one.")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--per-staff", action="store_true", help="one line per read")
    args = ap.parse_args()
    for spec in (args.spec or [HERE / n for n in DEFAULT_SPECS]):
        report(spec, args.dpi, args.per_staff)
    print("\nThis measures a CEILING, not a fix. Nothing here is shipped, and a "
          "position\nrule would have to clear both harnesses on both editions "
          "before it could be.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
