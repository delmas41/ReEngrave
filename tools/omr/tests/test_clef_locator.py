"""Tests for the classical-CV C-clef locator.

Cells are drawn here rather than loaded, so the tests exercise the real
pipeline — rule stripping, clustering, the symmetry gate, the snap — against
glyphs whose named line is known by construction. The synthetic C clef is
deliberately the archaic "ladder" shape (two verticals joined by two bars)
rather than a modern font's curl: it is the shape that motivated the module,
and it shares the only property the method depends on, symmetry about the line
it names.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from tools.omr.clef_locator import (
    ClefLocatorConfig,
    _refine_symmetry_axis,
    _vertical_symmetry,
    locate_clef,
)
from tools.omr.types import MeasureCell


SPACING = 20
STAFF_LINES = [100, 120, 140, 160, 180]  # top → bottom; line 5 … line 1
CELL_H, CELL_W = 320, 420


def line_y(line_from_bottom: int) -> int:
    return STAFF_LINES[5 - line_from_bottom]


def blank_page() -> np.ndarray:
    """A white cell with staff lines and the system barline drawn in."""
    img = np.full((CELL_H, CELL_W), 255, dtype=np.uint8)
    for y in STAFF_LINES:
        cv2.line(img, (0, y), (CELL_W - 1, y), 0, 2)
    # The initial barline, three pixels from the clef — close enough that only
    # rule stripping can separate them, which is the point.
    cv2.rectangle(img, (8, 100), (13, 180), 0, -1)
    return img


def draw_c_clef_at(img: np.ndarray, centre_y: int, x: int = 22) -> None:
    """An archaic ladder C clef centred on `centre_y`: two vertical strokes
    joined by two bars, symmetric top-to-bottom.

    Stroke widths are chosen the way a real engraver's are, not minimally —
    a clef's strokes are visibly thicker than a barline (which is what lets
    the locator tell them apart) and its bars are shorter than a staff line
    (which is what lets them survive rule stripping).
    """
    half = 2 * SPACING  # the glyph spans two spaces either side of its line
    cv2.rectangle(img, (x, centre_y - half), (x + 11, centre_y + half), 0, -1)
    cv2.rectangle(img, (x + 16, centre_y - half), (x + 27, centre_y + half), 0, -1)
    for dy in (-SPACING // 2, SPACING // 2):
        cv2.rectangle(img, (x, centre_y + dy - 4), (x + 27, centre_y + dy + 4), 0, -1)


def draw_c_clef(img: np.ndarray, line_from_bottom: int, x: int = 22) -> None:
    """An archaic ladder C clef naming `line_from_bottom`."""
    draw_c_clef_at(img, line_y(line_from_bottom), x=x)


def draw_g_clef(img: np.ndarray, x: int = 22) -> None:
    """A stand-in for a G clef: much taller than any C clef, and lopsided —
    a heavy loop up top and a long tail hanging below the staff."""
    cv2.rectangle(img, (x, 70), (x + 40, 150), 0, -1)      # the loop
    cv2.rectangle(img, (x + 16, 150), (x + 24, 250), 0, -1)  # the tail
    cv2.circle(img, (x + 20, 245), 10, 0, -1)


def draw_noteheads(img: np.ndarray) -> None:
    """Some ordinary note ink further into the measure."""
    for i, cx in enumerate(range(180, 400, 60)):
        cv2.ellipse(img, (cx, line_y(1 + (i % 4))), (12, 8), 0, 0, 360, 0, -1)


def make_cell(img: np.ndarray, staff_lines: list[int] | None = None) -> MeasureCell:
    return MeasureCell(
        page_index=0,
        system_index=0,
        staff_index=0,
        measure_index=0,
        image=img,
        image_no_staff=None,  # force the module's own rule stripping
        bbox_page_px=(0, 0, CELL_W, CELL_H),
        staff_line_ys_canonical=(
            STAFF_LINES if staff_lines is None else staff_lines
        ),
        upscale_factor=1.0,
    )


def cell_with_c_clef(line_from_bottom: int) -> MeasureCell:
    img = blank_page()
    draw_c_clef(img, line_from_bottom)
    draw_noteheads(img)
    return make_cell(img)


# ─── reading the five C clefs ───────────────────────────────────────────────


class TestLocatesCClefs:
    @pytest.mark.parametrize(
        "line,expected",
        [
            (1, "soprano"),
            (2, "mezzosoprano"),
            (3, "alto"),
            (4, "tenor"),
            (5, "baritone"),
        ],
    )
    def test_each_line_gives_its_clef(self, line, expected):
        found = locate_clef(cell_with_c_clef(line))
        assert found is not None, f"no clef located for line {line}"
        assert found.read.name == expected
        assert found.read.line == line
        assert found.read.source == "geometry"

    def test_alto_and_tenor_are_told_apart(self):
        # One staff line between them, and nothing else — the distinction the
        # detector's class label cannot carry.
        alto = locate_clef(cell_with_c_clef(3))
        tenor = locate_clef(cell_with_c_clef(4))
        assert (alto.read.name, tenor.read.name) == ("alto", "tenor")

    def test_the_barline_is_not_mistaken_for_the_clef(self):
        # It is taller than the clef and sits to its left, three pixels away.
        found = locate_clef(cell_with_c_clef(3))
        assert found.bbox[0] > 13

    def test_symmetry_is_high_for_a_c_clef(self):
        found = locate_clef(cell_with_c_clef(3))
        assert found.symmetry > 0.9


# ─── declining to guess ─────────────────────────────────────────────────────


class TestAbstains:
    def test_a_g_clef_yields_nothing(self):
        img = blank_page()
        draw_g_clef(img)
        draw_noteheads(img)
        assert locate_clef(make_cell(img)) is None

    def test_a_g_clef_does_not_let_later_ink_stand_in_for_it(self):
        # The locator's most dangerous failure mode: skip the treble clef for
        # being too tall, then read the key signature's sharp — narrow, tall
        # and symmetric — as the staff's clef. It must stop at the G clef.
        img = blank_page()
        draw_g_clef(img)
        # Two key-signature sharps, drawn thick enough to pass every size gate
        # a clef passes, and symmetric about their own centres.
        for x in (90, 118):
            cv2.rectangle(img, (x, 108), (x + 11, 172), 0, -1)
            cv2.rectangle(img, (x + 14, 108), (x + 25, 172), 0, -1)
            for cy in (130, 150):
                cv2.rectangle(img, (x, cy - 4), (x + 25, cy + 4), 0, -1)
        assert locate_clef(make_cell(img)) is None

    def test_an_empty_staff_yields_nothing(self):
        assert locate_clef(make_cell(blank_page())) is None

    def test_notes_alone_are_not_a_clef(self):
        img = blank_page()
        draw_noteheads(img)
        assert locate_clef(make_cell(img)) is None

    def test_a_staff_without_five_lines_yields_nothing(self):
        img = blank_page()
        draw_c_clef(img, 3)
        assert locate_clef(make_cell(img, staff_lines=[100, 120, 140])) is None

    def test_a_clef_too_far_into_the_measure_yields_nothing(self):
        img = blank_page()
        draw_c_clef(img, 3, x=300)  # 15 staff spaces in — not a clef position
        assert locate_clef(make_cell(img)) is None

    def test_ambiguous_placement_yields_nothing(self):
        # Sitting in a space rather than on a line: no clef names that.
        img = blank_page()
        draw_c_clef_at(img, line_y(3) + SPACING // 2)
        assert locate_clef(make_cell(img)) is None


# ─── the measurement itself ─────────────────────────────────────────────────


class TestSymmetryMeasurement:
    def test_symmetry_rewards_a_balanced_profile(self):
        mask = np.zeros((40, 20), dtype=np.uint8)
        mask[5:10, :] = 255
        mask[30:35, :] = 255
        assert _vertical_symmetry(mask, (0, 0, 20, 40)) > 0.99

    def test_symmetry_punishes_a_one_sided_profile(self):
        mask = np.zeros((40, 20), dtype=np.uint8)
        mask[0:10, :] = 255  # all the ink at the top — a tail-less G clef
        assert _vertical_symmetry(mask, (0, 0, 20, 40)) < 0.3

    def test_the_axis_ignores_a_stray_fragment(self):
        # A balanced glyph plus a scrap at the bottom. The box's midpoint is
        # dragged down; the axis should stay on the glyph.
        mask = np.zeros((60, 20), dtype=np.uint8)
        mask[10:14, :] = 255
        mask[26:30, :] = 255          # glyph balanced about y = 20
        mask[57:59, 0:3] = 255        # the scrap
        box_centre = 30.0
        axis = _refine_symmetry_axis(mask, (0, 0, 20, 60), max_shift=15)
        assert abs(axis - 20) < abs(box_centre - 20)
        assert abs(axis - 20) <= 1.5

    def test_the_axis_search_is_bounded(self):
        # It refines; it must never wander to a different staff line.
        mask = np.zeros((60, 20), dtype=np.uint8)
        mask[0:4, :] = 255
        max_shift = 5
        axis = _refine_symmetry_axis(mask, (0, 0, 20, 60), max_shift=max_shift)
        assert abs(axis - 29.5) <= max_shift + 0.5


class TestConfig:
    def test_the_symmetry_gate_is_load_bearing(self):
        # Guards against the threshold silently doing nothing.
        cell = cell_with_c_clef(3)
        found = locate_clef(cell)
        assert found is not None
        strict = ClefLocatorConfig(min_symmetry=found.symmetry + 0.001)
        assert locate_clef(cell, config=strict) is None
