"""Unit tests for the Phase 1i local re-segmentation pass
(`measure_extractor.resegment_fused_measures` and its helper
`_find_internal_barline_candidates`).

These are synthetic — no PDFs needed — so they run in every default
`pytest tools/omr/tests` invocation (no `omr_smoke`/PDF-on-disk skip).

Fixture layout: one page, one system with TWO staves (re-segmentation is
multi-staff-only — a candidate barline must be corroborated across staves
and drawn through the inter-staff gap, so a single-staff fixture can never
split):

    staff 0: y in [100, 180]   (5 lines, spacing 20)
    staff 1: y in [240, 320]   (5 lines, spacing 20)
    inter-staff gap: y in (180, 240)

A "real" barline is drawn as one vertical ink stripe spanning y in
[95, 325] — through BOTH staves and the gap between them, so both staves
vote for it and `_intersystem_connectivity` sees continuous gap ink.

Three "measures" are laid out along x (identical boundaries on both
staves, since barline x-positions are shared across a system):

    measure 0: x in [50, 250)    width 200  (normal)
    measure 1: x in [250, 662)   width 412  (>2x median -- the flagged cell)
    measure 2: x in [662, 862)   width 200  (normal)

Median width is 200, and 412 > 2 * 200 (transcribe.py's `phase1_warning`
check is a strict `>`), so measure 1 is exactly the kind of outlier that
check flags.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tools.omr.measure_extractor import (
    BARLINE_MIN_DISTANCE_PX,
    _find_internal_barline_candidates,
    _select_steered_splits,
    majority_bars_by_system,
    resegment_fused_measures,
)
from tools.omr.types import MeasureCell, PageImage, PageWithStaves, Staff
# Content is what separates furniture from a measure, and content only exists
# after detection — so the pass lives in `transcribe`, not here. Tested beside
# the measure work because that is what it is about.
from tools.omr.transcribe import _drop_furniture_measures


PAGE_W = 1000
PAGE_H = 400
STAFF0_YS = [100, 120, 140, 160, 180]  # span 80
STAFF1_YS = [240, 260, 280, 300, 320]  # span 80, gap (180, 240) above it
TEST_MAX_CELL_WIDTH = 256  # keep synthetic arrays small/fast


def _make_page(binary: np.ndarray | None = None) -> PageImage:
    rgb = np.full((PAGE_H, PAGE_W, 3), 255, dtype=np.uint8)
    if binary is None:
        binary = np.full((PAGE_H, PAGE_W), 255, dtype=np.uint8)  # all paper
    return PageImage(
        pdf_path=Path("synthetic.pdf"),
        page_index=0,
        dpi=300,
        rgb=rgb,
        binary=binary,
    )


def _make_staves() -> list[Staff]:
    return [
        Staff(page_index=0, staff_index=0, line_ys=list(STAFF0_YS),
              x_start=50, x_end=850, system_index=0),
        Staff(page_index=0, staff_index=1, line_ys=list(STAFF1_YS),
              x_start=50, x_end=850, system_index=0),
    ]


def _draw_barline(binary: np.ndarray, x: int, width: int = 3) -> None:
    """Draw one vertical ink stripe at column x spanning BOTH staves and
    the gap between them (y 95..325). 0 = ink (matches the project's
    binarization convention, see types.py PageImage.binary). Such a stripe
    is voted for by both staves and shows full inter-staff connectivity --
    i.e. it looks exactly like a genuine system barline."""
    half = width // 2
    binary[95:326, x - half:x + width - half] = 0


def _measure_cells(staves: list[Staff], boundaries: list[tuple[int, int]]) -> list[MeasureCell]:
    """Build lightweight MeasureCell stand-ins (one per staff x measure)
    for the pre-resegmentation state. Only bbox_page_px / system_index /
    staff_index / measure_index matter to resegment_fused_measures's
    bookkeeping -- the image fields are dummy since they're never read for
    cells that don't get split."""
    cells = []
    for staff in staves:
        y0, y1 = staff.top_y - 5, staff.bottom_y + 5
        for m_idx, (x0, x1) in enumerate(boundaries):
            cells.append(MeasureCell(
                page_index=0,
                system_index=staff.system_index,
                staff_index=staff.staff_index,
                measure_index=m_idx,
                image=np.zeros((10, 10, 3), dtype=np.uint8),
                image_no_staff=None,
                bbox_page_px=(x0, y0, x1, y1),
                staff_line_ys_canonical=[0, 20, 40, 60, 80],
                upscale_factor=1.0,
            ))
    return cells


BOUNDARIES = [(50, 250), (250, 662), (662, 862)]  # widths: 200, 412, 200


