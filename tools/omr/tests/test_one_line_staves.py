"""`OMR_ONE_LINE_STAVES` — admitting a one-line percussion staff to a cell.

`staff_detector._single_line_staff_rows` finds the single rule a percussion
part is printed on; `measure_extractor` then drops it at three sites, and the
staff reaches no cell, no detection and no export. This flag opens ONE of those
three, and these tests pin both halves of that: what the flag does, and — far
more important — what it does NOT do to the five-line staves beside it.

Synthetic, no PDFs, so they run in the default suite.

    staff 0: five lines, y 100..180, spacing 20
    staff 1: ONE line, y 240              (a percussion rule)
    staff 2: five lines, y 300..380, spacing 20
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tools.omr import measure_extractor as me
from tools.omr.measure_extractor import (
    CANONICAL_STAFF_SPAN_PX,
    _cell_span_px,
    _measure_x_boundaries,
    extract_measures,
)
from tools.omr.types import Barline, PageImage, PageWithStaves, Staff

PAGE_W = 1000
PAGE_H = 500
FIVE_A = [100, 120, 140, 160, 180]
ONE_LINE_Y = 240
FIVE_B = [300, 320, 340, 360, 380]
SPACING = 20.0


def _page() -> PageWithStaves:
    rgb = np.full((PAGE_H, PAGE_W, 3), 255, dtype=np.uint8)
    binary = np.full((PAGE_H, PAGE_W), 255, dtype=np.uint8)
    for ys in (FIVE_A, FIVE_B):
        for y in ys:
            binary[y, 60:860] = 0
            rgb[y, 60:860] = 0
    # The percussion rule runs wider than the staves' own content edge — which
    # is exactly why it must not vote on the system's x boundaries.
    binary[ONE_LINE_Y, 20:960] = 0
    rgb[ONE_LINE_Y, 20:960] = 0
    page = PageImage(pdf_path=Path("synthetic.pdf"), page_index=0,
                     rgb=rgb, binary=binary, dpi=300)
    staves = [
        Staff(page_index=0, staff_index=0, line_ys=list(FIVE_A),
              x_start=60, x_end=860, system_index=0),
        Staff(page_index=0, staff_index=1, line_ys=[ONE_LINE_Y],
              x_start=20, x_end=960, system_index=0,
              nominal_line_spacing_px=SPACING),
        Staff(page_index=0, staff_index=2, line_ys=list(FIVE_B),
              x_start=60, x_end=860, system_index=0),
    ]
    pws = PageWithStaves(page=page, staves=staves)
    pws.barlines = [
        Barline(page_index=0, system_index=0, x=460, y_top=95, y_bottom=385),
    ]
    return pws


def _cells(monkeypatch, flag: str | None):
    if flag is None:
        monkeypatch.delenv(me.ENV_ONE_LINE_STAVES, raising=False)
    else:
        monkeypatch.setenv(me.ENV_ONE_LINE_STAVES, flag)
    return extract_measures(_page(), max_cell_width=4096)


class TestFlagOff:
    def test_the_one_line_staff_produces_no_cell(self, monkeypatch):
        """The shipped behaviour, unchanged. This is what makes the ON test
        below meaningful rather than vacuous."""
        got = {c.staff_index for c in _cells(monkeypatch, None)}
        assert got == {0, 2}

    def test_explicit_zero_is_the_same_as_absent(self, monkeypatch):
        assert ({c.staff_index for c in _cells(monkeypatch, "0")}
                == {c.staff_index for c in _cells(monkeypatch, None)})


class TestFlagOn:
    def test_the_one_line_staff_now_produces_cells(self, monkeypatch):
        cells = _cells(monkeypatch, "1")
        assert {c.staff_index for c in cells} == {0, 1, 2}
        # And the same number of them as its neighbours: a percussion staff is
        # barred with the system, so a bar it is missing is a bar the export
        # would silently renumber.
        per_staff = {i: sum(1 for c in cells if c.staff_index == i)
                     for i in (0, 1, 2)}
        assert per_staff[1] == per_staff[0] == per_staff[2]

    def test_the_cell_arrives_at_the_SAME_SCALE_as_its_neighbours(
            self, monkeypatch):
        """The whole reason `_cell_span_px` exists.

        `_upscale_to_canonical` reads a span of 0 as "do not scale", so without
        the reconstructed span the percussion cell would reach the detector at
        page resolution while every other cell on the page arrives canonically
        upscaled — the inference-scale fault `benchmarks/omr-detector-scale`
        measured. Run this test with `_cell_span_px` replaced by
        `staff.span_px` and it fails on the ratio.
        """
        cells = _cells(monkeypatch, "1")
        five = next(c for c in cells if c.staff_index == 0)
        one = next(c for c in cells if c.staff_index == 1)
        assert one.upscale_factor == pytest.approx(five.upscale_factor, rel=0.02)
        # ...and that scale is the canonical one, not 1.0.
        assert one.upscale_factor > 1.5

    def test_the_cell_still_carries_exactly_one_staff_row(self, monkeypatch):
        """The abstention channel. Every geometric reader that needs five lines
        keys on this count, so a one-line cell must not be dressed up as five:
        the flag admits the INK, it does not invent a staff."""
        one = next(c for c in _cells(monkeypatch, "1") if c.staff_index == 1)
        assert len(one.staff_line_ys_canonical) == 1

    def test_no_pitch_is_resolved_on_it(self, monkeypatch):
        """A wrong staff is worse than a missing one. `pitch_for_notehead`
        already abstains below two rows; this asserts the flag does not route
        around that."""
        from tools.omr.pitch_resolver import pitch_for_notehead
        from tools.omr.template_matcher import SymbolDetection

        one = next(c for c in _cells(monkeypatch, "1") if c.staff_index == 1)
        det = SymbolDetection(
            cell=one, smufl_name="noteheadBlack", category="notehead",
            x_canonical=10, y_canonical=10,
            width_canonical=20, height_canonical=20, confidence=0.9,
        )
        assert pitch_for_notehead(det, "treble") is None

    def test_the_canonical_spacing_is_stated_for_consumers_that_need_it(
            self, monkeypatch):
        """A one-line cell has no gap to average, so `line_detection` and
        `staff_line_removal` would fall back to constants written for another
        frame. The unit is known at cut time and is written down."""
        cells = _cells(monkeypatch, "1")
        one = next(c for c in cells if c.staff_index == 1)
        five = next(c for c in cells if c.staff_index == 0)
        stated = getattr(one, "staff_line_spacing_canonical", None)
        assert stated is not None
        assert stated == pytest.approx(CANONICAL_STAFF_SPAN_PX / 4.0, rel=0.05)
        # Absent on a five-line cell, which is what keeps those consumers
        # byte-identical when the flag is off AND when it is on.
        assert getattr(five, "staff_line_spacing_canonical", None) is None


class TestTheFiveLineStavesDoNotMOVE:
    """The assertion that matters. A structural flag that shifts its
    neighbours' cells is not additive, and a percussion rule is set to the page
    margins — so it would shift them through `_measure_x_boundaries`."""

    def test_five_line_cells_are_identical_with_the_flag_on(self, monkeypatch):
        off = {(c.staff_index, c.measure_index): c
               for c in _cells(monkeypatch, None)}
        on = {(c.staff_index, c.measure_index): c
              for c in _cells(monkeypatch, "1")}
        assert set(off) <= set(on)
        for key, a in off.items():
            b = on[key]
            assert a.bbox_page_px == b.bbox_page_px, key
            assert a.staff_line_ys_canonical == b.staff_line_ys_canonical, key
            assert a.upscale_factor == b.upscale_factor, key
            assert np.array_equal(a.image, b.image), key

    def test_the_percussion_rule_does_not_vote_on_the_system_edges(self):
        """`_measure_x_boundaries` takes a MEDIAN over `x_start` and a MAX over
        `x_end`. The rule's 20..960 against the staves' 60..860 would move both
        ends, and every measure boundary with them."""
        pws = _page()
        five = [s for s in pws.staves if len(s.line_ys) >= 5]
        assert (_measure_x_boundaries(pws.barlines, five)
                != _measure_x_boundaries(pws.barlines, pws.staves))


class TestCellSpanPx:
    def test_a_five_line_staff_answers_with_its_own_span(self):
        s = Staff(page_index=0, staff_index=0, line_ys=list(FIVE_A),
                  x_start=0, x_end=1)
        assert _cell_span_px(s) == s.span_px == 80

    def test_a_one_line_staff_answers_with_four_page_spaces(self):
        s = Staff(page_index=0, staff_index=0, line_ys=[240],
                  x_start=0, x_end=1, nominal_line_spacing_px=SPACING)
        assert s.span_px == 0
        assert _cell_span_px(s) == 80

    def test_a_one_line_staff_with_no_spacing_abstains(self):
        """Nothing to reconstruct the scale from — and the caller reads 0 as
        'do not admit', rather than admitting an unscaled cell."""
        s = Staff(page_index=0, staff_index=0, line_ys=[240],
                  x_start=0, x_end=1, nominal_line_spacing_px=None)
        assert _cell_span_px(s) == 0

    def test_a_spacingless_rule_is_not_admitted(self, monkeypatch):
        monkeypatch.setenv(me.ENV_ONE_LINE_STAVES, "1")
        pws = _page()
        pws.staves[1].nominal_line_spacing_px = None
        cells = extract_measures(pws, max_cell_width=4096)
        assert {c.staff_index for c in cells} == {0, 2}


class TestTheExportSaysWhatTheStaffIS:
    """A staff we emit with the wrong clef is worse than a staff we drop.

    The positional clef default is `treble`, so an admitted percussion rule
    would export as a treble staff of rests — a bass drum notated as a pitched
    instrument. Both facts the export needs are GEOMETRY (one printed rule IS a
    one-line percussion staff), so they are stated, not read.
    """

    def test_a_percussion_clef_exports_as_percussion_not_treble(self):
        from tools.omr.export import _mxl_attributes_block
        got = _mxl_attributes_block("percussion", None, None, 8, "", True,
                                    staff_lines=1)
        assert "<sign>percussion</sign>" in got
        assert "<staff-lines>1</staff-lines>" in got
        # A percussion clef names no line, so it must not claim one.
        assert "<line>" not in got

    def test_without_the_branch_it_would_have_said_treble(self):
        """`_MXL_CLEF_SIGN` is built from the PITCHED clef families only, so an
        unknown name falls through to ("G", 2). This pins the fall-through that
        the percussion branch exists to avoid."""
        from tools.omr.export import _MXL_CLEF_SIGN
        assert "percussion" not in _MXL_CLEF_SIGN
        assert _MXL_CLEF_SIGN.get("percussion", ("G", 2)) == ("G", 2)

    def test_a_pitched_clef_is_untouched_and_emits_no_staff_details(self):
        from tools.omr.export import _mxl_attributes_block
        got = _mxl_attributes_block("bass", None, None, 8, "", True)
        assert "<sign>F</sign>" in got and "<line>4</line>" in got
        assert "staff-details" not in got

    def test_lilypond_already_spells_percussion_correctly(self):
        """No LilyPond change was needed and this says why: `\\clef percussion`
        is the literal LilyPond clef name, so `_clef_to_lily` passes it
        through. Pinned so a future suffix rule cannot quietly mangle it."""
        from tools.omr.export import _clef_to_lily
        assert _clef_to_lily("percussion") == "percussion"
