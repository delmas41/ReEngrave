"""Where does clef coverage go? One rejecting branch per header cell.

`clef_ground_truth_eval.py` scores twelve staves against hand-read truth, which
is the number that matters and is far too small a sample to steer by. This
probe re-walks `clef_locator.locate_clef`'s own decision tree over a whole
sample of pages and reports which branch each header cell died on — so a change
can be aimed at the branch that actually holds the coverage, and its effect
read off directly.

It reads NO ground truth, so it says nothing about whether a located clef is
RIGHT. That is deliberate: precision is `clef_ground_truth_eval.py`'s job and
the two must be reported separately, because buying coverage with false
positives is the one trade this layer refuses. Always run both.

    python3 benchmarks/omr-clef-geometry/probe_clef_rejection.py \
        --pdf /Users/seanjohnson/Downloads/Nottebohm-Beethovens-Studien-1873.pdf

The branch names come from `locate_clef` itself, via its optional `trace`
out-parameter. This script used to re-walk the decision tree in a copy, which
kept measurement code out of the production path but meant every new exit in
`locate_clef` had to be mirrored here or cells would be miscounted as something
else — and the first change after it was written added two. The trace costs one
dict write on a path that is already doing connected-components analysis, and
it cannot drift.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402

from tools.omr.clef_locator import (  # noqa: E402
    DEFAULT_LOCATOR_CONFIG as CFG,
    locate_clef,
)
from tools.omr.measure_extractor import detect_barlines  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.staff_header import header_cells_for_page  # noqa: E402
from tools.omr.types import MeasureCell  # noqa: E402


# `locate_clef` names its exits tersely; these are the names this report has
# always used, kept so figures from older runs stay comparable.
BRANCH_NAMES = {
    "no_staff_metrics": "no staff metrics",
    "no_mask": "no ink mask",
    "no_clusters": "no clusters",
    "only_debris": "only debris",
    "too_far_right": "too far in",
    "too_big": "cluster too big",
    "asymmetric": "not symmetric",
    "f_clef_dots": "F-clef dot veto",
    "ambiguous_snap": "ambiguous line snap",
}


def classify(cell: MeasureCell) -> tuple[str, tuple[float, float] | None]:
    """The branch this cell dies on, and the (w, h) in staff spaces of the
    cluster that killed it where there is one."""
    trace: dict = {}
    found = locate_clef(cell, trace=trace)
    size = None
    if trace.get("w_spaces") is not None and trace.get("h_spaces") is not None:
        size = (trace["w_spaces"], trace["h_spaces"])
    if found is not None:
        return f"located ({found.read.name})", size
    reason = trace.get("reason", "unknown")
    return BRANCH_NAMES.get(reason, reason), size


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--first", type=int, default=20)
    ap.add_argument("--last", type=int, default=248)
    ap.add_argument("--every", type=int, default=12)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--per-cell", action="store_true",
                    help="one line per header cell, for diffing two commits")
    args = ap.parse_args()

    pdf = Path(args.pdf)
    if not pdf.exists():
        print(f"no PDF at {pdf}", file=sys.stderr)
        return 1

    tally: Counter[str] = Counter()
    too_big: list[tuple[float, float]] = []
    pages = 0
    for page_index in range(args.first, args.last + 1, args.every):
        try:
            rendered = render_page(pdf, page_index, dpi=args.dpi)
            pws = detect_barlines(detect_staves(rendered))
        except Exception as exc:
            print(f"  p{page_index}: skipped ({type(exc).__name__})")
            continue
        cells = header_cells_for_page(pws)
        if not cells:
            continue
        pages += 1
        for staff_index, cell in sorted(cells.items()):
            reason, size = classify(cell)
            tally[reason.split(" (")[0]] += 1
            if reason == "cluster too big" and size:
                too_big.append(size)
            if args.per_cell:
                dims = f"{size[0]:.2f}x{size[1]:.2f}" if size else "-"
                print(f"CELL p{page_index} s{staff_index} {reason} {dims}")

    total = sum(tally.values())
    if not total:
        print("no header cells measured", file=sys.stderr)
        return 1

    print(f"\n{total} header cells over {pages} pages of {pdf.name}\n")
    for reason, count in tally.most_common():
        print(f"  {count:>4}  {100.0 * count / total:>5.1f}%  {reason}")

    if too_big:
        widths = np.array([w for w, _ in too_big])
        heights = np.array([h for _, h in too_big])
        wide = int((widths > CFG.max_width_spaces).sum())
        tall = int((heights > CFG.max_height_spaces).sum())
        both = int(((widths > CFG.max_width_spaces)
                    & (heights > CFG.max_height_spaces)).sum())
        print(f"\n  of the {len(too_big)} fused clusters:")
        print(f"    too TALL only  {tall - both}")
        print(f"    too WIDE only  {wide - both}")
        print(f"    both           {both}")
        print(f"    width   median {np.median(widths):.1f}  max {widths.max():.1f}"
              f"   (limit {CFG.max_width_spaces})")
        print(f"    height  median {np.median(heights):.1f}  max {heights.max():.1f}"
              f"   (limit {CFG.max_height_spaces})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
