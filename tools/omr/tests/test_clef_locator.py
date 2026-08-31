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

import dataclasses

import cv2
import numpy as np
import pytest

from tools.omr.clef_locator import (
    ClefLocatorConfig,
    DEFAULT_LOCATOR_CONFIG,
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
    a heavy loop up top and a long tail hanging below the staff.

    The loop is drawn as a stroke rather than a filled block, because a filled
    one is not what the locator sees. `strip_horizontal_rules` erases ink
    belonging to any run of 1.5 staff spaces or more, so a solid 2-space-wide
    rectangle is removed outright and what reached the gates was the 0.4-space
    tail — narrower than any real G clef, which measures 2.55 to 3.18 spaces
    across the engraved reference sheet and the piano corpus. The width of this
    glyph is load-bearing for the test below, so it has to be real.
    """
    cv2.ellipse(img, (x + 20, 110), (20, 40), 0, 0, 360, 0, 11)   # the loop
    cv2.rectangle(img, (x + 16, 150), (x + 24, 250), 0, -1)       # the tail
    cv2.circle(img, (x + 20, 245), 10, 0, -1)


def draw_heading_above(img: np.ndarray, x: int = 24) -> None:
    """A movement heading printed above the staff, in the clef's own column —
    "Nr. 15.", a rehearsal letter, a marking. Real ink, well clear of the top
    staff line, and the thing that used to fuse with the clef.

    Drawn as letterforms rather than a solid block, for the same reason the G
    clef is drawn as a stroke: `strip_horizontal_rules` erases ink belonging to
    a run of 1.5 staff spaces or more, so a filled block of heading-sized text
    is removed outright and cannot fuse with anything. Type has strokes, and
    the strokes are what survives.
    """
    for dx in (0, 13, 26):
        cv2.rectangle(img, (x + dx, 56), (x + dx + 7, 88), 0, -1)      # stems
        cv2.rectangle(img, (x + dx - 2, 56), (x + dx + 9, 61), 0, -1)  # serifs
        cv2.rectangle(img, (x + dx - 2, 83), (x + dx + 9, 88), 0, -1)


def draw_split_g_clef(img: np.ndarray, x: int = 22) -> None:
    """A G clef whose body and tail have come apart, as they do on a scan: the
    stroke thins where it crosses the staff and the morphology severs it. The
    gap here is 0.7 staff spaces, wider than the vertical tolerance — measured
    at 0.49 on Beethoven 5 — and BOTH pieces touch the staff, which is what
    must keep them together."""
    cv2.ellipse(img, (x + 20, 110), (20, 40), 0, 0, 360, 0, 11)   # the body
    cv2.rectangle(img, (x + 16, 164), (x + 24, 250), 0, -1)       # the tail
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


class TestTheVerticalGroupingRule:
    """Grouping header ink by proximity in BOTH axes, not just across.

    ON by default since it was measured against a corpus that could see both
    of its sides — see `ClefLocatorConfig.cluster_y_gap_spaces`. These tests
    pin what it does, what the page looked like without it, and that it is on.
    """

    OFF = dataclasses.replace(DEFAULT_LOCATOR_CONFIG, cluster_y_gap_spaces=None)

    def _heading_cell(self):
        img = blank_page()
        draw_c_clef(img, 3)
        draw_heading_above(img)
        draw_noteheads(img)
        return make_cell(img)

    def test_it_is_on_by_default(self):
        assert DEFAULT_LOCATOR_CONFIG.cluster_y_gap_spaces == 1.0

    def test_a_heading_above_the_staff_hides_the_clef_when_it_is_off(self):
        # What the layer did before, and the thing the rule exists to fix: the
        # heading and the clef are one column 5.5 staff spaces tall, which is
        # bigger than any C clef, so the search stops on it.
        assert locate_clef(self._heading_cell(), config=self.OFF) is None

    def test_a_heading_above_the_staff_does_not_hide_the_clef(self):
        # Measured over 191 headers of 19th-century engraving, that fusion was
        # 55% of all header cells — the single largest drain on clef coverage.
        found = locate_clef(self._heading_cell())
        assert found is not None and found.read.name == "alto"

    def test_ink_touching_the_staff_is_never_split_apart(self):
        """The safety half of the rule, and the reason it is restricted to ink
        standing clear of the staff.

        A glyph printed ON the staff arrives in pieces — the morphology severs
        its strokes where they cross a line — and those pieces must stay
        together whatever the gap between them, because half a treble clef is
        the size and shape of a C clef. Applied to all ink instead, at a
        tolerance small enough to be useful, this invented seventeen C clefs
        across twenty pages of a Beethoven 5 scan that has none there.
        """
        img = blank_page()
        draw_split_g_clef(img)
        draw_noteheads(img)
        assert locate_clef(make_cell(img)) is None


# ─── the margin is not the staff ────────────────────────────────────────────


class TestInkBeforeTheStaffBegins:
    """A clef is printed ON the staff, so glyph-sized ink standing in the
    margin is skipped rather than stopped for.

    The case is Edition Peters, which prints the stacked instrument numbers
    (1/2, 1/2/3) to the left of the system's bracket, close enough to fall
    inside the header window. A column of numerals is glyph-sized AND
    vertically symmetric — no shape gate can refuse it, because it really is
    symmetric — so what gives it away is where it stands. Twenty-four of the
    forty-one false positives on `mahler5-clef-sweep.json` are that family.
    """

    OFF = dataclasses.replace(DEFAULT_LOCATOR_CONFIG,
                              require_cluster_on_staff=False)
    # Where the staff's own lines begin. Everything here has to fit inside the
    # `header_frac` strip the locator searches (30% of the cell), which is what
    # a real header window gives it: the margin ink at its left, the clef a few
    # spaces in, and room to spare.
    STAFF_X0 = 70

    def _margin_and_clef(self, with_clef: bool):
        """A page whose staff starts at STAFF_X0, with a symmetric numeral
        stack in the margin before it."""
        img = np.full((CELL_H, CELL_W), 255, dtype=np.uint8)
        for y in STAFF_LINES:
            cv2.line(img, (self.STAFF_X0, y), (CELL_W - 1, y), 0, 2)
        # The bracket, at the staff's left edge.
        cv2.rectangle(img, (self.STAFF_X0 - 8, 100), (self.STAFF_X0 - 3, 180), 0, -1)
        # Two numerals stacked in the margin: glyph-sized, and symmetric about
        # the gap between them, which is what makes them dangerous.
        for dy in (-16, 16):
            cv2.rectangle(img, (16, line_y(3) + dy - 9), (34, line_y(3) + dy + 9), 0, -1)
        if with_clef:
            draw_c_clef(img, 3, x=self.STAFF_X0 + 6)
        draw_noteheads(img)
        return make_cell(img)

    def test_the_margin_stack_does_not_become_the_clef(self):
        # Without the rule the numerals are the leftmost glyph-sized cluster,
        # so they are what the locator reads.
        assert locate_clef(self._margin_and_clef(with_clef=False),
                           config=self.OFF) is not None
        # With it, a staff whose only glyph-sized header ink is in the margin
        # reads nothing, which is the right answer.
        assert locate_clef(self._margin_and_clef(with_clef=False)) is None

    def test_the_clef_behind_the_stack_is_still_found(self):
        # SKIPPED, not stopped for — the same reasoning the ink-fraction and
        # minimum-width tests already use. If this returned None the rule would
        # buy its precision by throwing the clef away too.
        found = locate_clef(self._margin_and_clef(with_clef=True))
        assert found is not None and found.read.line == 3

    def test_the_branch_is_reported_apart_from_debris(self):
        trace: dict = {}
        locate_clef(self._margin_and_clef(with_clef=False), trace=trace)
        assert trace["reason"] == "off_staff_only"
        assert trace["skipped_off_staff"] >= 1


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
        # Erase the dots, and ONLY the dots. This used to be a white column
        # through the whole cell, which also severed all five staff lines and
        # so moved where the staff appears to begin — nothing a print does,
        # but enough to trip the margin test (`require_cluster_on_staff`).
        cy = line_y(4)
        for dy in (-SPACING // 2, SPACING // 2):
            cv2.circle(img, (22 + 34, cy + dy), 7, 255, -1)
        found = locate_clef(make_cell(img))
        assert found is not None and found.read.line == 4

    def test_sparse_residue_does_not_block_the_clef_behind_it(self):
        """Stripping the system brace leaves a trail of specks down the left
        edge. They are nothing individually, but x-clustering draws one box
        around them, and a box 1.4 x 8 staff spaces reads as "bigger than any C
        clef" — so the locator used to stop on it and never look at the clef
        1.5 spaces to its right.

        Measured on Nottebohm p.164: five specks at 6% of their bounding box
        blocked a textbook 2.3 x 3.2-space alto clef. The ink-fraction test now
        runs BEFORE the size test, so a cluster has to be a glyph before it is
        worth stopping for.
        """
        img = blank_page()
        for x, y in ((20, 58), (32, 72), (44, 58), (20, 200), (32, 214), (44, 200)):
            cv2.rectangle(img, (x, y), (x + 3, y + 11), 0, -1)
        draw_c_clef(img, 3, x=70)
        found = locate_clef(make_cell(img))
        assert found is not None and found.read.name == "alto"

    def test_a_solid_oversized_glyph_still_stops_the_search(self):
        # The complement, and the one that must not break: a G clef is solid,
        # so it clears the ink test and still stops the search. Without this
        # the reordering above would reopen the read-the-key-signature bug.
        img = blank_page()
        draw_g_clef(img)
        draw_c_clef(img, 3, x=110)   # a C clef further in must NOT be taken
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


class TestTheDotVetoCanSeeTheDots:
    """The veto was being asked to find the dots in pixels it had never been shown.

    `benchmarks/omr-clef-geometry/RESULTS.md` — "the veto could not see the
    dots". Two crops stood between it and the evidence: it was handed the
    `header_frac` STRIP rather than the full mask, and it looked only INSIDE the
    candidate's own box. An F clef's dots are to the right of its body, so on
    Beethoven 5 p.54 staff 8 both sat past the strip's edge and the veto could
    not have fired whatever its thresholds were.
    """

    def test_it_searches_past_the_candidate_box(self):
        from tools.omr.clef_locator import DEFAULT_LOCATOR_CONFIG
        assert DEFAULT_LOCATOR_CONFIG.dot_search_right_spaces > 0, (
            "the dots belong to the glyph but need not belong to the candidate")

    def test_dots_just_right_of_the_body_are_found(self):
        """A body, and two dots beyond its right edge — where the search window
        reaches but the candidate box does not."""
        import numpy as np
        from tools.omr.clef_locator import DEFAULT_LOCATOR_CONFIG, _has_f_clef_dots

        spacing = 22.0
        mask = np.zeros((int(6 * spacing), int(8 * spacing)), np.uint8)
        # body: 2 spaces wide, 3 tall, starting one space in
        bx, by = int(spacing), int(spacing)
        bw, bh = int(2 * spacing), int(3 * spacing)
        mask[by:by + bh, bx:bx + bw] = 255
        # two dots, half a space PAST the body's right edge, one space apart
        r = int(0.18 * spacing)
        for cy in (by + int(1.0 * spacing), by + int(2.0 * spacing)):
            cx = bx + bw + int(0.4 * spacing)
            mask[cy - r:cy + r, cx - r:cx + r] = 255
        assert _has_f_clef_dots(mask, (bx, by, bw, bh), spacing,
                                DEFAULT_LOCATOR_CONFIG) is True

    def test_the_right_fraction_is_measured_against_the_body(self):
        """Widening the search must not move the line the `right of the body`
        test is measured against, or a dot on the body's LEFT would start
        passing as the window grew."""
        import numpy as np
        from tools.omr.clef_locator import DEFAULT_LOCATOR_CONFIG, _has_f_clef_dots

        spacing = 22.0
        mask = np.zeros((int(6 * spacing), int(8 * spacing)), np.uint8)
        bx, by = int(spacing), int(spacing)
        bw, bh = int(2 * spacing), int(3 * spacing)
        r = int(0.18 * spacing)
        # a pair on the LEFT of the body — never an F clef's dots
        for cy in (by + int(1.0 * spacing), by + int(2.0 * spacing)):
            cx = bx + int(0.15 * spacing)
            mask[cy - r:cy + r, cx - r:cx + r] = 255
        assert _has_f_clef_dots(mask, (bx, by, bw, bh), spacing,
                                DEFAULT_LOCATOR_CONFIG) is False


class TestMezzosopranoMustBeBetterEvidenced:
    """A rarer answer has to be better evidenced.

    Mezzosoprano is the rarest of the five C clefs by a long way. Over 101
    located candidates on a scanned Beethoven 5 it is named five times and is
    wrong all five — four G clefs whose surviving fragment balances about line 2,
    which is the line a G clef curls around, and one F clef. The one real
    mezzosoprano in any corpus scores 0.981; the five misreads score 0.712-0.815.
    See `benchmarks/omr-clef-geometry/beethoven5-clef-sweep.json`.
    """

    def test_the_floor_is_above_every_measured_misread_and_below_the_real_one(self):
        from tools.omr.clef_locator import DEFAULT_LOCATOR_CONFIG as C
        assert 0.815 < C.min_symmetry_mezzosoprano < 0.981, (
            "the five misreads top out at 0.815 and the reference sheet's real "
            "mezzosoprano scores 0.981 — the floor has to sit between them")

    def test_it_is_stricter_than_the_general_floor_and_only_for_this_clef(self):
        from tools.omr.clef_locator import DEFAULT_LOCATOR_CONFIG as C
        assert C.min_symmetry_mezzosoprano > C.min_symmetry, (
            "asking MORE of the rare answer is the whole idea; a general raise "
            "would cost the scanned alto and tenor clefs, which score 0.70-0.80")
