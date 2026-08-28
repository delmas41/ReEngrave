"""Find the region of a staff that holds its clef, key signature and time
signature — measured from the page, not inherited from measure segmentation.

Every header reader in this pipeline (the clef specialist, the CV C-clef
locator, the time-signature reader, and the key-signature reader) starts from
the same assumption: that the staff-START measure cell contains the header.
On real 19th-century prints that assumption fails, and when it fails it fails
silently — the reader runs, sees no clef and no accidentals, and the staff
falls back to a default that is simply wrong.

## Why the staff-start cell isn't reliable

`Staff.x_start` is the start of the **longest contiguous ink run** along the
middle staff line (`staff_detector._staff_x_extent`). On a clean print that is
the left end of the staff. On a degraded one the line is broken — faded ink,
scanner threshold, the clef and key-signature glyphs sitting on top of it — and
the longest *unbroken* stretch is then the music AFTER the header, so `x_start`
lands to the right of the very glyphs a header reader is looking for.

Measured on Beethoven 5 p.2 (IMSLP 575951, 300 dpi), one system whose eleven
staves all begin at page x≈285:

    x_start:  547, 436, 383, 777, 1007, 985, 1233, 1001, 927, 1048, 986

A 56-staff-space spread on a system that is physically flush. `_measure_x_
boundaries` takes the minimum across the system, so the staff-start cell began
at x=383 — past the treble clef (x≈310–355) and past all three key-signature
flats (x≈360–395). The cell contained a whole rest and a barline. A key
signature of three flats read as no key signature at all, on every staff.

## What this module measures instead

The individual staff lines are broken, but the staff *band* is not: at almost
every column between the staff's left end and its right end, SOME row in the
band carries ink — a line fragment, or the glyph sitting on it. So the left
edge is found by walking left along the band's ink profile from a column known
to be inside the staff, bridging gaps shorter than `gap_tolerance_spaces`, and
stopping where the ink genuinely stops. The same staff as above, band profile
from page x=250 (`#` = ink in some row of the band):

    ....#######..####################################################…
        ^bracket ^staff starts here (x≈263) — continuous from here right

The right edge is the system's first barline, or a width cap when no barline is
found. Erring left is safe and erring right is not: extra ink at the left of
the window is bracket and instrument-name text that every reader already has to
skip, while a window that starts too late loses the clef outright. So the left
edge carries a deliberate `left_margin_spaces` bias.

Taking the minimum is only safe while the walk cannot under-report, and it once
could: `_staff_x_extent` bridges broken lines, which lets `Staff.x_start` land
in the instrument name, and a walk starting there never meets the bracket meant
to stop it. `_anchor_column` now enforces what it used to assume. The failure
that rule prevents is not small — the under-reported edge also stops the window
being cut at the system's own initial rule, so it ends where the header begins.

## What this module does NOT do

It does not touch `Staff.x_start` or measure segmentation. Phase 1 has no
regression baseline, so changing a value that every later stage consumes is a
much bigger bet than adding a measurement beside it (the same reasoning that
parked the text-as-staff fix). Header readers opt in by asking for a header
cell; everything else sees the pipeline it saw before.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .measure_extractor import _build_measure_cell
from .staff_line_removal import remove_staff_lines_from_cell
from .types import MeasureCell, PageWithStaves, Staff


# A header cell is not a measure. It overlaps measure 0 and would corrupt any
# per-measure bookkeeping that keyed on it, so it carries a measure_index that
# cannot collide with a real one.
HEADER_MEASURE_INDEX = -1


@dataclass(frozen=True)
class HeaderWindowConfig:
    """Knobs for header-window measurement. Every length is in staff spaces
    (the distance between adjacent staff lines) so the thresholds hold at any
    DPI or engraving size.

    gap_tolerance_spaces:
        How long a break in the staff band's ink the leftward walk will bridge.
        Small — a quarter space is a few pixels at any sane DPI. It is meant to
        cross scanner dropout inside the staff, NOT to reach the instrument
        name printed to the left (which sits a good two spaces clear, and would
        drag the window into text if bridged).
    left_margin_spaces:
        Extra room added at the left once the edge is found. Erring left costs
        a reader nothing; erring right costs it the clef.
    min_width_spaces / max_width_spaces:
        A barline closer than the minimum is the system's own initial rule, not
        the end of the header, so it is skipped. The maximum caps the window
        when a system has no barline near the header at all.
    """

    gap_tolerance_spaces: float = 0.25
    left_margin_spaces: float = 0.5
    min_width_spaces: float = 3.0
    max_width_spaces: float = 16.0


DEFAULT_CONFIG = HeaderWindowConfig()


@dataclass(frozen=True)
class HeaderWindow:
    """The measured header region of one staff, in PAGE pixels.

    x0/x1:      left/right edge of the window.
    right_from: "barline" when the right edge is the system's first barline,
                "width_cap" when no usable barline was found and the window was
                capped instead — a hint that the window may hold music as well
                as header, which readers that care can weigh.
    """

    staff_index: int
    system_index: int
    x0: int
    x1: int
    right_from: str

    @property
    def width(self) -> int:
        return self.x1 - self.x0


def _band_ink_profile(binary: np.ndarray, staff: Staff) -> np.ndarray:
    """Columns where ANY row of the staff band carries ink.

    The band is the staff proper plus a couple of pixels of slack, not the
    padded cell: ink from the staff above or below must not leak in, or the
    leftward walk would follow a neighbour's line past this staff's edge.
    """
    h = binary.shape[0]
    y0 = max(0, staff.top_y - 2)
    y1 = min(h, staff.bottom_y + 3)
    if y1 <= y0:
        return np.zeros(binary.shape[1], dtype=bool)
    return binary[y0:y1].min(axis=0) == 0


def _rule_columns(binary: np.ndarray, staff: Staff, min_coverage: float = 0.9) -> np.ndarray:
    """Columns where ink covers nearly the whole staff band — the system's
    bracket and its initial vertical rule.

    These are the left wall of the staff. Without them the leftward walk keeps
    going into the instrument name printed beside the system ("Fl.", "Cor."),
    which sits close enough that a tolerance generous enough to cross print
    dropout will also cross the gap to the text. A vertical rule is
    unmistakable and always sits exactly at the boundary we want, so it is a
    better stopping rule than any tolerance could be.
    """
    h = binary.shape[0]
    y0 = max(0, staff.top_y - 2)
    y1 = min(h, staff.bottom_y + 3)
    if y1 <= y0:
        return np.zeros(binary.shape[1], dtype=bool)
    band = binary[y0:y1] == 0
    return band.mean(axis=0) >= min_coverage


def _walk_left(ink: np.ndarray, anchor: int, gap_px: int, wall: np.ndarray) -> int:
    """Walk left from `anchor` along `ink`, bridging runs of blank shorter than
    or equal to `gap_px`, and return the leftmost column still connected.

    Stops on a `wall` column (a full-height vertical rule): the staff begins
    there, and anything further left belongs to the score's furniture rather
    than to this staff.
    """
    x = anchor
    while x > 0:
        if wall[x - 1]:
            return x - 1
        if ink[x - 1]:
            x -= 1
            continue
        # A blank column — look back over the tolerance to see whether the ink
        # resumes. If it does, the gap is print dropout; step across it.
        lo = max(0, x - 1 - gap_px)
        window = ink[lo : x - 1]
        if window.size and window.any():
            hit = lo + int(np.flatnonzero(window)[-1]) + 1
            # Don't bridge a gap that has a wall on its far side — that ink is
            # the rule itself, not a continuation of this staff's lines.
            if wall[lo : x - 1].any():
                return x
            x = hit
            continue
        break
    return x


def _anchor_column(ink: np.ndarray, staff: Staff, wall: np.ndarray | None = None) -> int | None:
    """A column that is certainly inside the staff, to walk left from.

    `staff.x_start` is the natural candidate, and this module was written when
    it could only ever be too far RIGHT — the longest strictly-contiguous run
    can start late but never early, and starting late is the direction that
    keeps the walk inside the staff.

    That guarantee is gone. `_staff_x_extent` now bridges breaks of up to a
    staff space (`STAFF_LINE_MAX_GAP_SPACES`), which is what put the clef back
    inside the measure cell — but the same bridging also reaches LEFT across
    the gap between the system's bracket and the instrument name printed beside
    it, and `x_start` then lands in the TEXT. Measured on Beethoven 6 p.2,
    whose bracket stands at x≈435: two of the ten staves of system 0 report
    `x_start` 328 and 334. A walk starting there is already outside the staff,
    so it never meets the bracket, runs on through the instrument name and
    returns a left edge a hundred pixels too far out.

    `system_left_edge` takes the MINIMUM across the system, so one such staff
    sets the window for all of them — and the damage is not just a wide window.
    The right edge is the first barline at least `min_width_spaces` from the
    left one, so an edge that starts too far out stops SKIPPING the system's
    own initial rule and cuts the window there instead. On Beethoven 5 p.2
    system 1 that produced a 6.4-space window running from before the bracket
    to the rule the clefs stand behind: instrument names, and no clef at all.

    So the guarantee is now enforced rather than assumed, using the fact
    `_walk_left` already stops on: a full-band vertical rule is the staff's
    left boundary. An anchor left of the leftmost such rule is outside the
    staff, and is moved to the first ink beyond that rule — beyond rather than
    onto it, so the walk stops ON the rule rather than stepping across it.
    """
    n = ink.size
    x = int(np.clip(staff.x_start, 0, n - 1))
    if wall is not None and wall.any():
        first_wall = int(np.flatnonzero(wall)[0])
        if x < first_wall:
            end = first_wall
            while end + 1 < n and wall[end + 1]:
                end += 1
            x = min(n - 1, end + 1)
    if ink[x]:
        return x
    rest = np.flatnonzero(ink[x:])
    if rest.size:
        return x + int(rest[0])
    return None


def _staff_left_candidate(
    pws: PageWithStaves, staff: Staff, config: HeaderWindowConfig
) -> int | None:
    """This staff's own estimate of where the system's staves begin."""
    spacing = max(1.0, staff.line_spacing_px)
    ink = _band_ink_profile(pws.page.binary, staff)
    if not ink.any():
        return None
    wall = _rule_columns(pws.page.binary, staff)
    anchor = _anchor_column(ink, staff, wall)
    if anchor is None:
        return None
    return _walk_left(
        ink, anchor,
        gap_px=max(1, int(round(config.gap_tolerance_spaces * spacing))),
        wall=wall,
    )


def system_left_edge(
    pws: PageWithStaves,
    system_index: int,
    config: HeaderWindowConfig = DEFAULT_CONFIG,
) -> int | None:
    """Where the staves of one system begin, in page pixels.

    Taken as the MINIMUM of the per-staff estimates, because the estimate can
    only ever be too far right and never too far left. A staff whose anchor
    (`Staff.x_start`) landed deep inside the music walks left only as far as
    the first barline it meets — that barline is a full-height rule, so the
    walk stops there and the staff reports a much too large value. A staff
    whose anchor is sound walks back to the system's initial rule and reports
    the truth. The minimum picks the sound one, and the wall rule is what makes
    the minimum safe: nothing can under-run past the bracket into the
    instrument names, so there is no runaway value for the minimum to prefer.

    On Beethoven 5 p.2 system 0 the eleven per-staff estimates are

        535, 279, 282, 691, 995, 935, 1197, 937, 900, 1000, 901

    — nine of them stopped at a barline, two walked back to the real edge, and
    the minimum (279) is right to within a couple of pixels.
    """
    staves = [s for s in pws.staves if s.system_index == system_index]
    cands = [c for c in (_staff_left_candidate(pws, s, config) for s in staves) if c is not None]
    return min(cands) if cands else None


def measure_header_window(
    pws: PageWithStaves,
    staff: Staff,
    config: HeaderWindowConfig = DEFAULT_CONFIG,
    *,
    left_edge: int | None = None,
) -> HeaderWindow | None:
    """Measure the header window of one staff. Returns None when the staff has
    no usable ink profile — abstaining rather than guessing a window, so a
    caller that gets None knows to fall back rather than read garbage.

    `left_edge` supplies an already-computed system left edge (see
    `header_cells_for_page`, which measures each system once); when it is None
    the system's edge is measured here.
    """
    spacing = max(1.0, staff.line_spacing_px)
    if left_edge is None:
        left_edge = system_left_edge(pws, staff.system_index, config)
    if left_edge is None:
        return None
    x0 = max(0, left_edge - int(round(config.left_margin_spaces * spacing)))

    min_w = int(round(config.min_width_spaces * spacing))
    max_w = int(round(config.max_width_spaces * spacing))
    page_w = pws.page.binary.shape[1]

    # The system's first barline that is far enough right to be a measure
    # boundary rather than the system's own initial rule.
    candidates = [
        bl.x for bl in pws.barlines
        if bl.system_index == staff.system_index and bl.x >= x0 + min_w
    ]
    if candidates and min(candidates) <= x0 + max_w:
        x1, right_from = min(candidates), "barline"
    else:
        x1, right_from = x0 + max_w, "width_cap"
    x1 = min(int(x1), page_w, staff.x_end if staff.x_end > x0 + min_w else page_w)

    if x1 - x0 < min_w:
        return None
    return HeaderWindow(
        staff_index=staff.staff_index,
        system_index=staff.system_index,
        x0=int(x0),
        x1=int(x1),
        right_from=right_from,
    )


def extract_header_cell(
    pws: PageWithStaves,
    staff: Staff,
    config: HeaderWindowConfig = DEFAULT_CONFIG,
    *,
    left_edge: int | None = None,
) -> MeasureCell | None:
    """Crop one staff's header as a canonical MeasureCell, ready for any reader
    that already consumes cells (the YOLO detector, `clef_locator`,
    `key_signature_locator`).

    The cell is built by the same code path as a real measure cell, so its
    canonical scaling, staff-line coordinates and staff-line-removed variant
    are identical in kind — only the x-range differs. It carries
    `HEADER_MEASURE_INDEX` so it can never be mistaken for measure 0.

    Returns None when the window can't be measured or the crop is degenerate.
    """
    window = measure_header_window(pws, staff, config, left_edge=left_edge)
    if window is None:
        return None
    cell = _build_measure_cell(
        pws, staff, staff.system_index, window.x0, window.x1, HEADER_MEASURE_INDEX,
    )
    if cell is None:
        return None
    remove_staff_lines_from_cell(cell)
    return cell


def header_windows_for_page(
    pws: PageWithStaves,
    config: HeaderWindowConfig = DEFAULT_CONFIG,
) -> dict[int, HeaderWindow]:
    """Header windows for every staff on a page, keyed by `staff_index`.

    Measures each system's left edge ONCE and shares it across that system's
    staves — both cheaper and more accurate than each staff deciding alone (see
    `system_left_edge`, where the minimum over a system is what rescues a staff
    whose own lines are broken). Staves whose window can't be measured are
    simply absent.
    """
    out: dict[int, HeaderWindow] = {}
    for system_index in sorted({s.system_index for s in pws.staves}):
        left = system_left_edge(pws, system_index, config)
        if left is None:
            continue
        for staff in pws.staves:
            if staff.system_index != system_index:
                continue
            window = measure_header_window(pws, staff, config, left_edge=left)
            if window is not None:
                out[staff.staff_index] = window
    return out


def header_cells_for_page(
    pws: PageWithStaves,
    config: HeaderWindowConfig = DEFAULT_CONFIG,
    windows: dict[int, HeaderWindow] | None = None,
) -> dict[int, MeasureCell]:
    """Header cells for every staff on a page, keyed by `staff_index`.

    The entry point header readers should use. Pass `windows` from
    `header_windows_for_page` when the caller already has them, so the page is
    measured once rather than once per consumer.
    """
    if windows is None:
        windows = header_windows_for_page(pws, config)
    out: dict[int, MeasureCell] = {}
    for staff in pws.staves:
        window = windows.get(staff.staff_index)
        if window is None:
            continue
        cell = _build_measure_cell(
            pws, staff, staff.system_index, window.x0, window.x1, HEADER_MEASURE_INDEX,
        )
        if cell is None:
            continue
        remove_staff_lines_from_cell(cell)
        out[staff.staff_index] = cell
    return out
