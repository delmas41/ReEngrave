"""Unit tests for staff-line removal.

Synthetic cells, so they run without a PDF. Each one is a shape that decided
the design: a line thicker than the old fixed neighbourhood, a symbol crossing
that must survive whole, a line that wanders, and a beam lying along a line.
"""

from __future__ import annotations

import numpy as np
import pytest

from tools.omr.staff_line_removal import (
    LINE_CROSSING_FACTOR,
    MAX_ERASABLE_RUN_SPACES,
    _line_thickness,
    _vertical_runs_through,
    remove_staff_lines_from_cell,
)
from tools.omr.types import MeasureCell


SPACING = 100          # canonical staff spacing
LINE_YS = [100, 200, 300, 400, 500]


def _cell(paint=None, thickness: int = 6, wander: int = 0, width: int = 600) -> MeasureCell:
    """A blank cell with five staff lines of the given printed thickness.

    `paint(img)` may add symbols. `wander` shifts each line's y by up to that
    many pixels along its length, the way a real printed line drifts.
    """
    h = 640
    img = np.full((h, width), 255, dtype=np.uint8)
    for y in LINE_YS:
        for x in range(width):
            dy = int(round(wander * np.sin(x / 90.0)))
            top = y + dy - thickness // 2
            img[max(0, top):max(0, top) + thickness, x] = 0
    if paint is not None:
        paint(img)
    return MeasureCell(
        page_index=0, system_index=0, staff_index=0, measure_index=0,
        image=img, image_no_staff=None, bbox_page_px=(0, 0, width, h),
        staff_line_ys_canonical=list(LINE_YS), upscale_factor=1.0,
    )


def _ink_on_lines(img: np.ndarray, radius: int = 1) -> int:
    return sum(int((img[y - radius:y + radius + 1] == 0).sum()) for y in LINE_YS)


class TestVerticalRuns:

    def test_measures_a_run_through_the_row(self):
        ink = np.zeros((50, 4), dtype=bool)
        ink[20:30, 1] = True          # a 10px run through row 25
        heights, tops, bottoms, present = _vertical_runs_through(ink, 25, max_search=40)
        assert present[1] and heights[1] == 10
        assert tops[1] == 20 and bottoms[1] == 29
        assert not present[0] and heights[0] == 0

    def test_a_gap_ends_the_run(self):
        ink = np.zeros((50, 2), dtype=bool)
        ink[20:25, 0] = True
        ink[26:40, 0] = True          # separated by one blank row
        heights, _, _, _ = _vertical_runs_through(ink, 22, max_search=40)
        assert heights[0] == 5


class TestLineThickness:

    def test_ignores_columns_carrying_a_symbol(self):
        heights = np.array([6, 6, 6, 6, 120, 140, 6, 6], dtype=float)
        assert _line_thickness(heights, cap=35) == pytest.approx(6.0)

    def test_falls_back_to_the_cap_when_nothing_looks_like_a_line(self):
        heights = np.array([200.0, 300.0])
        assert _line_thickness(heights, cap=35) == 35.0


class TestRemoval:

    def test_a_thick_line_is_erased(self):
        """The regression that mattered: a line thicker than the old fixed
        +-4px neighbourhood used to preserve itself, so nothing was removed."""
        cell = _cell(thickness=20)
        before = _ink_on_lines(cell.image)
        out = remove_staff_lines_from_cell(cell)
        assert before > 0
        assert _ink_on_lines(out) == 0, "a 20px line must still be removed"

    @pytest.mark.parametrize("thickness", [2, 6, 12, 20, 30])
    def test_erased_at_every_printed_thickness(self, thickness):
        cell = _cell(thickness=thickness)
        out = remove_staff_lines_from_cell(cell)
        assert _ink_on_lines(out) == 0

    def test_a_wandering_line_is_erased_along_its_path(self):
        cell = _cell(thickness=8, wander=4)
        out = remove_staff_lines_from_cell(cell)
        remaining = int((out == 0).sum())
        assert remaining == 0, f"{remaining} px of a wandering line survived"

    def test_a_crossing_stem_survives_whole(self):
        def paint(img):
            img[80:520, 300:308] = 0        # a stem through all five lines
        cell = _cell(thickness=8, paint=paint)
        out = remove_staff_lines_from_cell(cell)
        column = out[80:520, 303]
        assert (column == 0).all(), "the stem must not be cut where lines crossed it"

    def test_a_notehead_on_a_line_survives(self):
        def paint(img):
            img[270:330, 200:260] = 0       # notehead centred on line 3
        cell = _cell(thickness=8, paint=paint)
        out = remove_staff_lines_from_cell(cell)
        assert (out[270:330, 200:260] == 0).all()

    def test_a_beam_lying_along_a_line_is_not_erased(self):
        """A beam is about half a staff space thick. On a page whose lines are
        already thick, 2x thickness would reach past it — MAX_ERASABLE_RUN_SPACES
        is what stops that."""
        beam_h = int(0.5 * SPACING)
        def paint(img):
            img[300 - beam_h // 2:300 + beam_h // 2, 350:550] = 0
        cell = _cell(thickness=28, paint=paint)
        out = remove_staff_lines_from_cell(cell)
        kept = (out[300 - beam_h // 2:300 + beam_h // 2, 400:500] == 0).mean()
        assert kept > 0.9, f"only {kept:.0%} of the beam survived"
        assert MAX_ERASABLE_RUN_SPACES < 0.5

    def test_blank_paper_between_lines_is_untouched(self):
        cell = _cell(thickness=8)
        out = remove_staff_lines_from_cell(cell)
        assert (out[140:160] == 255).all()

    def test_sets_the_field_in_place_and_keeps_the_shape(self):
        cell = _cell()
        out = remove_staff_lines_from_cell(cell, in_place=True)
        assert cell.image_no_staff is not None
        assert cell.image_no_staff.shape == cell.image.shape[:2]
        assert out.shape == cell.image.shape[:2]

    def test_the_crossing_factor_is_the_documented_one(self):
        assert LINE_CROSSING_FACTOR == 2.0
