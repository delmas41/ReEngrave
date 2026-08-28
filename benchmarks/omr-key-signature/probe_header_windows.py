"""Does the measured header window actually contain the staff's clef?

The whole header layer — the clef readers and the key-signature reader alike —
rests on one property of `staff_header.measure_header_window`: that the window
it measures holds the header. `eval_key_signatures.py` scores the READING
against hand-read ground truth, which is the number that matters but exists for
only three pages. This probe scores the WINDOW, needs no ground truth at all,
and so can run over as much of the corpus as you have patience for.

The proxy is deliberately narrow: a staff counts when a clef-sized ink cluster
stands at the head of its window, by the same two measures
`key_signature_locator` uses to pick its anchor. That is not "the clef was read
correctly" — it is "the clef is in the picture", which is the precondition
everything downstream needs and the thing a Phase-1 geometry change breaks.

    python3 benchmarks/omr-key-signature/probe_header_windows.py --scores 20 --pages 3

To compare two commits, run it in a worktree of each and diff the totals —
there is no built-in "before" mode, because the before is whatever you are
comparing against:

    git worktree add --detach /tmp/before <commit>
    (cd /tmp/before && python3 benchmarks/omr-key-signature/probe_header_windows.py …)

Measured this way across 26 pages of 20 scores (Beethoven symphonies 1-9, the
gitignored IMSLP corpus), the clamp in `staff_header._anchor_column` that
stopped `x_start` under-running into the instrument names moved the figure from
186/455 staves to 233/455. One page of the 26 went backwards, by one staff.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import cv2  # noqa: E402

from tools.omr.header_ink import (  # noqa: E402
    DEFAULT_INK_CONFIG,
    cluster_components_2d,
    header_ink_mask,
    staff_metrics,
)
from tools.omr.key_signature_locator import DEFAULT_LOCATOR_CONFIG as LOC  # noqa: E402
from tools.omr.measure_extractor import detect_barlines  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.staff_header import header_cells_for_page  # noqa: E402
from tools.omr.types import MeasureCell  # noqa: E402

# The corpus is gitignored; a machine without it gets a clear message, not a
# traceback.
CORPUS = REPO / "tools" / "omr" / "training" / "data" / "imslp"

# The two measures that make an oversized cluster the CLEF rather than some
# other large piece of ink — `key_signature_locator`'s
# `clef_anchor_max_start_spaces` and `clef_anchor_min_height_spaces`.
#
# Restated here rather than imported, so the probe runs unchanged against a
# commit from before those knobs existed. That is the whole point of it: the
# before/after in the docstring was measured by checking out the earlier commit
# in a worktree and running THIS file there. Keep the two in step by hand; the
# locator's config is the source of truth.
CLEF_AT_HEAD_MAX_START_SPACES = 5.50
CLEF_AT_HEAD_MIN_HEIGHT_SPACES = 1.80


def _clef_at_head(cell: MeasureCell) -> bool | None:
    """Whether a clef-sized cluster stands at the head of this header cell.

    Deliberately the same two measures `key_signature_locator` anchors on —
    see `CLEF_AT_HEAD_MAX_START_SPACES` for why they are restated rather than
    imported.
    """
    metrics = staff_metrics(cell)
    if metrics is None:
        return None
    spacing, top_y, bottom_y = metrics
    mask = header_ink_mask(cell, spacing, cell.staff_line_ys_canonical, DEFAULT_INK_CONFIG)
    if mask is None:
        return None

    n, _labels, stats, _cent = cv2.connectedComponentsWithStats(mask, connectivity=8)
    min_area = LOC.min_component_area_spaces * spacing * spacing
    margin = LOC.staff_band_spaces * spacing
    components = []
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] < min_area:
            continue
        y = int(stats[i, cv2.CC_STAT_TOP])
        h = int(stats[i, cv2.CC_STAT_HEIGHT])
        if not (top_y - margin <= y + h / 2.0 <= bottom_y + margin):
            continue
        components.append((
            int(stats[i, cv2.CC_STAT_LEFT]), y,
            int(stats[i, cv2.CC_STAT_WIDTH]), h, int(stats[i, cv2.CC_STAT_AREA]),
        ))

    for x, _y, w, h in cluster_components_2d(
        components, max_gap=LOC.cluster_gap_spaces * spacing
    ):
        w_sp, h_sp = w / spacing, h / spacing
        oversized = h_sp >= LOC.clef_min_height_spaces or w_sp > LOC.max_width_spaces
        if (oversized
                and x <= CLEF_AT_HEAD_MAX_START_SPACES * spacing
                and h_sp >= CLEF_AT_HEAD_MIN_HEIGHT_SPACES):
            return True
    return False


def _score_page(pdf: Path, page_index: int, dpi: int) -> tuple[int, int]:
    rendered = render_page(pdf, page_index, dpi=dpi)
    pws = detect_barlines(detect_staves(rendered))
    if not pws.staves:
        return 0, 0
    cells = header_cells_for_page(pws)
    hits = total = 0
    for staff in pws.staves:
        cell = cells.get(staff.staff_index)
        if cell is None:
            continue
        verdict = _clef_at_head(cell)
        if verdict is None:
            continue
        total += 1
        hits += bool(verdict)
    return hits, total


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--scores", type=int, default=20, help="how many PDFs to sample")
    ap.add_argument("--pages", type=int, default=3, help="pages per PDF, from page 1")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--seed", type=int, default=20260828,
                    help="the sample is a fixed shuffle, so runs are comparable")
    args = ap.parse_args()

    pdfs = sorted(CORPUS.glob("*/pdfs/*/score.pdf"))
    if not pdfs:
        print(f"no corpus on this machine ({CORPUS}) — nothing to probe", file=sys.stderr)
        return 1
    random.Random(args.seed).shuffle(pdfs)

    hits = total = 0
    for pdf in pdfs[: args.scores]:
        work = pdf.parent.parent.parent.name
        for page_index in range(1, 1 + args.pages):
            try:
                page_hits, page_total = _score_page(pdf, page_index, args.dpi)
            except Exception as exc:                      # a short or broken scan
                print(f"  {work[:26]:<26} p{page_index}: skipped ({type(exc).__name__})")
                continue
            if not page_total:
                continue
            hits += page_hits
            total += page_total
            print(f"  {work[:26]:<26} p{page_index}: clef at head of window "
                  f"{page_hits}/{page_total}")

    if not total:
        print("\nno staves measured", file=sys.stderr)
        return 1
    print(f"\nTOTAL: {hits}/{total} staves ({100.0 * hits / total:.0f}%) have a clef at "
          f"the head of their measured header window")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