def _staff_measure_widths(cells, staff_index):
    return sorted(
        c.bbox_page_px[2] - c.bbox_page_px[0]
        for c in cells if c.staff_index == staff_index
    )


class TestClearInternalBarlineSplits:
    """A >2x-median cell with one genuine, well-formed internal barline at
    its center (spanning both staves + the gap) should split cleanly into
    2 plausible-width measures on every staff of the system."""

    def test_candidate_found_at_center(self):
        binary = np.full((PAGE_H, PAGE_W), 255, dtype=np.uint8)
        _draw_barline(binary, 456)  # center of the flagged [250, 662) cell
        staves = _make_staves()
        candidates = _find_internal_barline_candidates(binary, staves, 250, 662)
        assert candidates == [456]

    def test_resegment_splits_into_two_measures(self):
        page = _make_page()
        _draw_barline(page.binary, 456)
        staves = _make_staves()
        pws = PageWithStaves(page=page, staves=staves, barlines=[])
        cells = _measure_cells(staves, BOUNDARIES)

        out = resegment_fused_measures(pws, cells, max_cell_width=TEST_MAX_CELL_WIDTH)

        # 3 cells/staff x 2 staves = 6 in -> 4 cells/staff x 2 = 8 out.
        assert len(out) == 8, "the fused cell split in two on BOTH staves"
        for staff_index in (0, 1):
            widths = _staff_measure_widths(out, staff_index)
            assert widths == [200, 200, 206, 206], (
                f"staff {staff_index}: split pieces should each be ~median "
                "width, not the original fused 412px cell"
            )
            idxs = sorted(c.measure_index for c in out if c.staff_index == staff_index)
            assert idxs == [0, 1, 2, 3], "measure_index renumbered 0..3 per staff"
        # New split cells carry a real rendered image, not the placeholder.
        for c in out:
            assert c.image.shape[0] > 0 and c.image.shape[1] > 0
            assert c.width <= TEST_MAX_CELL_WIDTH


class TestNoInternalBarlineStaysFused:
    """A >2x-median cell with NO genuine internal barline ink must be left
    exactly as Phase 1 produced it -- no spurious split."""

    def test_no_candidates_found(self):
        binary = np.full((PAGE_H, PAGE_W), 255, dtype=np.uint8)  # blank
        staves = _make_staves()
        candidates = _find_internal_barline_candidates(binary, staves, 250, 662)
        assert candidates == []

    def test_resegment_leaves_cell_untouched(self):
        page = _make_page()  # blank binary -- no ink anywhere
        staves = _make_staves()
        pws = PageWithStaves(page=page, staves=staves, barlines=[])
        cells = _measure_cells(staves, BOUNDARIES)

        out = resegment_fused_measures(pws, cells, max_cell_width=TEST_MAX_CELL_WIDTH)

        assert len(out) == 6, "no split should happen -- same cell count as input"
        assert _staff_measure_widths(out, 0) == [200, 200, 412]
        # The untouched fused cell should be the SAME object (identity),
        # not rebuilt -- resegment_fused_measures passes through cells it
        # doesn't split.
        fused_in = next(c for c in cells if c.bbox_page_px[2] - c.bbox_page_px[0] == 412)
        assert fused_in in out


class TestSliverSplitRejected:
    """A candidate barline that IS detected but would produce an
    implausibly narrow (sliver) sub-measure must be rejected outright --
    the whole split is discarded, not just the bad piece."""

    def test_off_center_candidate_produces_sliver_and_is_rejected(self):
        page = _make_page()
        # Cell is [250, 662) (width 412, median 200). A barline at x=330
        # clears the BARLINE_MIN_DISTANCE_PX edge-exclusion zone (330 -
        # 250 = 80 > 60) but yields piece widths [80, 332]: 80 is below
        # the acceptance floor (0.5 * 200 = 100) -- a sliver.
        candidate_x = 250 + BARLINE_MIN_DISTANCE_PX + 20
        assert candidate_x - 250 > BARLINE_MIN_DISTANCE_PX  # sanity: not edge-excluded
        _draw_barline(page.binary, candidate_x)
        staves = _make_staves()
        pws = PageWithStaves(page=page, staves=staves, barlines=[])
        cells = _measure_cells(staves, BOUNDARIES)

        # The candidate should still be *found* (it's a real barline shape,
        # not filtered by the edge-exclusion)...
        candidates = _find_internal_barline_candidates(page.binary, staves, 250, 662)
        assert candidates == [candidate_x]

        # ...but resegment_fused_measures must reject the split because
        # one resulting piece would be a sliver.
        out = resegment_fused_measures(pws, cells, max_cell_width=TEST_MAX_CELL_WIDTH)
        assert len(out) == 6, "sliver split must be rejected -- cell count unchanged"
        assert _staff_measure_widths(out, 0) == [200, 200, 412], (
            "the fused cell must stay whole, not sliced into a sliver"
        )


