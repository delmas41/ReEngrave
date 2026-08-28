"""Tests for geometric clef resolution — deciding WHICH line a clef names.

The point of these tests is that alto vs tenor (vs soprano) is a question about
position, not appearance, and so has a right answer that doesn't depend on a
model's confidence. They pin that answer down.
"""

from __future__ import annotations

import pytest

from tools.omr.clef_geometry import (
    ANCHOR_FRACTION_FROM_TOP,
    CLEF_BY_FAMILY_LINE,
    CLEF_TO_FAMILY_LINE,
    ClefGeometryConfig,
    clef_family,
    clef_name_from_class,
    resolve_clef,
)
from tools.omr.pitch_resolver import _CLEF_ANCHORS


# A 5-line staff, top → bottom, 20px apart. Line 1 (bottom) = y 180,
# line 3 (middle) = 140, line 5 (top) = 100.
STAFF = [100, 120, 140, 160, 180]
SPACING = 20


def c_clef_box(line_from_bottom: int, height: int = 80) -> dict:
    """A C-clef bounding box centred on `line_from_bottom`, as the detector
    would emit it — the glyph is symmetric about the line it names."""
    line_y = STAFF[5 - line_from_bottom]
    return {"y_top": line_y - height / 2, "height": height}


# ─── the clef table itself ──────────────────────────────────────────────────


class TestClefTable:
    def test_the_five_c_clefs_are_the_five_staff_lines(self):
        assert CLEF_BY_FAMILY_LINE["C"] == {
            1: "soprano",
            2: "mezzosoprano",
            3: "alto",
            4: "tenor",
            5: "baritone",
        }

    def test_alto_and_tenor_differ_by_exactly_one_line(self):
        # The entire distinction the detector cannot see.
        assert CLEF_TO_FAMILY_LINE["tenor"][1] - CLEF_TO_FAMILY_LINE["alto"][1] == 1

    def test_every_clef_has_a_pitch_anchor(self):
        # A clef the geometry can name but the pitch resolver can't anchor
        # would silently drop every pitch on its staff.
        for name in CLEF_TO_FAMILY_LINE:
            assert name in _CLEF_ANCHORS

    def test_every_clef_has_octave_shifted_variants(self):
        for name in CLEF_TO_FAMILY_LINE:
            for suffix in ("_8va", "_8vb", "_15ma", "_15mb"):
                assert name + suffix in _CLEF_ANCHORS

    @pytest.mark.parametrize(
        "clef,expected",
        [
            # Regression: these four were the hand-written table before the
            # anchors were derived from the clef table, and must not move.
            ("treble", ("F", 5)),
            ("bass", ("A", 3)),
            ("alto", ("G", 4)),
            ("tenor", ("E", 4)),
            # Derived: the top line's pitch for each newly supported clef.
            ("soprano", ("D", 5)),
            ("mezzosoprano", ("B", 4)),
            ("baritone", ("C", 4)),
            ("varbaritone", ("C", 4)),  # same sounding clef, F-clef spelling
            ("subbass", ("F", 3)),
            ("french", ("A", 5)),
        ],
    )
    def test_anchor_pitches(self, clef, expected):
        assert _CLEF_ANCHORS[clef] == expected

    def test_c_clef_anchor_is_the_box_centre(self):
        # Not a magic constant: the C clef is symmetric about its line.
        assert ANCHOR_FRACTION_FROM_TOP["C"] == 0.5


# ─── class-name handling ────────────────────────────────────────────────────


class TestClefFamily:
    @pytest.mark.parametrize(
        "smufl,family",
        [
            # DeepScoresV2 spelling and the detector wrapper's spelling both
            # have to work — they name the same glyphs.
            ("cClefAlto", "C"),
            ("clefCAlto", "C"),
            ("cClefTenor", "C"),
            ("clefCTenor", "C"),
            ("gClef", "G"),
            ("clefG", "G"),
            ("fClef", "F"),
            ("clefF", "F"),
            ("cClefAltoChange", "C"),  # a clef change names the same clef
            ("fClefChange", "F"),
        ],
    )
    def test_families(self, smufl, family):
        assert clef_family(smufl) == family

    @pytest.mark.parametrize(
        "smufl", ["clef8", "clef15", "unpitchedPercussionClef1", "", None]
    )
    def test_non_pitched_classes_are_not_clefs(self, smufl):
        assert clef_family(smufl) is None
        assert clef_name_from_class(smufl) is None

    def test_generic_c_clef_falls_back_to_alto(self):
        assert clef_name_from_class("clefC") == "alto"


