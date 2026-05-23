"""Unit tests for tools/omr/rhythm.py — Phase 4c/g/h rhythm-resolution logic.

These tests cover the pure-function helpers without needing real PDFs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from tools.omr.rhythm import (
    _BEAM_COUNT_DURATIONS,
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
        d = FakeDet(category="time_sig_digit", smufl_name="timeSigCommon")
        result = parse_time_signature([d])
        assert result == {"numerator": 4, "denominator": 4, "raw": "C"}

    def test_cut_common_shortcut(self):
        d = FakeDet(category="time_sig_digit", smufl_name="timeSigCutCommon")
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
        ts = FakeDet(category="time_sig_digit", smufl_name="timeSigCommon")
        assert parse_time_signature([nh, ts]) == {
            "numerator": 4, "denominator": 4, "raw": "C"
        }


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
