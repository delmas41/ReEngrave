"""Unit tests for tools/omr/rhythm.py — Phase 4c/g/h rhythm-resolution logic.

These tests cover the pure-function helpers without needing real PDFs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from tools.omr.rhythm import (
    _BEAM_COUNT_DURATIONS,
    _beamed_groups,
    _beams_attached_to_stem,
    _distance_to_band,
    _tuplet_digit,
    _tuplet_groups,
    _FLAG_DURATIONS,
    _NOTEHEAD_INTRINSIC,
    _REST_DURATIONS,
    _deduplicate_beams,
    _dot_multiplier,
    _flag_duration,
    _intrinsic_notehead_duration,
    _name_for_dots,
    _overlaps_any_in_x,
    _spans_the_whole_cell,
    _pair_dots_to_targets,
    _normalize_class,
    _rest_duration,
    parse_time_signature,
)
from tools.omr.transcribe import _parse_inline_accidental


# ─── Stub classes that mimic SymbolDetection's attribute surface ────────────


@dataclass
class FakeDet:
    """A minimal stand-in for SymbolDetection — quack-compatible with what
    rhythm.py reads (smufl_name, category, x_canonical, y_canonical,
    width_canonical, height_canonical, confidence)."""
    smufl_name: str = ""
    category: str = ""
    x_canonical: int = 0
    y_canonical: int = 0
    width_canonical: int = 30
    height_canonical: int = 20
    confidence: float = 0.9


# ─── _normalize_class ───────────────────────────────────────────────────────


class TestNormalizeClass:
    def test_lowercases(self):
        assert _normalize_class("NoteheadBlackInSpace") == "noteheadblackinspace"

    def test_strips_nonalnum(self):
        assert _normalize_class("clef-8va") == "clef8va"

    def test_empty_string(self):
        assert _normalize_class("") == ""

    def test_none_safe(self):
        # The function explicitly checks for falsy input
        assert _normalize_class(None) == ""


# ─── _intrinsic_notehead_duration ────────────────────────────────────────────


class TestIntrinsicNoteheadDuration:
    @pytest.mark.parametrize("name, expected_beats, expected_type", [
        ("noteheadBlackInSpace", 1.0, "quarter"),
        ("noteheadBlackOnLine", 1.0, "quarter"),
        ("noteheadBlackInSpaceSmall", 1.0, "quarter"),
        ("noteheadHalfInSpace", 2.0, "half"),
        ("noteheadHalfOnLine", 2.0, "half"),
        ("noteheadWholeInSpace", 4.0, "whole"),
        ("noteheadWholeOnLine", 4.0, "whole"),
        ("noteheadDoubleWholeInSpace", 8.0, "double_whole"),
    ])
    def test_known_classes(self, name, expected_beats, expected_type):
        result = _intrinsic_notehead_duration(name)
        assert result == (expected_beats, expected_type)

    def test_unknown_class_returns_none(self):
        assert _intrinsic_notehead_duration("noteheadDiamond") is None

    def test_non_notehead_returns_none(self):
        assert _intrinsic_notehead_duration("clefG") is None


# ─── _rest_duration ─────────────────────────────────────────────────────────


class TestRestDuration:
    @pytest.mark.parametrize("name, beats", [
        ("restWhole", 4.0),
        ("restHalf", 2.0),
        ("restQuarter", 1.0),
        ("rest8th", 0.5),
        ("rest16th", 0.25),
        ("rest32nd", 0.125),
        ("rest64th", 0.0625),
    ])
    def test_known_rests(self, name, beats):
        result = _rest_duration(name)
        assert result is not None
        assert result[0] == beats

    def test_unknown_rest_returns_none(self):
        assert _rest_duration("restMaxima") is None


# ─── _flag_duration ─────────────────────────────────────────────────────────


class TestFlagDuration:
    @pytest.mark.parametrize("name, beats", [
        ("flag8thUp", 0.5),
        ("flag8thDown", 0.5),
        ("flag16thUp", 0.25),
        ("flag16thDown", 0.25),
        ("flag32ndUp", 0.125),
        ("flag64thDown", 0.0625),
    ])
    def test_known_flags(self, name, beats):
        result = _flag_duration(name)
        assert result is not None
        assert result[0] == beats

    def test_unknown_flag(self):
        assert _flag_duration("flagSomethingElse") is None


# ─── _dot_multiplier + _name_for_dots ───────────────────────────────────────


class TestDotMultiplier:
    @pytest.mark.parametrize("n_dots, expected", [
        (0, 1.0),
        (1, 1.5),
        (2, 1.75),
        (3, 1.875),
    ])
    def test_multiplier(self, n_dots, expected):
        assert _dot_multiplier(n_dots) == pytest.approx(expected)

    def test_zero_dots_prefix(self):
        assert _name_for_dots(0) == ""

    def test_one_dot_prefix(self):
        assert _name_for_dots(1) == "dotted_"

    def test_multiple_dots_prefix(self):
        assert _name_for_dots(2) == "2dotted_"


# ─── _pair_dots_to_targets ──────────────────────────────────────────────────
#
# A dot does not sit at its note's height. A note in a space takes its dot in
# the same space; a note ON A LINE takes it in the space ABOVE — half a staff
# space up, by engraving convention. The tolerance used to be a multiple of the
# DOT's own box height, which is a length with no musical meaning, and the
# on-a-line case landed within a few pixels of it and went either way.


SPACE = 100  # canonical staff-line spacing on the benchmark pages


#: Both helpers place a box by its CENTRE, because centre-to-centre is what the
#: rule measures and what "half a space above" means on the page.
def _dot(x, y_centre, w=44, h=42):
    return FakeDet(smufl_name="augmentationDot", category="structural",
                   x_canonical=x, y_canonical=y_centre - h // 2,
                   width_canonical=w, height_canonical=h)


def _note(x, y_centre, w=90, h=100):
    return FakeDet(smufl_name="noteheadBlackOnLine", category="notehead",
                   x_canonical=x, y_canonical=y_centre - h // 2,
                   width_canonical=w, height_canonical=h)


class TestPairDotsToTargets:
    def test_note_in_a_space_takes_a_dot_at_its_own_height(self):
        note = _note(0, 250)
        dot = _dot(140, 250)
        assert _pair_dots_to_targets([dot], [note], SPACE) == {id(note): 1}

    def test_note_on_a_line_takes_a_dot_half_a_space_above(self):
        # The measured case: 54 of the benchmark's 110 dots sit here, at
        # 0.28-0.57 spaces up, and the old rule kept only some of them.
        note = _note(0, 250)
        dot = _dot(140, 250 - SPACE // 2)
        assert _pair_dots_to_targets([dot], [note], SPACE) == {id(note): 1}

    def test_a_dot_a_full_space_away_is_not_this_note_s(self):
        # One space up is where the NEXT staff position's notehead sits, so a
        # dot that far off belongs to something else.
        note = _note(0, 250)
        dot = _dot(140, 250 - SPACE)
        assert _pair_dots_to_targets([dot], [note], SPACE) == {}

    def test_a_dot_below_a_note_is_not_that_note_s(self):
        # A dot goes in the space ABOVE its note, or level with it. Never under.
        note = _note(0, 250)
        dot = _dot(140, 250 + SPACE // 2)
        assert _pair_dots_to_targets([dot], [note], SPACE) == {}

    def test_a_double_stop_gives_each_note_its_own_dot(self):
        # Brahms's Viola. Two noteheads a space apart, each with its own dot in
        # the space above it — so the LOWER dot is equidistant from both notes,
        # and a symmetric window gives it to whichever was listed first. Then
        # the upper note is double-dotted and the lower one has no dot at all.
        upper, lower = _note(0, 700), _note(0, 800)
        dots = [_dot(140, 650), _dot(140, 750)]
        assert _pair_dots_to_targets(dots, [upper, lower], SPACE) == {
            id(upper): 1, id(lower): 1,
        }

    def test_tolerance_scales_with_the_staff(self):
        # A cell scaled by width rather than by staff span has a smaller staff,
        # and the same half-space offset is fewer pixels. Same music, same
        # answer — which the old rule, measuring against the dot's own box,
        # could not give.
        small = 40
        note = _note(0, 100, w=36, h=40)
        dot = _dot(56, 100 - small // 2, w=18, h=17)
        assert _pair_dots_to_targets([dot], [note], small) == {id(note): 1}

    def test_target_must_be_to_the_left(self):
        note = _note(200, 250)
        dot = _dot(40, 250)
        assert _pair_dots_to_targets([dot], [note], SPACE) == {}

    def test_nearer_note_wins(self):
        far, near = _note(0, 250), _note(300, 250)
        dot = _dot(420, 250)
        assert _pair_dots_to_targets([dot], [far, near], SPACE) == {id(near): 1}

    def test_two_dots_on_one_note_count_twice(self):
        note = _note(0, 250)
        dots = [_dot(140, 250), _dot(200, 250)]
        assert _pair_dots_to_targets(dots, [note], SPACE) == {id(note): 2}

    def test_ink_at_a_cell_edge_with_no_note_near_it_pairs_with_nothing(self):
        # The two outliers in the benchmark: a dot-shaped fragment at the top
        # of a cell, five spaces from any notehead.
        note = _note(0, 600)
        dot = _dot(140, 8, h=17)
        assert _pair_dots_to_targets([dot], [note], SPACE) == {}


# ─── _overlaps_any_in_x — which beam list speaks for a column ───────────────
#
# A YOLO beam box bounds the whole STACK of strokes, not one stroke, so its
# centre lands in the gap between two levels and welds them into one. Where the
# classical-CV detector has measured a column, its answer stands alone; where it
# found nothing, YOLO's coverage is still better than none.


def _beam(x, w, y=0, h=60):
    return FakeDet(smufl_name="beam", category="structural",
                   x_canonical=x, y_canonical=y,
                   width_canonical=w, height_canonical=h)


class TestOverlapsAnyInX:
    def test_overlapping_box_is_covered(self):
        assert _overlaps_any_in_x(_beam(200, 400), [_beam(0, 300)])

    def test_disjoint_box_is_not(self):
        assert not _overlaps_any_in_x(_beam(400, 100), [_beam(0, 300)])

    def test_touching_edges_do_not_count_as_overlap(self):
        # Abutting spans share no column; the second one is still the only
        # reading of its own.
        assert not _overlaps_any_in_x(_beam(300, 100), [_beam(0, 300)])

    def test_empty_others_covers_nothing(self):
        assert not _overlaps_any_in_x(_beam(0, 100), [])

    def test_any_one_overlap_is_enough(self):
        others = [_beam(0, 50), _beam(500, 50)]
        assert _overlaps_any_in_x(_beam(480, 100), others)


# ─── _beams_attached_to_stem — reach measured to the BAND, not its centre ───
#
# A beam detection bounds one stroke over its whole run, so a SLOPED stroke's
# band spans the stroke's entire vertical excursion and its CENTRE is a y the
# stroke occupies only in the middle of the group. Measuring the stem's reach
# to that centre overstates the distance for the OUTERMOST stem of the group
# by about half the band height — and the window is only 4 x the clustering
# tolerance, so the outermost note of a sixteenth group lost its second beam
# and came out twice as long.
#
# The geometry below is measured, not invented: Mozart 41, Oboe I (staff 1),
# measure 0, canonical coordinates at staff spacing 65.2 px. See
# benchmarks/omr-corpus-widening-2026-09/MOZART41_BEAMS.md.

M41_SPACING = 65.2
M41_TOL = M41_SPACING * 0.35          # 22.8 px; end_window is 4x = 91.3 px

#: The two CV beam bands over the rising triplet of sixteenths.
M41_BANDS = [
    FakeDet(smufl_name="beam", category="structural",
            x_canonical=1062, y_canonical=163,
            width_canonical=267, height_canonical=44),
    FakeDet(smufl_name="beam", category="structural",
            x_canonical=1060, y_canonical=217,
            width_canonical=269, height_canonical=47),
]


def _m41_stem(x, y, h):
    return FakeDet(smufl_name="stem", category="stem", x_canonical=x,
                   y_canonical=y, width_canonical=8, height_canonical=h)


class TestBeamsAttachedToStem:
    #: All three stems of the group carry two strokes. The third is the one
    #: that used to read 1 — its top is 146, so its distance to the second
    #: band's CENTRE (240) is 94 px against a 91.3 px window, while its
    #: distance to the BAND (217-264) is 71.
    @pytest.mark.parametrize("x,y,h", [(1061, 192, 275),
                                       (1189, 170, 265),
                                       (1318, 146, 256)])
    def test_every_stem_of_a_sloped_group_reads_both_strokes(self, x, y, h):
        stem = _m41_stem(x, y, h)
        assert _beams_attached_to_stem(stem, M41_BANDS, M41_TOL) == 2

    def test_the_outermost_stem_is_the_one_the_centre_rule_lost(self):
        # Pins the mechanism rather than just the outcome: the old rule is
        # reproduced here, and it must disagree on exactly this stem.
        stem = _m41_stem(1318, 146, 256)
        centres = [b.y_canonical + b.height_canonical // 2 for b in M41_BANDS]
        d_centre = [abs(c - stem.y_canonical) for c in centres]
        end_window = M41_TOL * 4.0
        assert d_centre[0] <= end_window < d_centre[1]
        assert _beams_attached_to_stem(stem, M41_BANDS, M41_TOL) == 2

    def test_a_stem_end_inside_a_band_is_at_zero_distance(self):
        assert _distance_to_band(180.0, 163.0, 207.0) == 0.0

    def test_distance_to_a_band_is_to_its_nearer_edge(self):
        assert _distance_to_band(146.0, 217.0, 264.0) == 71.0
        assert _distance_to_band(300.0, 217.0, 264.0) == 36.0

    def test_a_beam_that_does_not_overlap_the_stem_in_x_is_not_counted(self):
        # The x filter is unchanged; widening the y reach must not reach
        # sideways into the next group.
        far = FakeDet(smufl_name="beam", category="structural",
                      x_canonical=1750, y_canonical=163,
                      width_canonical=267, height_canonical=44)
        stem = _m41_stem(1061, 192, 275)
        assert _beams_attached_to_stem(stem, [far], M41_TOL) == 0

    def test_a_beam_far_beyond_the_window_is_still_rejected(self):
        # The band rule is a bounded widening, not an open one: a band a
        # staff's height away from either stem end stays out.
        stem = _m41_stem(1061, 192, 275)
        remote = FakeDet(smufl_name="beam", category="structural",
                         x_canonical=1062, y_canonical=900,
                         width_canonical=267, height_canonical=44)
        assert _beams_attached_to_stem(stem, [remote], M41_TOL) == 0

    def test_a_level_beam_is_unaffected_by_the_change(self):
        # A single thin band: centre and edges are within a bar's thickness of
        # each other, so both rules agree. This is why 8 of the 12 benchmark
        # works see no stem change at all.
        flat = FakeDet(smufl_name="beam", category="structural",
                       x_canonical=1062, y_canonical=180,
                       width_canonical=267, height_canonical=8)
        stem = _m41_stem(1061, 192, 275)
        assert _beams_attached_to_stem(stem, [flat], M41_TOL) == 1


# ─── _parse_inline_accidental (in transcribe.py, but we test alongside) ─────


class TestParseInlineAccidental:
    @pytest.mark.parametrize("name, expected", [
        ("accidentalSharp", "#"),
        ("accidentalFlat", "b"),
        ("accidentalNatural", "natural"),
        ("accidentalDoubleSharp", "##"),
        ("accidentalDoubleFlat", "bb"),
    ])
    def test_known_inline_accidentals(self, name, expected):
        assert _parse_inline_accidental(name) == expected

    def test_keysharp_not_inline(self):
        # keySharp is the key-signature variant, not an inline accidental.
        assert _parse_inline_accidental("keySharp") is None

    def test_unknown(self):
        assert _parse_inline_accidental("clefG") is None
        assert _parse_inline_accidental("") is None


# ─── parse_time_signature ───────────────────────────────────────────────────


class TestParseTimeSignature:
    def test_common_time_shortcut(self):
        # x_canonical past the left-edge margin — a real time sig sits after
        # the clef, not jammed against x==0 (which is a misread; see below).
        d = FakeDet(category="time_sig_digit", smufl_name="timeSigCommon", x_canonical=50)
        result = parse_time_signature([d])
        assert result == {"numerator": 4, "denominator": 4, "raw": "C",
                          "symbol": "common"}

    def test_cut_common_shortcut(self):
        d = FakeDet(category="time_sig_digit", smufl_name="timeSigCutCommon", x_canonical=50)
        result = parse_time_signature([d])
        assert result == {"numerator": 2, "denominator": 2, "raw": "C|",
                          "symbol": "cut"}

    def test_no_time_sig_returns_none(self):
        assert parse_time_signature([]) is None

    def test_stacked_4_over_4(self):
        # Two digits at the same x, "4" on top "4" below.
        top = FakeDet(
            category="time_sig_digit", smufl_name="timeSig4",
            x_canonical=100, y_canonical=10, width_canonical=20, height_canonical=20,
        )
        bot = FakeDet(
            category="time_sig_digit", smufl_name="timeSig4",
            x_canonical=100, y_canonical=40, width_canonical=20, height_canonical=20,
        )
        result = parse_time_signature([top, bot])
        assert result is not None
        assert result["numerator"] == 4
        assert result["denominator"] == 4
        assert result["raw"] == "4/4"

    def test_stacked_3_over_8(self):
        top = FakeDet(
            category="time_sig_digit", smufl_name="timeSig3",
            x_canonical=100, y_canonical=10, width_canonical=20, height_canonical=20,
        )
        bot = FakeDet(
            category="time_sig_digit", smufl_name="timeSig8",
            x_canonical=100, y_canonical=40, width_canonical=20, height_canonical=20,
        )
        result = parse_time_signature([top, bot])
        assert result is not None
        assert result["numerator"] == 3
        assert result["denominator"] == 8

    def test_single_digit_assumes_denominator_4(self):
        d = FakeDet(
            category="time_sig_digit", smufl_name="timeSig3",
            x_canonical=100, y_canonical=10, width_canonical=20, height_canonical=20,
        )
        result = parse_time_signature([d])
        # One digit → assume 3/4
        assert result == {"numerator": 3, "denominator": 4, "raw": "3/4"}

    def test_ignores_non_time_sig_dets(self):
        nh = FakeDet(category="notehead", smufl_name="noteheadBlackOnLine")
        ts = FakeDet(category="time_sig_digit", smufl_name="timeSigCommon", x_canonical=50)
        assert parse_time_signature([nh, ts]) == {
            "numerator": 4, "denominator": 4, "raw": "C", "symbol": "common"
        }

    def test_rejects_left_edge_misread(self):
        # A time-sig glyph jammed at the cell's left edge (x==0) is the
        # orchestral instrument-number / margin misread — must be ignored.
        edge = FakeDet(category="time_sig_digit", smufl_name="timeSigCommon", x_canonical=0)
        assert parse_time_signature([edge]) is None
        # ... and stacked digit misreads at the edge (the "666/666" pattern)
        d1 = FakeDet(category="time_sig_digit", smufl_name="timeSig6", x_canonical=0, y_canonical=10)
        d2 = FakeDet(category="time_sig_digit", smufl_name="timeSig6", x_canonical=0, y_canonical=40)
        assert parse_time_signature([d1, d2]) is None

    def test_keeps_glyph_just_past_margin(self):
        # A real time sig a bit past the margin (x >= threshold) is kept.
        d = FakeDet(category="time_sig_digit", smufl_name="timeSigCommon", x_canonical=16)
        assert parse_time_signature([d]) == {"numerator": 4, "denominator": 4,
                                             "raw": "C", "symbol": "common"}


# ─── _deduplicate_beams ────────────────────────────────────────────────────


class TestDeduplicateBeams:
    def test_duplicates_within_tolerance_removed(self):
        # Two beams at near-identical positions; lower-conf one should drop.
        b1 = FakeDet(
            category="structural", smufl_name="beam",
            x_canonical=100, y_canonical=50, width_canonical=200, height_canonical=10,
            confidence=0.9,
        )
        b2 = FakeDet(
            category="structural", smufl_name="beam",
            x_canonical=102, y_canonical=51, width_canonical=200, height_canonical=10,
            confidence=0.8,
        )
        kept = _deduplicate_beams([b1, b2], line_spacing=50)
        assert len(kept) == 1
        assert kept[0].confidence == 0.9  # the higher-conf one wins

    def test_separated_beams_both_kept(self):
        # Two distinctly-positioned beams (different y) should both survive.
        b1 = FakeDet(
            category="structural", smufl_name="beam",
            x_canonical=100, y_canonical=50, width_canonical=200, height_canonical=10,
            confidence=0.9,
        )
        b2 = FakeDet(
            category="structural", smufl_name="beam",
            x_canonical=100, y_canonical=80, width_canonical=200, height_canonical=10,
            confidence=0.9,
        )
        kept = _deduplicate_beams([b1, b2], line_spacing=50)
        # y-tolerance is line_spacing × 0.18 = 9; |80-50|=30 > 9 → both kept.
        assert len(kept) == 2

    def test_no_overlap_keeps_all(self):
        # x-ranges don't overlap → no dedup, all kept.
        b1 = FakeDet(
            category="structural", smufl_name="beam",
            x_canonical=100, y_canonical=50, width_canonical=50, height_canonical=10,
        )
        b2 = FakeDet(
            category="structural", smufl_name="beam",
            x_canonical=300, y_canonical=50, width_canonical=50, height_canonical=10,
        )
        kept = _deduplicate_beams([b1, b2], line_spacing=50)
        assert len(kept) == 2

    def test_empty_input_returns_empty(self):
        assert _deduplicate_beams([], line_spacing=50) == []


# ── beams stack at one end of the stem ──────────────────────────────────────
# The stem-anchored counter enforced this; the no-stem fallback did not, and
# swept a window 5.5 staff-spaces tall into a single count. On an engraved
# Brahms 1 page that produced beam levels of 5, 6, 7 and 8 — an eight-beam note
# is a 1024th — which the cap then turned into sixty-fourths.

class _FakeBeam:
    def __init__(self, x, y, w=200, h=8):
        self.x_canonical, self.y_canonical = x, y
        self.width_canonical, self.height_canonical = w, h
        self.confidence = 0.9
        self.category = "structural"
        self.smufl_name = "beam"


class _FakeNotehead:
    def __init__(self, x, y, w=30, h=24):
        self.x_canonical, self.y_canonical = x, y
        self.width_canonical, self.height_canonical = w, h


def test_fallback_counts_one_beam_group_not_a_whole_window():
    from tools.omr.rhythm import _beam_levels_for_notehead
    spacing = 100.0
    tol = spacing * 0.22
    nh = _FakeNotehead(100, 500)
    # A stem-up note: its two beams stack at the top of the stem. The strays
    # sit BETWEEN the notehead and that group — beams of other voices printed
    # nearby, which is what the tall window used to sweep in.
    beams = [
        _FakeBeam(50, 200), _FakeBeam(50, 225),      # the group: 2 levels
        _FakeBeam(50, 320), _FakeBeam(50, 400),      # other groups, in-window
    ]
    levels = _beam_levels_for_notehead(
        nh, beams, max_stem_distance=spacing * 5.5,
        beam_y_cluster_tol=tol, x_tolerance=spacing * 0.6,
    )
    assert levels == 2, f"counted {levels}; only the end group should count"


def test_fallback_never_reports_an_impossible_depth():
    from tools.omr.rhythm import _beam_levels_for_notehead
    spacing = 100.0
    nh = _FakeNotehead(100, 500)
    # Eight beams spread evenly through the window — the shape that produced
    # levels of 8 before. Whatever is counted must be a real note value.
    beams = [_FakeBeam(50, 150 + 60 * i) for i in range(8)]
    levels = _beam_levels_for_notehead(
        nh, beams, max_stem_distance=spacing * 5.5,
        beam_y_cluster_tol=spacing * 0.22, x_tolerance=spacing * 0.6,
    )
    assert levels <= 4, f"{levels} beams is not a note value"


# ─── Tuplets ────────────────────────────────────────────────────────────────


class TestTupletDigit:
    @pytest.mark.parametrize("name, expected", [
        ("tuplet3", 3),
        ("tuplet6", 6),
        ("tupletBracket", None),
        ("noteheadBlackInSpace", None),
        ("", None),
    ])
    def test_digit(self, name, expected):
        assert _tuplet_digit(name) == expected


class TestBeamedGroups:
    """The beam box gives a group its extent, and it has to be PADDED.

    A beam box bounds the beam INK, which starts at the first stem. With stems
    up the first notehead's centre sits a notehead's width to the left of it,
    so an unpadded test drops the first note of every stem-up group — measured
    on Mahler's first triplet: box x 1659-1957 against centres 1621/1770/1918.
    """

    #: The real geometry, from Mahler 5 measure 1: noteheads ~79px wide with
    #: centres 1621/1770/1918, beam ink starting at 1659. The first notehead's
    #: RIGHT edge is where its stem is, and that is where the beam begins.
    WIDTH = 79

    @classmethod
    def _heads(cls, *xs):
        return [FakeDet(smufl_name="noteheadBlackInSpace", category="notehead",
                        x_canonical=x - cls.WIDTH // 2,
                        width_canonical=cls.WIDTH) for x in xs]

    def test_first_note_left_of_the_beam_ink_is_still_in_the_group(self):
        heads = self._heads(1621, 1770, 1918)
        beam = FakeDet(smufl_name="beam", category="structural",
                       x_canonical=1659, width_canonical=298)
        groups = _beamed_groups(heads, [beam], pad=self.WIDTH)
        assert len(groups) == 1
        assert len(groups[0]) == 3

    def test_unpadded_would_lose_it(self):
        heads = self._heads(1621, 1770, 1918)
        beam = FakeDet(smufl_name="beam", category="structural",
                       x_canonical=1659, width_canonical=298)
        assert len(_beamed_groups(heads, [beam], pad=0)[0]) == 2

    def test_two_beat_groups_stay_two_groups(self):
        """Adjacency would merge these; the boxes are why it does not."""
        heads = self._heads(100, 200, 300, 900, 1000, 1100)
        beams = [
            FakeDet(smufl_name="beam", category="structural",
                    x_canonical=140, width_canonical=200),
            FakeDet(smufl_name="beam", category="structural",
                    x_canonical=940, width_canonical=200),
        ]
        groups = _beamed_groups(heads, beams, pad=self.WIDTH)
        assert [len(g) for g in groups] == [3, 3]

    def test_a_lone_beamed_note_is_not_a_group(self):
        heads = self._heads(100)
        beam = FakeDet(smufl_name="beam", category="structural",
                       x_canonical=140, width_canonical=20)
        assert _beamed_groups(heads, [beam], pad=self.WIDTH) == []


class TestTupletGroups:
    """Which beamed groups a tuplet marker actually claims."""

    @staticmethod
    def _setup(marker_dets, xs=(100, 160, 220), levels=1):
        heads = [FakeDet(smufl_name="noteheadBlackInSpace", category="notehead",
                         x_canonical=x - 15, width_canonical=30) for x in xs]
        beams = [FakeDet(smufl_name="beam", category="structural",
                         x_canonical=xs[0] + 5,
                         width_canonical=xs[-1] - xs[0] + 10)]
        out = {id(h): {"duration_beats": 0.5, "duration_type": "eighth",
                       "dots": 0, "beam_levels": levels} for h in heads}
        dets = heads + beams + list(marker_dets)
        return heads, out, dets, beams

    @staticmethod
    def _digit(x, n=3):
        return FakeDet(smufl_name=f"tuplet{n}", category="structural",
                       x_canonical=x, width_canonical=20)

    @staticmethod
    def _bracket(x, w):
        return FakeDet(smufl_name="tupletBracket", category="structural",
                       x_canonical=x, width_canonical=w)

    def test_digit_over_the_group_claims_it(self):
        heads, out, dets, beams = self._setup([self._digit(150)])
        claimed = _tuplet_groups(heads, out, dets, beams, nh_width=30)
        assert len(claimed) == 1
        members, actual, normal = claimed[0]
        assert (actual, normal) == (3, 2)
        assert len(members) == 3

    def test_no_marker_means_no_tuplet(self):
        heads, out, dets, beams = self._setup([])
        assert _tuplet_groups(heads, out, dets, beams, nh_width=30) == []

    def test_digit_that_disagrees_with_the_group_size_abstains(self):
        """A '3' over four beamed notes is a triplet plus something else, and
        which note is outside it is not knowable from the box."""
        heads, out, dets, beams = self._setup(
            [self._digit(150)], xs=(100, 160, 220, 280))
        assert _tuplet_groups(heads, out, dets, beams, nh_width=30) == []

    def test_unmeasured_digits_abstain(self):
        heads, out, dets, beams = self._setup(
            [self._digit(150, n=5)], xs=(100, 140, 180, 220, 260))
        assert _tuplet_groups(heads, out, dets, beams, nh_width=30) == []

    def test_wide_bracket_enclosing_one_group_is_read_as_a_triplet(self):
        """Detected brackets are far wider than the notes they cover — one
        measured at 1846px over a 478px group — so the test is CONTAINMENT of
        the group by the bracket, not the bracket's centre."""
        heads, out, dets, beams = self._setup([self._bracket(0, 900)])
        claimed = _tuplet_groups(heads, out, dets, beams, nh_width=30)
        assert len(claimed) == 1
        assert claimed[0][1:] == (3, 2)

    def test_bracket_covering_two_groups_cannot_say_which(self):
        heads = [FakeDet(smufl_name="noteheadBlackInSpace", category="notehead",
                         x_canonical=x - 15, width_canonical=30)
                 for x in (100, 160, 220, 600, 660, 720)]
        beams = [FakeDet(smufl_name="beam", category="structural",
                         x_canonical=105, width_canonical=120),
                 FakeDet(smufl_name="beam", category="structural",
                         x_canonical=605, width_canonical=120)]
        out = {id(h): {"duration_beats": 0.5, "duration_type": "eighth",
                       "dots": 0, "beam_levels": 1} for h in heads}
        dets = heads + beams + [self._bracket(0, 900)]
        assert _tuplet_groups(heads, out, dets, beams, nh_width=30) == []

    def test_unbeamed_notes_are_never_claimed(self):
        heads, out, dets, beams = self._setup([self._digit(150)], levels=0)
        for rec in out.values():
            rec["beam_levels"] = 0
        assert _tuplet_groups(heads, out, dets, beams, nh_width=30) == []

    # ── the same glyph under DSv2's other class name ───────────────────────
    #
    # A `3` over a beamed group is `tuplet3` and a `3` beside a notehead is
    # `fingering3`; the distinction is POSITIONAL and the detector reproduces
    # it badly on orchestral pages. Measured over the twelve engraved works of
    # `benchmarks/omr-corpus-widening-2026-09`: 33 `fingering3` against 16
    # `tuplet3`, and ALL 33 sit in a cell that holds a real triplet.
    # `mozart-sym41-mvt1` alone hands back 30 of them for its 40 groups.

    @staticmethod
    def _fingering(x, n=3):
        return FakeDet(smufl_name=f"fingering{n}", category="ornament",
                       x_canonical=x, width_canonical=20)

    def test_a_fingering_digit_over_a_beamed_group_is_read_as_a_tuplet(self):
        heads, out, dets, beams = self._setup([self._fingering(150)])
        claimed = _tuplet_groups(heads, out, dets, beams, nh_width=30)
        assert len(claimed) == 1
        assert claimed[0][1:] == (3, 2)

    def test_the_gate_is_unchanged_for_the_new_class(self):
        """Admitting the class must not relax the test that makes it safe: the
        group still has to hold exactly as many notes as the digit claims."""
        heads, out, dets, beams = self._setup(
            [self._fingering(150)], xs=(100, 160, 220, 280))
        assert _tuplet_groups(heads, out, dets, beams, nh_width=30) == []

    def test_a_fingering_digit_off_the_group_claims_nothing(self):
        heads, out, dets, beams = self._setup([self._fingering(900)])
        assert _tuplet_groups(heads, out, dets, beams, nh_width=30) == []

    def test_an_unreadable_digit_no_longer_vetoes_a_readable_one(self):
        """`_TUPLET_NORMAL_FOR` holds only 3, and the old loop took the FIRST
        digit inside the group — so a stray `fingering2` sitting over a real
        triplet abandoned it. Mozart 41 detects one `fingering1` and one
        `fingering2` beside its 30 `fingering3`."""
        heads, out, dets, beams = self._setup(
            [self._fingering(120, n=2), self._fingering(150, n=3)])
        claimed = _tuplet_groups(heads, out, dets, beams, nh_width=30)
        assert len(claimed) == 1
        assert claimed[0][1:] == (3, 2)

    def test_a_fingering_digit_we_cannot_read_still_abstains(self):
        heads, out, dets, beams = self._setup(
            [self._fingering(150, n=5)], xs=(100, 140, 180, 220, 260))
        assert _tuplet_groups(heads, out, dets, beams, nh_width=30) == []

    def test_two_beam_strokes_over_one_group_claim_it_once(self):
        """A sixteenth carries TWO beam strokes and the CV detector finds both.
        Each used to produce its own group over the same noteheads, so the
        ratio was applied once per stroke and a triplet sixteenth came out
        `1/4 * 2/3 * 2/3 = 1/9`. Invisible on eighth triplets, which is all the
        three original works print; `mozart-sym41-mvt1` reported ratio 2/3 on
        89 notes."""
        xs = (100, 160, 220)
        heads = [FakeDet(smufl_name="noteheadBlackInSpace", category="notehead",
                         x_canonical=x - 15, width_canonical=30) for x in xs]
        beams = [FakeDet(smufl_name="beam", category="structural",
                         x_canonical=xs[0] + 5,
                         width_canonical=xs[-1] - xs[0] + 10),
                 FakeDet(smufl_name="beam", category="structural",
                         x_canonical=xs[0] + 5,
                         width_canonical=xs[-1] - xs[0] + 10)]
        out = {id(h): {"duration_beats": 0.25, "duration_type": "16th",
                       "dots": 0, "beam_levels": 2} for h in heads}
        dets = heads + beams + [self._digit(150)]
        claimed = _tuplet_groups(heads, out, dets, beams, nh_width=30)
        assert len(claimed) == 1, "one group of notes, not one per beam stroke"