class TestNormalWidthCellsNeverTouched:
    """Cells that are NOT >2x-median outliers must never be examined for
    internal barlines at all, even if the page happens to contain
    barline-shaped ink inside them (regression guard for the 'only touch
    flagged cells' hard rule)."""

    def test_ink_inside_a_normal_cell_is_ignored(self):
        page = _make_page()
        # Draw a perfectly good barline-shaped stripe inside measure 0
        # ([50, 250), width 200 -- NOT flagged, since median is 200 and
        # 200 is not > 2*200).
        _draw_barline(page.binary, 150)
        staves = _make_staves()
        pws = PageWithStaves(page=page, staves=staves, barlines=[])
        cells = _measure_cells(staves, BOUNDARIES)

        out = resegment_fused_measures(pws, cells, max_cell_width=TEST_MAX_CELL_WIDTH)

        assert len(out) == 6, "normal-width cells must never be split, regardless of content"
        assert _staff_measure_widths(out, 0) == [200, 200, 412]


class TestSingleStaffSystemNeverSplit:
    """Re-segmentation is multi-staff-only: a single-staff 'system' (an
    isolated instrument line, or a staff-detector mis-grouping) has no
    cross-staff corroboration, so even a textbook-clear internal barline
    must NOT trigger a split. Guards the tightened multi-staff requirement."""

    def test_single_staff_candidate_rejected(self):
        binary = np.full((PAGE_H, PAGE_W), 255, dtype=np.uint8)
        _draw_barline(binary, 456)
        one_staff = [_make_staves()[0]]  # just the top staff, alone
        candidates = _find_internal_barline_candidates(binary, one_staff, 250, 662)
        assert candidates == [], "single-staff systems are ineligible for re-segmentation"

    def test_single_staff_cell_stays_fused(self):
        page = _make_page()
        _draw_barline(page.binary, 456)
        one_staff = [_make_staves()[0]]
        pws = PageWithStaves(page=page, staves=one_staff, barlines=[])
        cells = _measure_cells(one_staff, BOUNDARIES)

        out = resegment_fused_measures(pws, cells, max_cell_width=TEST_MAX_CELL_WIDTH)

        assert len(out) == 3, "single-staff cell must never split"
        assert _staff_measure_widths(out, 0) == [200, 200, 412]


# ─── Trailing tail handling (_measure_x_boundaries) ──────────────────────────


class TestTrailingTail:
    """A tail much narrower than a real measure used to be DISCARDED, on the
    assumption it was the blank strip between the final barline and the end of
    the staff lines. That assumption fails whenever a spurious barline is
    detected near the end of a system, and then real music is deleted from the
    page with nothing downstream able to tell (the measure COUNT stays right).

    Measured on WTC p.6 system 2: a false barline at x=4476, where two stems
    happen to align across the staves, ended the last cell there and dropped
    the 340px of notes that followed. The tail is now absorbed into the last
    measure instead.
    """

    @staticmethod
    def _staff(x_start: int, x_end: int):
        from tools.omr.types import Staff
        return Staff(page_index=0, staff_index=0, line_ys=[100, 120, 140, 160, 180],
                     x_start=x_start, x_end=x_end, system_index=0)

    @staticmethod
    def _barlines(xs: list[int]):
        from tools.omr.types import Barline
        return [Barline(page_index=0, x=x, y_top=95, y_bottom=185, system_index=0)
                for x in xs]

    def _boundaries(self, barline_xs, x_start=100, x_end=1100):
        from tools.omr.measure_extractor import _measure_x_boundaries
        return _measure_x_boundaries(self._barlines(barline_xs), [self._staff(x_start, x_end)])

    def test_narrow_tail_is_absorbed_not_dropped(self):
        # Two wide measures then a 60px sliver: the sliver is folded into the
        # measure before it, so the covered span still reaches the staff edge.
        got = self._boundaries([100, 500, 1040, 1100])
        assert got[-1][1] == 1100, f"tail dropped: {got}"
        assert got == [(100, 500), (500, 1100)]

    def test_no_x_is_left_uncovered(self):
        """The invariant that matters: boundaries must tile the staff."""
        for xs in ([100, 500, 1040, 1100], [100, 400, 700, 1100], [100, 600, 1100]):
            got = self._boundaries(xs)
            assert got[0][0] == 100
            assert got[-1][1] == 1100
            for a, b in zip(got, got[1:]):
                assert a[1] == b[0], f"gap between {a} and {b}"

    def test_a_wide_tail_is_still_its_own_measure(self):
        # 600px after the last barline is a measure, not a strip.
        got = self._boundaries([100, 500, 1100])
        assert got == [(100, 500), (500, 1100)]

    def test_single_measure_page_is_unaffected(self):
        got = self._boundaries([100, 1100])
        assert got == [(100, 1100)]
