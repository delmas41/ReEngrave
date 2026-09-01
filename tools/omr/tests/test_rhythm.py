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
        assert result == {"numerator": 4, "denominator": 4, "raw": "C"}

    def test_cut_common_shortcut(self):
        d = FakeDet(category="time_sig_digit", smufl_name="timeSigCutCommon", x_canonical=50)
        result = parse_time_signature([d])
        assert result == {"numerator": 2, "denominator": 2, "raw": "C|"}

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
            "numerator": 4, "denominator": 4, "raw": "C"
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
        assert parse_time_signature([d]) == {"numerator": 4, "denominator": 4, "raw": "C"}


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
