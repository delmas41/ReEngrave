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
    resegment_fused_measures,
)
from tools.omr.types import MeasureCell, PageImage, PageWithStaves, Staff


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


# ─── One-line percussion staves must not reach the barline scanner ───────────


class TestOneLineStaffIsExcludedFromResegmentation:
    """A percussion part printed as a single rule has no five-line span.

    `detect_barlines` and `extract_measures` both exclude such staves, because
    a staff two spaces tall votes "barline" for every stem that crosses it.
    `resegment_fused_measures` did not, and there the omission was not merely
    noise: `_detect_barlines_in_window` sizes its morphological kernel from the
    staff span, so a span of 0 asks OpenCV for a 1x0 kernel and it raises.

    La Mer p.25 is the page the one-line-staff support was validated on. Its
    regression test covers staff detection and stops short of transcription, so
    the page could not be read end to end until this guard was added."""

    def _system_with_a_one_line_staff(self):
        staves = _make_staves()
        # A single rule between the two real staves: one line_y, so
        # top_y == bottom_y and the span is 0.
        staves.append(Staff(page_index=0, staff_index=2, line_ys=[210],
                            x_start=50, x_end=850, system_index=0))
        return staves

    def test_zero_span_staff_does_not_raise(self):
        page = _make_page()
        _draw_barline(page.binary, 430)
        pws = PageWithStaves(page=page, staves=self._system_with_a_one_line_staff(),
                             barlines=[])
        cells = _measure_cells(_make_staves(), BOUNDARIES)  # cells for the 5-line staves

        out = resegment_fused_measures(pws, cells, max_cell_width=TEST_MAX_CELL_WIDTH)
        assert out, "a one-line staff in the system must not break Phase 1"