# ─── Steered re-segmentation ────────────────────────────────────────


class TestSelectSteeredSplits:
    """The pure accept/reject decision (no image)."""

    def test_fills_shortfall_in_given_order(self):
        cc = [(1, 250, 610, [430]), (3, 700, 1100, [900])]  # median 200
        assert _select_steered_splits(cc, 1, 200) == {1: [250, 430, 610]}
        assert _select_steered_splits(cc, 2, 200) == {
            1: [250, 430, 610], 3: [700, 900, 1100]}

    def test_zero_or_negative_shortfall_is_noop(self):
        assert _select_steered_splits([(1, 250, 610, [430])], 0, 200) == {}
        assert _select_steered_splits([(1, 250, 610, [430])], -2, 200) == {}

    def test_no_candidates_skipped(self):
        assert _select_steered_splits([(1, 250, 610, [])], 1, 200) == {}

    def test_sliver_rejected(self):
        # barline @280 in [250,610] -> pieces [30, 330]; 30 < 0.5*200 -> sliver
        assert _select_steered_splits([(1, 250, 610, [280])], 1, 200) == {}

    def test_never_overshoots(self):
        # a cell with 2 candidates but only 1 bar short -> skip it entirely
        assert _select_steered_splits([(1, 250, 850, [400, 650])], 1, 200) == {}
        # ...but accepted when the shortfall can absorb both
        assert _select_steered_splits([(1, 250, 850, [400, 650])], 2, 200) == {
            1: [250, 400, 650, 850]}


# Boundaries with a sub-2x fused cell (360px, median 200 -> 1.8x): the
# conservative pass ignores it (< 2x), but a known bar count can steer a split.
_SUB2X_BOUNDARIES = [(50, 250), (250, 610), (610, 810)]  # widths 200, 360, 200


class TestSteeredResegmentation:
    def test_sub_2x_cell_split_only_when_steered(self):
        page = _make_page()
        _draw_barline(page.binary, 430)  # genuine barline mid the 360px cell
        staves = _make_staves()
        pws = PageWithStaves(page=page, staves=staves, barlines=[])

        # No expected count: conservative ignores the 1.8x cell -> stays fused.
        out0 = resegment_fused_measures(
            pws, _measure_cells(staves, _SUB2X_BOUNDARIES),
            max_cell_width=TEST_MAX_CELL_WIDTH)
        assert len(out0) == 6
        assert _staff_measure_widths(out0, 0) == [200, 200, 360]

        # Dossier says 4 bars -> steer the split.
        out = resegment_fused_measures(
            pws, _measure_cells(staves, _SUB2X_BOUNDARIES),
            max_cell_width=TEST_MAX_CELL_WIDTH,
            expected_bars_by_system={0: 4})
        assert len(out) == 8
        assert _staff_measure_widths(out, 0) == [180, 180, 200, 200]

    def test_never_fabricates_a_barline(self):
        # Blank cell (no ink), the expected count demands 4 bars -> steering must NOT split.
        page = _make_page()  # blank
        staves = _make_staves()
        pws = PageWithStaves(page=page, staves=staves, barlines=[])
        out = resegment_fused_measures(
            pws, _measure_cells(staves, _SUB2X_BOUNDARIES),
            max_cell_width=TEST_MAX_CELL_WIDTH,
            expected_bars_by_system={0: 4})
        assert len(out) == 6, "no barline ink -> no split, even when told to find one"

    def test_relaxes_upper_width_guard_under_steering(self):
        # A >2x cell whose split the conservative gate rejects (one piece 1.9x >
        # MAX_PIECE_FRAC 1.75x); steering drops that upper guard.
        boundaries = [(50, 250), (250, 750), (750, 950)]  # widths 200, 500, 200
        page = _make_page()
        _draw_barline(page.binary, 370)  # pieces [120, 380]; 380 = 1.9x median
        staves = _make_staves()
        pws = PageWithStaves(page=page, staves=staves, barlines=[])

        out0 = resegment_fused_measures(
            pws, _measure_cells(staves, boundaries), max_cell_width=TEST_MAX_CELL_WIDTH)
        assert len(out0) == 6, "conservative rejects the too-wide-piece split"

        out = resegment_fused_measures(
            pws, _measure_cells(staves, boundaries),
            max_cell_width=TEST_MAX_CELL_WIDTH, expected_bars_by_system={0: 4})
        assert len(out) == 8, "steering accepts it (sliver floor still applies)"

    def test_inert_when_count_already_met(self):
        # A genuine barline exists, but the expected count is already satisfied ->
        # steering does nothing (respects the known count).
        page = _make_page()
        _draw_barline(page.binary, 430)
        staves = _make_staves()
        pws = PageWithStaves(page=page, staves=staves, barlines=[])
        out = resegment_fused_measures(
            pws, _measure_cells(staves, _SUB2X_BOUNDARIES),
            max_cell_width=TEST_MAX_CELL_WIDTH, expected_bars_by_system={0: 3})
        assert len(out) == 6, "count met -> no steered split"