# ─── _spans_the_whole_cell — a beam group cannot reach both barlines ────────


class TestSpansTheWholeCell:
    """A beam lives inside its measure; ink that crosses the whole cell is a
    staff line or a system rule. The CV beam detector rejects that class by
    requiring two stem ENDS on a component; YOLO beams get no such test and are
    used wherever CV is silent — which is exactly where CV refused something.
    """

    class _Cell:
        def __init__(self, width):
            self.width = width

    @staticmethod
    def _beam(width):
        return FakeDet(smufl_name="beam", category="structural",
                       x_canonical=0, y_canonical=0,
                       width_canonical=width, height_canonical=30)

    def test_a_beam_over_part_of_the_bar_is_kept(self):
        assert not _spans_the_whole_cell(self._beam(500), self._Cell(2000))

    def test_a_beam_over_half_the_bar_is_kept(self):
        # The widest real one measured is 0.5 of its cell.
        assert not _spans_the_whole_cell(self._beam(1000), self._Cell(2000))

    def test_ink_across_the_whole_bar_is_not(self):
        # Brahms's Viola bar 2: 1965 px of a 1966 px cell, 0.33 spaces thick.
        assert _spans_the_whole_cell(self._beam(1965), self._Cell(1966))

    def test_the_cut_sits_in_the_measured_gap(self):
        # Nothing at all was measured between 0.5 and 0.7 of a cell.
        cell = self._Cell(1000)
        assert not _spans_the_whole_cell(self._beam(500), cell)
        assert _spans_the_whole_cell(self._beam(700), cell)

    def test_an_unknown_cell_width_keeps_everything(self):
        assert not _spans_the_whole_cell(self._beam(9999), self._Cell(0))
        assert not _spans_the_whole_cell(self._beam(9999), None)