# ─── the resolution itself ──────────────────────────────────────────────────


class TestResolveClef:
    @pytest.mark.parametrize(
        "line,expected",
        [(1, "soprano"), (2, "mezzosoprano"), (3, "alto"), (4, "tenor"), (5, "baritone")],
    )
    def test_position_decides_the_c_clef(self, line, expected):
        read = resolve_clef("clefCAlto", staff_line_ys=STAFF, **c_clef_box(line))
        assert read.name == expected
        assert read.line == line
        assert read.source == "geometry"

    def test_the_class_label_does_not_decide_it(self):
        # Same box, opposite labels: geometry gives the same answer both times.
        box = c_clef_box(4)
        as_alto = resolve_clef("clefCAlto", staff_line_ys=STAFF, **box)
        as_tenor = resolve_clef("clefCTenor", staff_line_ys=STAFF, **box)
        assert as_alto.name == as_tenor.name == "tenor"

    def test_a_mislabelled_tenor_is_read_as_alto_when_it_sits_on_line_three(self):
        # The exact failure the clef fine-tune could not train away.
        read = resolve_clef("clefCTenor", staff_line_ys=STAFF, **c_clef_box(3))
        assert read.name == "alto"

    def test_falls_back_to_the_label_without_staff_geometry(self):
        read = resolve_clef("clefCTenor", staff_line_ys=None, **c_clef_box(4))
        assert read.name == "tenor"
        assert read.source == "class"
        assert read.line is None

    def test_falls_back_when_the_staff_is_not_five_lines(self):
        read = resolve_clef("clefCAlto", staff_line_ys=[100, 120, 140], **c_clef_box(3))
        assert read.source == "class"

    def test_abstains_when_the_box_lands_between_lines(self):
        # Half a space off — too ambiguous to name a line, so keep the label.
        box = c_clef_box(3)
        box["y_top"] += SPACING / 2
        read = resolve_clef("clefCAlto", staff_line_ys=STAFF, **box)
        assert read.source == "class"
        assert read.residual > ClefGeometryConfig().max_residual

    def test_small_misfits_are_still_resolved(self):
        box = c_clef_box(3)
        box["y_top"] += 4  # a fifth of a space — well within tolerance
        read = resolve_clef("clefCAlto", staff_line_ys=STAFF, **box)
        assert read.name == "alto"
        assert read.source == "geometry"

    def test_g_and_f_clefs_keep_their_label_by_default(self):
        # Geometry is not trusted for these families — treble and bass are
        # overwhelmingly likely, and a wrong guess transposes a whole staff.
        for smufl, expected in (("clefG", "treble"), ("clefF", "bass")):
            read = resolve_clef(
                smufl, y_top=100, height=80, staff_line_ys=STAFF
            )
            assert read.name == expected
            assert read.source == "class"

    def test_g_family_can_be_enabled(self):
        config = ClefGeometryConfig(families=frozenset({"C", "G"}))
        # Anchor fraction 0.625 from the top: a box whose named line is line 2.
        line_y = STAFF[5 - 2]
        height = 160
        read = resolve_clef(
            "clefG",
            y_top=line_y - ANCHOR_FRACTION_FROM_TOP["G"] * height,
            height=height,
            staff_line_ys=STAFF,
            config=config,
        )
        assert read.name == "treble"
        assert read.source == "geometry"

    def test_non_clef_detections_return_nothing(self):
        assert resolve_clef("clef8", staff_line_ys=STAFF, **c_clef_box(3)) is None
        assert resolve_clef(None, staff_line_ys=STAFF, **c_clef_box(3)) is None