# ─── The system's own majority bar count (majority_bars_by_system) ────────────


def _cells_for_counts(counts: dict[tuple[int, int], int]) -> list[MeasureCell]:
    """Cells for `{(system_index, staff_index): n_measures}`. Only the index
    fields matter here — majority_bars_by_system counts cells, nothing else."""
    cells = []
    for (sys_idx, staff_idx), n in counts.items():
        for m_idx in range(n):
            cells.append(MeasureCell(
                page_index=0,
                system_index=sys_idx,
                staff_index=staff_idx,
                measure_index=m_idx,
                image=np.zeros((10, 10, 3), dtype=np.uint8),
                image_no_staff=None,
                bbox_page_px=(50 + 100 * m_idx, 0, 150 + 100 * m_idx, 90),
                staff_line_ys_canonical=[0, 20, 40, 60, 80],
                upscale_factor=1.0,
            ))
    return cells


class TestMajorityBarsBySystem:
    """The count a system's staves agree on, computed off the cells alone —
    before any symbol is detected. It steers re-segmentation, so it abstains
    wherever the page gives no unambiguous answer."""

    def test_unanimous_system(self):
        cells = _cells_for_counts({(0, 0): 4, (0, 1): 4, (0, 2): 4})
        assert majority_bars_by_system(cells) == {0: 4}

    def test_one_short_staff_yields_the_majority(self):
        # The case the whole feature exists for: three staves read 4 bars and
        # one reads 3, so the fourth has a fused pair.
        cells = _cells_for_counts({(0, 0): 4, (0, 1): 4, (0, 2): 4, (0, 3): 3})
        assert majority_bars_by_system(cells) == {0: 4}

    def test_tie_abstains(self):
        # 2-2 gives no basis to call either side the anomaly.
        cells = _cells_for_counts({(0, 0): 4, (0, 1): 4, (0, 2): 3, (0, 3): 3})
        assert majority_bars_by_system(cells) == {}

    def test_bare_plurality_abstains(self):
        # Modal count held by 1 of 3 staves is not a strict majority.
        cells = _cells_for_counts({(0, 0): 2, (0, 1): 3, (0, 2): 4})
        assert majority_bars_by_system(cells) == {}

    def test_single_staff_system_abstains(self):
        # Nothing to cross-check against; asserting a count from one staff is
        # circular — it would only ever confirm what that staff already read.
        assert majority_bars_by_system(_cells_for_counts({(0, 0): 5})) == {}

    def test_systems_are_independent(self):
        cells = _cells_for_counts({
            (0, 0): 4, (0, 1): 4,          # system 0 agrees
            (1, 0): 6, (1, 1): 6, (1, 2): 5,  # system 1: majority 6
            (2, 0): 3, (2, 1): 2,          # system 2: tie -> absent
        })
        assert majority_bars_by_system(cells) == {0: 4, 1: 6}

    def test_empty_input(self):
        assert majority_bars_by_system([]) == {}


class TestMajoritySteeringIsSafeOnRestingStaves:
    """The one hazard of steering from the page's own majority rather than an
    external count: it runs BEFORE detection, so it cannot use the note-content
    test that separates a fused pair of real bars from a condensed
    multi-measure rest — the dominant orchestral false positive, and the reason
    `_flag_measure_count_inconsistency` down-weights that case to "low".

    What protects it is that a multi-measure rest carries no internal barline,
    and steering never splits without barline ink. This pins that end to end:
    majority computed from the cells, fed straight to re-segmentation."""

    def test_resting_staff_is_not_split_to_meet_the_majority(self):
        # A blank page: no barline ink anywhere.
        page = _make_page()
        staves = _make_staves()
        pws = PageWithStaves(page=page, staves=staves, barlines=[])
        cells = _measure_cells(staves, _SUB2X_BOUNDARIES)

        # Both staves read 3 here, so make the majority DEMAND more than the
        # page can honestly supply and confirm nothing is fabricated.
        out = resegment_fused_measures(
            pws, cells, max_cell_width=TEST_MAX_CELL_WIDTH,
            expected_bars_by_system={0: 5})
        assert len(out) == len(cells), "no ink -> no split, whatever the count says"
        assert _staff_measure_widths(out, 0) == _staff_measure_widths(cells, 0)

    def test_majority_feeds_resegmentation_without_fabricating(self):
        page = _make_page()
        staves = _make_staves()
        pws = PageWithStaves(page=page, staves=staves, barlines=[])
        cells = _measure_cells(staves, _SUB2X_BOUNDARIES)

        expected = majority_bars_by_system(cells)
        assert expected == {0: 3}, "both staves read 3 -> that is the majority"

        out = resegment_fused_measures(
            pws, cells, max_cell_width=TEST_MAX_CELL_WIDTH,
            expected_bars_by_system=expected)
        assert len(out) == len(cells), "count already met -> steering inert"


