"""The ONE place every script in this directory gets its fresh page image
from (lane-2.48-recipe, 2026-10-01, CLAUDE.md rule 7: "a control must be
able to fail").

Sean's suspicion: several scripts here (`recheck_2_48_seeded.py`,
`boundary_measure.py`, `headfit.py`, the `crop_*.py` family) render the
page FRESH and lay the record's stored geometry over it, and two
instruments built on that fresh render failed their clean-head controls
(ink-centre scatter 3.16px; two-candidate head fit 6/15) -- possible cause:
the fresh render does not sit in the same pixel frame the record's GATHER
used.

**Measured, not assumed** (FINDINGS 2026-10-01, lane-2.48-recipe):
production's own recipe for the pixel frame every GATHER coordinate is
filed against is exactly

    detect_staves(render_page(pdf_path, page_index, dpi=dpi))

(`tools/omr/staged/pipeline.py:prepare_pages`) -- ONE call to `render_page`,
which already binarizes and deskews internally
(`preprocessing.render_page`'s own docstring: "already binarized and
deskewed"). Every script in this directory that built a fresh frame called
`deskew()` a SECOND time on `render_page`'s own already-deskewed output --
a real divergence from the production recipe, even though on Litolff p3 at
600dpi it measures as a byte-exact no-op (the first call finds 0.2499deg
and rotates; the second, run on the now-rotated image, finds 0.0deg and
returns the SAME arrays, unchanged -- confirmed by a direct array diff,
mean/max abs diff 0). Calling `detect_staves` on the SINGLE-call frame
reproduces the record's own stored `staff_lines` to the integer pixel for
every staff checked (e.g. staff/3/0/8 = [1643, 1659, 1674, 1690, 1705],
matching both `library/_shared-records/beethoven5-litolff-mvt1-whole-
20261001.record.json` and the a3ef66 lane's `beethoven5-litolff-p3.
record.json` exactly) -- so on THIS page/DPI/PDF there is no frame-
reproduction gap at all, and the clean-head control failures measured
upstream (boundary_measure.py §C, headfit.py's control (a)) are NOT
explained by a recipe divergence; see that FINDINGS entry for the real
cause (the detector's own box, not the frame, on a MERGING plate).

It is still wrong to call `deskew()` twice -- a no-op today is not a no-op
on every page/DPI/PDF this directory's scripts might ever be pointed at,
and "a control must be able to fail" cuts both ways: if the frame ever DOES
drift, every script that re-deskews should see the SAME drift, from the
SAME place, not independently reinvent (and independently mis-invent) the
recipe. Every script here now calls `render_page_matching_gather` instead
of its own `render_page`+`deskew` pair.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.omr.preprocessing import render_page as _render_page  # noqa: E402


def render_page_matching_gather(pdf_path, page_index: int, dpi: int = 600):
    """The page image, in EXACTLY the pixel frame GATHER's own
    `prepare_pages` hands `detect_staves` -- one `render_page` call, no
    second `deskew`. Returns `preprocessing.PageImage` (already binarized
    + deskewed internally); callers must not mutate `.rgb`/`.binary` in
    place and must not call `deskew()` on the result again."""
    return _render_page(pdf_path, page_index, dpi=dpi)
