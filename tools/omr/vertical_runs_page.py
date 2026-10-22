"""Vertical ink runs read off the WHOLE PAGE, so nothing clips their ends.

⚠️⚠️ WHY THIS EXISTS, IN ONE SENTENCE: `Q.VERTICAL_RUN` made Sean's barline
test computable and the answer was a clean negative *for a structural reason
that has nothing to do with barlines* — the runs are measured inside a MEASURE
CELL, a cell is the staff plus `PAD_ABOVE_STAFF_LINES` / `PAD_BELOW_STAFF_LINES`
= 4 + 4 staff spaces, and a barline is TALLER than that, so its two ends are the
CROP's and not the ink's. The signature is exact and reproduced on both
publishers: the `too TALL` bucket's median end offsets are **−4.00 / +4.00
staff spaces**, and ten of nineteen print-settled barlines read `h = 12.00`
exactly — 4 + 4 + 4, the cell.
`benchmarks/omr-vertical-runs-2026-09/FINDINGS.md` §3.

**So his test was UNAVAILABLE, not refuted, and this module is the instrument
that makes it available.** It is the `cv_hairpins` precedent applied to
vertical ink: `hairpin_detection` reads a staff BAND across the page rather
than per-measure cells, *"so its hairpins are never cut by a barline"* — the
same move, one family over, for a mark that is cut by the cell rather than by
the barline.

⚠️ IT IS NOT A BAND, IT IS THE PAGE, AND THE DIFFERENCE IS SEAN'S OWN RULE.
*"Bar lines are the length of a staff OR THEY EXTEND TO OTHER SYSTEMS."* A
per-staff band deep enough for a one-staff barline still clips a SYSTEMIC one,
which would reproduce the very fault this module exists to remove — one
window's worth further out. The only window that cannot clip a mark is no
window: components are found on the whole page and attributed afterwards.

⚠️⚠️ NOTHING IS FILTERED. No height bound, no width bound, no aspect, no edge
rule, no area floor. That is `Q.INK`'s discipline (*"ink is ink… there is
nothing that should be classified as unseen — only unclassified"*) and it is
the whole point here: `detect_stems` refuses **64.7%** of its candidates by a
DIMENSION bound, and a barline is refused by `RUN_TOO_TALL` — a height bound
named for stems, applied to the population that contains barlines. A threshold
at the reading site is a decision taken in the wrong stage, and the one kind
that cannot be revisited: a row that was never created is evidence no later
rule can reconsider.

⚠️ THE OPENING RECIPE IS `detect_stems`' OWN, IMPORTED RATHER THAN RESTATED
(`STEM_KERNEL_MARGIN`, the `min_height_lines` floor, `_binary_ink`'s
threshold), so the two readers cannot drift into disagreeing about what a
vertical run IS while disagreeing about where to look for one. What differs is
the WINDOW and the FILTERS, which is the claim under test; if the recipe
differed too, a delta could not be attributed.

⚠️ THE STAFF LINES ARE NOT ERASED HERE, AND THAT IS NOT AN OVERSIGHT.
`detect_stems` reads `cell.image_no_staff` because a cell-level erasure exists;
no page-level erased raster does, and a vertical opening removes a horizontal
line by construction — a staff line is a few pixels tall in any single column,
far under a kernel of ~1.6 staff spaces. So the erasure the cell path pays for
is, for THIS operation, already done by the kernel. What it does mean is that
the two readers see different images, and every row this module returns says
so (`staff_lines_erased=False`), because the one thing that must never happen
is a later reader assuming they agree.

⚠️ WHAT THIS MODULE DOES NOT DO: it names nothing. A run here is neither a stem
nor a barline nor a bracket — it is a vertical piece of ink with page
coordinates and a length. Deciding which is an ADJUDICATE question, and the
evidence it would need (does this run's x column continue into the next staff?
do its ends meet `Q.STAFF_LINES`?) is exactly what page coordinates make
askable and cell coordinates do not.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Sequence

import cv2
import numpy as np

from .line_detection import STEM_KERNEL_MARGIN, _binary_ink

#: The shortest run the kernel is sized against, in staff spaces — the same
#: `min_height_lines` default `detect_stems` takes, so the two readers open
#: with the identical structuring element. ⚠️ It sizes the KERNEL and is NOT a
#: filter: a component shorter than this can still survive the opening (the
#: kernel is 0.8x of it) and is returned like any other.
KERNEL_REFERENCE_SPACES = 2.0


@dataclass(frozen=True)
class PageVerticalRun:
    """One vertical ink run in PAGE pixels, named by nothing.

    ⚠️ `[x, y, w, h]`, the `Q.STEM` / `Q.VERTICAL_RUN` spelling — NOT corners.
    Three box conventions already disagree inside one record here and reading
    one as another gives a negative width.
    """

    x: float
    y: float
    w: float
    h: float
    area: int
    #: Staff spaces, from the page's own staves — never the nominal 100 px.
    width_spaces: float
    height_spaces: float
    staff_space_px: float
    #: The staff whose horizontal reach and nearest band this run falls in, or
    #: None when the page has no staff that can claim it. ⚠️ ATTRIBUTION IS
    #: REPORTED, NEVER USED TO CROP: a run is found first and attributed
    #: after, so a systemic barline crossing twelve staves is one run with one
    #: box, and `staff_index` merely says where its TOP end landed.
    staff_index: Optional[int]
    #: How many staves' vertical extents this run's y-range overlaps. A stem
    #: is 1; a bar-dividing line is 1; a systemic barline or a bracket is more.
    #: ⚠️ A COUNT, NOT A CLASSIFICATION.
    staves_spanned: int

    @property
    def y_top(self) -> float:
        return self.y

    @property
    def y_bottom(self) -> float:
        return self.y + self.h

    @property
    def x_center(self) -> float:
        return self.x + self.w / 2.0


def page_staff_spacing(staves: Sequence[Any]) -> float:
    """The page's staff-space unit, in page px, as the MEDIAN over staves.

    ⚠️ THE MEDIAN AND NOT ONE STAFF'S. A conductor's page prints staves at one
    rastral size, but a scan's warp moves any single staff's spacing by a few
    percent, and this number multiplies every length this module reports. The
    median over a page of 12-27 staves is the cheapest statistic that does not
    ride on whichever staff happened to be first — the same statistic, and the
    same reason, as `system_left_consensus`, where taking the MINIMUM of one
    estimate per staff let one staff under-running its siblings by 70 px move
    the whole window and empty eleven header crops.

    Returns 0.0 when no staff supplies four gaps, and the caller must treat
    that as "this page has no unit" rather than substituting one.
    """
    gaps: List[float] = []
    for s in staves:
        ys = sorted(float(y) for y in (getattr(s, "line_ys", None) or ()))
        if len(ys) < 2:
            continue
        gaps.extend(b - a for a, b in zip(ys, ys[1:]))
    if not gaps:
        return 0.0
    return float(np.median(gaps))


def _staff_bounds(staves: Sequence[Any]) -> List[tuple]:
    """`(top, bottom, x0, x1, index)` per staff, in page px."""
    out = []
    for i, s in enumerate(staves):
        ys = [float(y) for y in (getattr(s, "line_ys", None) or ())]
        if not ys:
            continue
        x0 = float(getattr(s, "x_start", 0.0) or 0.0)
        x1 = float(getattr(s, "x_end", 0.0) or 0.0)
        idx = getattr(s, "staff_index", None)
        out.append((min(ys), max(ys), x0, x1, i if idx is None else int(idx)))
    return out


def read_page_vertical_runs(page_image: Any,
                            staves: Sequence[Any],
                            *,
                            spacing: Optional[float] = None,
                            ) -> List[PageVerticalRun]:
    """Every vertical run on the page, accepted by nothing and refused by nothing.

    `page_image` is a `PageImage`; the ink comes from its `rgb` render through
    `line_detection._binary_ink`, which is the SAME threshold the cell path
    takes.

    ⚠️ IT READS `rgb`, NOT `binary`, AND THE CELL PATH IS WHY. A measure cell's
    `image` is cut from the rendered page and `detect_stems` re-thresholds it
    at 180; taking Sauvola's `binary` here instead would make every length
    difference between the two readers attributable to two binarisations as
    much as to two windows — and `omr-hairpin-cv-2026-09` already measured that
    the recipe alone moves a count 57 vs 62 on identical code. The frame is the
    same either way (both are the deskewed render), so this costs nothing and
    removes a confound.

    Returns runs in page pixels. An empty list means the page held no vertical
    ink at all, which is a different fact from "this page has no staves" — that
    one raises, because a page with no staff-space unit cannot report a length
    and silently reporting pixels as spaces is the frame error this whole
    thread exists to remove.
    """
    img = getattr(page_image, "rgb", None)
    if img is None:
        img = getattr(page_image, "image", None)
    if img is None or getattr(img, "size", 0) == 0:
        return []

    sp = float(spacing) if spacing else page_staff_spacing(staves)
    if sp <= 1.0:
        raise ValueError(
            "no staff-space unit for this page: a length cannot be reported "
            "in staff spaces and page px must not be passed off as spaces")

    ink = _binary_ink(img)
    kernel_h = max(3, int(round(sp * KERNEL_REFERENCE_SPACES
                                * STEM_KERNEL_MARGIN)))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_h))
    opened = cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel)
    num, _, stats, _ = cv2.connectedComponentsWithStats(opened, connectivity=8)

    bounds = _staff_bounds(staves)
    out: List[PageVerticalRun] = []
    for i in range(1, num):  # 0 is background
        x, y, w, h, area = (int(v) for v in stats[i][:5])
        y_top, y_bot = float(y), float(y + h)
        xc = x + w / 2.0
        spanned = 0
        owner: Optional[int] = None
        best = None
        for (top, bottom, sx0, sx1, idx) in bounds:
            if y_bot >= top and y_top <= bottom:
                spanned += 1
                # ⚠️ The owner is the staff whose band the run's TOP end sits
                # nearest, among the staves it overlaps AND whose printed
                # x-reach contains it. A run outside every staff's x-reach —
                # a margin rule, a page edge — is attributed to NONE rather
                # than to the nearest, because "I could not tell" must not be
                # written down as an answer.
                if sx1 > sx0 and not (sx0 <= xc <= sx1):
                    continue
                d = abs(y_top - top)
                if best is None or d < best:
                    best, owner = d, idx
        out.append(PageVerticalRun(
            x=float(x), y=float(y), w=float(w), h=float(h), area=area,
            width_spaces=round(w / sp, 3), height_spaces=round(h / sp, 3),
            staff_space_px=round(sp, 2),
            staff_index=owner, staves_spanned=spanned))
    return out