# ─── One-line percussion staves must not reach the barline scanner ───────────


class TestOneLineStaffIsExcludedFromResegmentation:
    """A percussion part printed as a single rule has no five-line span.

    `detect_barlines` and `extract_measures` both exclude such staves, because
    a staff two spaces tall votes "barline" for every stem that crosses it.
    `resegment_fused_measures` did not, and there the omission was not merely
    noise: `_detect_barlines_in_window` sizes its morphological kernel from the
    staff span, so a span of 0 asks OpenCV for a 1x0 kernel and it raises.

    Found by the majority-steering probe on La Mer p.25 — the very page the
    one-line-staff support was validated on, which could not be transcribed at
    all until this guard was added."""

    def _system_with_a_one_line_staff(self):
        staves = _make_staves()
        # A single rule sitting between the two real staves: one line_y, so
        # top_y == bottom_y and the span is 0.
        staves.append(Staff(page_index=0, staff_index=2, line_ys=[210],
                            x_start=50, x_end=850, system_index=0))
        return staves

    def test_zero_span_staff_does_not_raise(self):
        page = _make_page()
        _draw_barline(page.binary, 430)
        staves = self._system_with_a_one_line_staff()
        pws = PageWithStaves(page=page, staves=staves, barlines=[])
        cells = _measure_cells(_make_staves(), BOUNDARIES)  # cells for the 5-line staves only

        out = resegment_fused_measures(pws, cells, max_cell_width=TEST_MAX_CELL_WIDTH)
        assert out, "a one-line staff in the system must not break Phase 1"

    def test_zero_span_staff_does_not_raise_when_steered(self):
        page = _make_page()
        _draw_barline(page.binary, 430)
        staves = self._system_with_a_one_line_staff()
        pws = PageWithStaves(page=page, staves=staves, barlines=[])
        cells = _measure_cells(_make_staves(), _SUB2X_BOUNDARIES)

        # The majority here is 3 and both staves read 3, so steering would be
        # inert and would never reach the barline scanner. Demand 4 to force the
        # steered branch to run.
        assert majority_bars_by_system(cells) == {0: 3}
        out = resegment_fused_measures(
            pws, cells, max_cell_width=TEST_MAX_CELL_WIDTH,
            expected_bars_by_system={0: 4})
        assert out, "the steered path must be guarded too"


# ─── system furniture read as a measure ─────────────────────────────────────


