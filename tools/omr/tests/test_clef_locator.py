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


# A C clef is a compact glyph, and the drawing below has to be one too or the
# tests pass a shape no engraver prints. Measured: on the engraved reference
# sheet a C clef is 2.75 staff spaces wide by 4.0 tall — 0.68 wide over tall —
# and across 74 hand-checked archaic clefs in Nottebohm the ratio runs 0.50 to
# 1.26. This glyph was 1.4 by 4.0, a ratio of 0.35, narrower than anything in
# either corpus. Its width is fixed by the engraving: the bars have to stay
# under the 1.5-space run that `strip_horizontal_rules` erases, which is what
# lets them survive at all. So the height comes down to 2.6 spaces instead —
# squarely inside the 2.4-to-3.6 the real clefs measure, where 4.0 was taller
# than any of them — and the ratio lands at 0.54.
CLEF_W = 28   # 1.4 staff spaces: bars short enough to survive rule stripping
CLEF_HALF = int(1.3 * SPACING)


def draw_c_clef_at(img: np.ndarray, centre_y: int, x: int = 22) -> None:
    """An archaic ladder C clef centred on `centre_y`: two vertical strokes
    joined by two bars, symmetric top-to-bottom.

    Proportions follow real clefs rather than a schematic — see CLEF_W. Stroke
    widths are chosen the way a real engraver's are, not minimally: a clef's
    strokes are visibly thicker than a barline (which is what lets the locator
    tell them apart) and its bars are shorter than a staff line (which is what
    lets them survive rule stripping).
    """
    half = CLEF_HALF  # the glyph spans two spaces either side of its line
    cv2.rectangle(img, (x, centre_y - half), (x + 11, centre_y + half), 0, -1)
    cv2.rectangle(
        img, (x + CLEF_W - 11, centre_y - half), (x + CLEF_W, centre_y + half), 0, -1
    )
    for dy in (-SPACING // 2, SPACING // 2):
        cv2.rectangle(
            img, (x, centre_y + dy - 4), (x + CLEF_W, centre_y + dy + 4), 0, -1
        )


def draw_c_clef(img: np.ndarray, line_from_bottom: int, x: int = 22) -> None:
    """An archaic ladder C clef naming `line_from_bottom`."""
    draw_c_clef_at(img, line_y(line_from_bottom), x=x)


def draw_f_clef(img: np.ndarray, line_from_bottom: int = 4, x: int = 22) -> None:
    """An F clef: a body of roughly C-clef proportions plus the two dots that
    straddle the line it names. The body alone is deliberately drawn to pass
    the size and symmetry gates — that is the situation the dot veto exists
    for, and it is what a real bass clef did on Nottebohm p.31."""
    cy = line_y(line_from_bottom)
    # Body drawn to real clef proportions, so this cell reaches the dot veto
    # rather than being turned away earlier by the size or aspect gates — the
    # veto is what the test is about.
    cv2.rectangle(img, (x, cy - 26), (x + 11, cy + 26), 0, -1)
    cv2.rectangle(img, (x + 14, cy - 26), (x + 25, cy + 26), 0, -1)
    for dy in (-10, 10):
        cv2.rectangle(img, (x, cy + dy - 4), (x + 25, cy + dy + 4), 0, -1)
    for dy in (-SPACING // 2, SPACING // 2):   # the dots
        cv2.circle(img, (x + 34, cy + dy), 5, 0, -1)


def draw_g_clef(img: np.ndarray, x: int = 22) -> None:
    """A stand-in for a G clef: much taller than any C clef, and lopsided —
    a heavy loop up top and a long tail hanging below the staff."""
    cv2.rectangle(img, (x, 70), (x + 40, 150), 0, -1)      # the loop
    cv2.rectangle(img, (x + 16, 150), (x + 24, 250), 0, -1)  # the tail
    cv2.circle(img, (x + 20, 245), 10, 0, -1)


def draw_heading_above(img: np.ndarray, x: int = 24) -> None:
    """A movement heading printed above the staff, in the clef's own column —
    "Nr. 15.", a rehearsal letter, a marking. Real ink, well clear of the top
    staff line, and the thing that used to fuse with the clef."""
    cv2.rectangle(img, (x, 30), (x + 34, 62), 0, -1)


def draw_brace_bulge(img: np.ndarray, x: int = 20) -> None:
    """The waist of a system brace, as it survives rule stripping: a sliver to
    the left of the clef, vertically symmetric and wide enough to clear the
    width gate — 1.0 staff space by 4.5, where the real ones measured 0.68 to
    1.27 wide. It read as a C clef on four Nottebohm staves."""
    cv2.rectangle(img, (x, 96), (x + 20, 186), 0, -1)


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


class TestReadsPastTheFurniture:
    """What the header actually contains besides the clef."""

    def test_a_heading_above_the_staff_does_not_hide_the_clef(self):
        # The single largest drain on clef coverage: the heading sits in the
        # clef's own column, so grouping ink by its x-gap alone made one
        # cluster six-plus staff spaces tall and the search gave up on it.
        # Measured over 191 headers of 19th-century engraving, that was 55% of
        # them.
        img = blank_page()
        draw_c_clef(img, 3)
        draw_heading_above(img)
        draw_noteheads(img)
        found = locate_clef(make_cell(img))
        assert found is not None and found.read.name == "alto"

    def test_a_heading_below_the_staff_does_not_hide_the_clef(self):
        img = blank_page()
        draw_c_clef(img, 3)
        cv2.rectangle(img, (24, 220), (58, 252), 0, -1)   # a page number
        found = locate_clef(make_cell(img))
        assert found is not None and found.read.name == "alto"

    def test_the_brace_is_not_read_as_a_clef(self):
        # A brace's waist survives the rule stripping — it is wider than the
        # thin-rule allowance, and inside a header crop it is shorter than the
        # heavy-rule one — and what is left is symmetric and clef-sized. Only
        # its proportions give it away: it is a sliver, and a C clef is
        # compact.
        img = blank_page()
        draw_brace_bulge(img)
        draw_c_clef(img, 3, x=56)
        draw_noteheads(img)
        found = locate_clef(make_cell(img))
        assert found is not None and found.read.name == "alto"
        assert found.bbox[0] > 40, "read the brace instead of the clef"

    def test_a_brace_with_no_clef_behind_it_yields_nothing(self):
        img = blank_page()
        draw_brace_bulge(img)
        draw_noteheads(img)
        assert locate_clef(make_cell(img)) is None


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

    def test_an_f_clef_is_rejected_by_its_dots(self):
        # An F clef can wear a C clef's proportions — width, height and
        # symmetry all inside the range of real C clefs. Its two dots are what
        # give it away, and they are reliable because they are not decoration:
        # they straddle the line the clef names.
        img = blank_page()
        draw_f_clef(img, 4)
        draw_noteheads(img)
        assert locate_clef(make_cell(img)) is None

    def test_the_same_body_without_dots_is_read_as_a_c_clef(self):
        # Proves the dots are doing the rejecting, not the body's shape.
        img = blank_page()
        draw_f_clef(img, 4)
        # Erase the dots.
        cv2.rectangle(img, (48, 0), (70, CELL_H), 255, -1)
        found = locate_clef(make_cell(img))
        assert found is not None and found.read.line == 4

    def test_a_glyph_taller_than_any_c_clef_yields_nothing(self):
        # 4.8 staff spaces. The tallest C clef in either reference corpus is
        # 4.05 (engraved) / 3.59 (archaic), and the cap used to sit at 5.0 —
        # loose enough that a treble clef which had lost its tail measured
        # 4.86, passed, and named the wrong clef.
        img = blank_page()
        draw_c_clef_at(img, line_y(3))
        cv2.rectangle(img, (22, 92), (22 + CLEF_W, 188), 0, -1)
        draw_noteheads(img)
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

    def test_the_occupancy_check_overrides_the_shape_test(self):
        # Observed on Nottebohm p.21: where a cell begins PAST its clef, the
        # first cluster is real notation, and a stacked chord is tall,
        # glyph-sized and vertically symmetric enough to pass for a C clef.
        # The detector has already called those boxes noteheads, and a clef
        # never overlaps one — so occupancy beats shape, whatever shape says.
        cell = cell_with_c_clef(3)
        found = locate_clef(cell)
        assert found is not None
        assert locate_clef(cell, occupied_boxes=[found.bbox]) is None

    def test_a_real_clef_survives_the_occupancy_check(self):
        cell = cell_with_c_clef(3)
        elsewhere = [(300, 100, 30, 20)]  # a notehead further into the measure
        found = locate_clef(cell, occupied_boxes=elsewhere)
        assert found is not None and found.read.name == "alto"

    def test_ambiguous_placement_yields_nothing(self):
        # Sitting in a space rather than on a line: no clef names that.
        img = blank_page()
        draw_c_clef_at(img, line_y(3) + SPACING // 2)
        assert locate_clef(make_cell(img)) is None


# ─── the measurement itself ─────────────────────────────────────────────────


class TestSymmetryMeasurement:
    def test_a_balanced_profile_scores_high(self):
        mask = np.zeros((40, 20), dtype=np.uint8)
        mask[5:10, :] = 255
        mask[30:35, :] = 255
        _axis, score = _refine_symmetry_axis(mask, (0, 0, 20, 40), max_shift=5)
        assert score > 0.99

    def test_a_one_sided_profile_scores_low(self):
        # All the ink at the top — a G clef without its tail. The bounded
        # search must not be able to rescue it by sliding onto the ink.
        mask = np.zeros((60, 20), dtype=np.uint8)
        mask[0:12, :] = 255
        _axis, score = _refine_symmetry_axis(mask, (0, 0, 20, 60), max_shift=8)
        assert score < 0.5

    def test_the_axis_ignores_a_stray_fragment(self):
        # A balanced glyph plus a scrap at the bottom. The box's midpoint is
        # dragged down; the axis should stay on the glyph.
        mask = np.zeros((60, 20), dtype=np.uint8)
        mask[10:14, :] = 255
        mask[26:30, :] = 255          # glyph balanced about y = 20
        mask[57:59, 0:3] = 255        # the scrap
        box_centre = 30.0
        axis, _score = _refine_symmetry_axis(mask, (0, 0, 20, 60), max_shift=15)
        assert abs(axis - 20) < abs(box_centre - 20)
        assert abs(axis - 20) <= 1.5

    def test_the_axis_search_is_bounded(self):
        # It refines; it must never wander to a different staff line.
        mask = np.zeros((60, 20), dtype=np.uint8)
        mask[0:4, :] = 255
        max_shift = 5
        axis, _score = _refine_symmetry_axis(mask, (0, 0, 20, 60), max_shift=max_shift)
        assert abs(axis - 29.5) <= max_shift + 0.5


class TestConfig:
    def test_the_symmetry_gate_is_load_bearing(self):
        # Guards against the threshold silently doing nothing.
        cell = cell_with_c_clef(3)
        found = locate_clef(cell)
        assert found is not None
        strict = ClefLocatorConfig(min_symmetry=found.symmetry + 0.001)
        assert locate_clef(cell, config=strict) is None
