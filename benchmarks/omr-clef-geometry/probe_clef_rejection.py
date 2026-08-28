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

The branch names below mirror the `return None` / `continue` sites in
`locate_clef` one for one. If that function grows a new exit, this needs the
matching arm or cells will be miscounted as something else — the probe
duplicates the walk rather than instrumenting it in place, so that the
production path carries no measurement code.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from tools.omr.clef_geometry import DEFAULT_CONFIG as GEOMETRY, resolve_clef  # noqa: E402
from tools.omr.clef_locator import (  # noqa: E402
    DEFAULT_LOCATOR_CONFIG as CFG,
    _analysis_scale,
    _cluster_components,
    _has_f_clef_dots,
    _ink_mask,
    _refine_symmetry_axis,
    _staff_metrics,
)
from tools.omr.measure_extractor import detect_barlines  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.staff_header import header_cells_for_page  # noqa: E402
from tools.omr.types import MeasureCell  # noqa: E402


def classify(cell: MeasureCell) -> tuple[str, tuple[float, float] | None]:
    """The branch this cell dies on, and the (w, h) in staff spaces of the
    cluster that killed it where there is one."""
    metrics = _staff_metrics(cell)
    if metrics is None:
        return "no staff metrics", None
    spacing, top_y, bottom_y = metrics
    mask = _ink_mask(cell, spacing, CFG)
    if mask is None:
        return "no ink mask", None

    scale = _analysis_scale(spacing, CFG)
    spacing *= scale
    top_y *= scale
    bottom_y *= scale
    staff_line_ys = [y * scale for y in sorted(cell.staff_line_ys_canonical)]

    hw = max(1, int(round(mask.shape[1] * CFG.header_frac)))
    strip = mask[:, :hw]
    n, _labels, stats, _cent = cv2.connectedComponentsWithStats(strip, connectivity=8)

    min_area = CFG.min_component_area_spaces * spacing * spacing
    band_margin = CFG.staff_band_spaces * spacing
    band_top, band_bottom = top_y - band_margin, bottom_y + band_margin
    boxes = []
    for i in range(1, n):
        if int(stats[i, cv2.CC_STAT_AREA]) < min_area:
            continue
        y_i = int(stats[i, cv2.CC_STAT_TOP])
        h_i = int(stats[i, cv2.CC_STAT_HEIGHT])
        if not (band_top <= y_i + h_i / 2.0 <= band_bottom):
            continue
        boxes.append((
            int(stats[i, cv2.CC_STAT_LEFT]), y_i,
            int(stats[i, cv2.CC_STAT_WIDTH]), h_i, int(stats[i, cv2.CC_STAT_AREA]),
        ))
    if not boxes:
        return "no clusters", None

    saw_any = False
    for bbox in _cluster_components(boxes, max_gap=CFG.cluster_gap_spaces * spacing):
        x, y, w, h = bbox
        w_sp, h_sp = w / spacing, h / spacing
        saw_any = True
        if x / spacing > CFG.max_start_spaces:
            return "too far in", (w_sp, h_sp)
        if h_sp > CFG.max_height_spaces or w_sp > CFG.max_width_spaces:
            return "cluster too big", (w_sp, h_sp)
        if w_sp < CFG.min_width_spaces or h_sp < CFG.min_height_spaces:
            continue
        ink = int(np.count_nonzero(strip[y : y + h, x : x + w]))
        if w * h == 0 or ink / float(w * h) < CFG.min_ink_fraction:
            continue
        axis_y, symmetry = _refine_symmetry_axis(
            strip, bbox, max_shift=CFG.axis_refine_spaces * spacing
        )
        if symmetry < CFG.min_symmetry:
            return "not symmetric", (w_sp, h_sp)
        if _has_f_clef_dots(strip, bbox, spacing, CFG):
            return "F-clef dot veto", (w_sp, h_sp)
        read = resolve_clef("cClefAlto", anchor_y=axis_y,
                            staff_line_ys=staff_line_ys, config=GEOMETRY)
        if read is None or read.source != "geometry":
            return "ambiguous line snap", (w_sp, h_sp)
        return f"located ({read.name})", (w_sp, h_sp)
    return ("only debris" if saw_any else "no clusters"), None


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