class TestFurnitureMeasuresAreDropped:
    """Dvorak 9's Simrock print opens every system with a 56-px cell holding one
    `brace` at confidence 0.33, so all fifteen staves emit nine measures where
    the page prints eight. Width does not separate that from a genuine bar
    (4.2 spaces on a compressed rest bar against 2.2 here); content does."""

    @staticmethod
    def _note(x=20.0):
        return {"class": "noteheadBlackOnLine", "category": "notehead",
                "bbox": [x, 10, 5, 5], "bbox_page": [x, 10, 5, 5],
                "confidence": 0.9, "pitch": "C4", "duration_beats": 1.0,
                "duration_type": "quarter", "dots": 0}

    @staticmethod
    def _rest():
        return {"class": "restWhole", "category": "rest", "bbox": [20, 10, 6, 4],
                "bbox_page": [20, 10, 6, 4], "confidence": 0.8,
                "duration_beats": 4.0, "duration_type": "whole", "dots": 0}

    @staticmethod
    def _brace():
        return {"class": "brace", "category": "structural", "bbox": [2, 0, 3, 60],
                "bbox_page": [2, 0, 3, 60], "confidence": 0.33}

    def _page(self, per_staff):
        """`per_staff` is a list of lists of detection lists."""
        return {"page_index": 0, "systems": [{"system_index": 0, "staves": [
            {"staff_index": si, "n_measures": len(cells),
             "measures": [{"measure_index": mi, "bbox_page_px": [0, 0, 100, 50],
                           "detections": dets}
                          for mi, dets in enumerate(cells)]}
            for si, cells in enumerate(per_staff)]}]}

    def _measures(self, page):
        return [len(s["measures"]) for s in page["systems"][0]["staves"]]

    def test_a_leading_brace_only_column_is_dropped_from_every_staff(self):
        page = self._page([
            [[self._brace()], [self._note()], [self._note()]],
            [[], [self._rest()], [self._note()]],
        ])
        cells, dets = _drop_furniture_measures(page)
        assert (cells, dets) == (2, 1)
        assert self._measures(page) == [2, 2]
        assert [m["measure_index"] for m in
                page["systems"][0]["staves"][0]["measures"]] == [0, 1]

    def test_a_column_where_ONE_staff_plays_is_a_measure(self):
        """Per-staff emptiness says nothing — any staff may be tacet. Only a
        column silent on EVERY staff is furniture."""
        page = self._page([
            [[self._brace()], [self._note()]],
            [[self._note()], [self._note()]],
        ])
        assert _drop_furniture_measures(page) == (0, 0)
        assert self._measures(page) == [2, 2]

    def test_a_tacet_staff_keeps_the_column_through_its_whole_bar_rest(self):
        page = self._page([[[self._rest()], [self._note()]],
                           [[self._rest()], [self._note()]]])
        assert _drop_furniture_measures(page) == (0, 0)

    def test_a_trailing_courtesy_column_is_dropped(self):
        page = self._page([[[self._note()], [self._note()], []],
                           [[self._note()], [self._note()], [self._brace()]]])
        cells, _ = _drop_furniture_measures(page)
        assert cells == 2 and self._measures(page) == [2, 2]

    def test_a_silent_column_in_the_MIDDLE_is_kept(self):
        """A spurious barline mid-system splits one bar into two halves that
        both still hold notes, so a music-free middle column is far more likely
        a bar the detector failed on — and dropping it would splice its
        neighbours together and shift every measure after it."""
        page = self._page([[[self._note()], [], [self._note()]],
                           [[self._note()], [], [self._note()]]])
        assert _drop_furniture_measures(page) == (0, 0)
        assert self._measures(page) == [3, 3]

    def test_a_system_with_no_music_at_all_is_left_alone(self):
        """A recognition failure, not a furniture question. Deleting its
        measures would turn a bad reading into no reading."""
        page = self._page([[[self._brace()], []], [[], []]])
        assert _drop_furniture_measures(page) == (0, 0)
        assert self._measures(page) == [2, 2]

    def test_a_single_measure_system_is_never_touched(self):
        page = self._page([[[self._brace()]], [[]]])
        assert _drop_furniture_measures(page) == (0, 0)


# ── cue C: grouped systems are not open scores (OMR_CHOIR_GROUPING) ─────────
#
# detect_barlines asks "do this system's barlines cross the inter-staff gaps?"
# by comparing connected vs unconnected vote-accepted COLUMNS, and a
# rhythmic-unison tutti answers wrong: aligned stems pass the vote, none of
# them connected, and the unconnected columns outnumber the true barlines, so
# a conductor's page flips into open-score mode and every stem column stands
# (the Brandenburg 3 family — benchmarks/omr-choir-grouping-2026-09/).
# Cue C (opt-in) reads the answer off the STAVES instead: a system whose
# staves form ≥2 bracket-groups, at least half of them in multi-staff groups,
# is a grouped ensemble system, which a true open score can never be.

from tools.omr.measure_extractor import _is_grouped_system, detect_barlines


def _staff_with_group(idx: int, ys: list[int], group: int,
                      x0: int = 40, x1: int = 960) -> Staff:
    s = Staff(page_index=0, staff_index=idx, line_ys=ys, x_start=x0, x_end=x1)
    s.system_index = 0
    s.group_index = group
    return s


def _five(top: int) -> list[int]:
    return [top + 20 * i for i in range(5)]


def test_is_grouped_system_truth_table():
    mk = _staff_with_group
    # one group (the default everywhere the gap-size fallback grouped) → False
    assert not _is_grouped_system([mk(i, _five(100 + 100 * i), 0) for i in range(4)])
    # two choirs of three → True (the Bach family)
    groups = [0, 0, 0, 1, 1, 1]
    assert _is_grouped_system(
        [mk(i, _five(100 + 100 * i), g) for i, g in enumerate(groups)])
    # the full Bach structure [3, 3, 3, 1, 2] → True (11 of 12 in multi)
    groups = [0] * 3 + [1] * 3 + [2] * 3 + [3] + [4] * 2
    assert _is_grouped_system(
        [mk(i, _five(100 + 100 * i), g) for i, g in enumerate(groups)])
    # a vocal page: four singleton voices + one keyboard pair → False —
    # most staves are NOT in multi-staff groups, so open-score mode (where
    # per-staff barlines survive on votes alone) is preserved.
    groups = [0, 1, 2, 3, 4, 4]
    assert not _is_grouped_system(
        [mk(i, _five(100 + 100 * i), g) for i, g in enumerate(groups)])


def _choir_barred_page_with_unison_stems():
    """Two 3-staff choirs in ONE system. Real barlines drawn through each
    choir (never between choirs); 'stems' drawn through every staff
    individually at x-positions aligned across all six staves — the
    rhythm-unison signature that out-votes the barlines."""
    img = np.full((1200, 1000), 255, np.uint8)
    tops = [100, 200, 300, 460, 560, 660]     # choir gap between 300 and 460
    all_ys = [_five(t) for t in tops]
    for ys in all_ys:
        for y in ys:
            img[y:y + 2, 40:960] = 0
    # real barlines: through each choir's three staves and the gaps between
    for x in (60, 260, 460, 660, 860):
        img[all_ys[0][0]:all_ys[2][-1] + 2, x:x + 3] = 0
        img[all_ys[3][0]:all_ys[5][-1] + 2, x:x + 3] = 0
    # unison "stems": through each staff alone, aligned across all six.
    # Spaced >= BARLINE_MIN_DISTANCE_PX apart so per-staff thinning keeps
    # them all: the flip needs the unconnected columns to OUTNUMBER twice
    # the connected ones (9 stems vs 5 barlines here).
    for x in (130, 195, 330, 395, 530, 595, 730, 795, 925):
        for ys in all_ys:
            img[ys[0]:ys[-1] + 2, x:x + 2] = 0
    staves = []
    for i, ys in enumerate(all_ys):
        s = Staff(page_index=0, staff_index=i, line_ys=ys, x_start=40, x_end=960)
        s.system_index = 0
        s.group_index = 0 if i < 3 else 1
        staves.append(s)
    page = PageImage(pdf_path=Path("synthetic.pdf"), page_index=0, dpi=300,
                     rgb=np.dstack([img] * 3), binary=img)
    return PageWithStaves(page=page, staves=staves)


def test_open_score_flip_accepts_unison_stems_without_cue_c(monkeypatch):
    """The disease, pinned: flag off (explicit opt-out since the 2026-09-05
    default flip), the unconnected stem columns outnumber the five true
    barlines, the gate flips to open-score mode and the stems stand."""
    monkeypatch.setenv("OMR_CHOIR_GROUPING", "0")
    pws = detect_barlines(_choir_barred_page_with_unison_stems())
    xs = sorted(b.x for b in pws.barlines)
    assert len(xs) > 5, f"expected stem columns to be accepted, got {xs}"


def test_cue_c_keeps_a_grouped_system_out_of_open_score_mode(monkeypatch):
    monkeypatch.setenv("OMR_CHOIR_GROUPING", "1")
    pws = detect_barlines(_choir_barred_page_with_unison_stems())
    xs = sorted(b.x for b in pws.barlines)
    assert len(xs) == 5, f"expected exactly the five true barlines, got {xs}"
    assert all(abs(x - t) <= 3 for x, t in zip(xs, (60, 260, 460, 660, 860)))


def test_cue_c_leaves_ungrouped_systems_in_open_score_mode(monkeypatch):
    """A true open score has no bracket-groups (group_index all 0), so cue C
    must not touch it even with the flag on: votes remain the whole of the
    evidence there."""
    monkeypatch.setenv("OMR_CHOIR_GROUPING", "1")
    pws = _choir_barred_page_with_unison_stems()
    for s in pws.staves:
        s.group_index = 0
    out = detect_barlines(pws)
    xs = sorted(b.x for b in out.barlines)
    assert len(xs) > 5, "no group evidence -> open-score mode must survive"


def test_cue_c_requires_a_window_blind_gap(monkeypatch):
    """The engraved-benchmark falsification, pinned (condition 2): a true
    open score whose gaps are ALL touched by its systemic start barline —
    the LilyPond orchestral fixture shape — must stay in open-score mode
    even when bridging jitter has manufactured bracket-groups. Same fixture
    as the choir page plus one left rule crossing every gap; group indices
    unchanged. Cue C fired here before condition 2 and deleted the real
    barlines of nine engraved works (pooled 0.1306 -> 0.8560)."""
    monkeypatch.setenv("OMR_CHOIR_GROUPING", "1")
    pws = _choir_barred_page_with_unison_stems()
    img = pws.page.binary
    top = pws.staves[0].line_ys[0]
    bot = pws.staves[-1].line_ys[-1] + 2
    img[top:bot, 44:46] = 0  # systemic start barline through the choir gap too
    out = detect_barlines(pws)
    xs = sorted(b.x for b in out.barlines)
    assert len(xs) > 5, (
        "no window-blind gap -> open-score mode must survive, votes stand")
