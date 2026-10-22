"""Unit tests for the positional key-signature reader
(`tools/omr/key_signature_geometry.py`).

The slot tables are the load-bearing data in that module — get one position
wrong and every note on the staff moves — so they are checked here against the
pitches an engraver prints, independently of how the module derives them.
"""

from __future__ import annotations

import pytest

from tools.omr.key_signature_geometry import (
    FLAT_PITCHES,
    SHARP_PITCHES,
    alterations_for_fifths,
    fit_key_signature,
    slot_positions,
)


# ─── slot tables ────────────────────────────────────────────────────────────

class TestSlotTables:
    @pytest.mark.parametrize("clef", ["treble", "bass", "alto", "tenor"])
    def test_seven_slots_each(self, clef):
        assert len(slot_positions(clef, "#")) == 7
        assert len(slot_positions(clef, "b")) == 7

    def test_treble_sharps(self):
        # F5 C5 G5 D5 A4 E5 B4 — pos 0 is the top line (F5), increasing downward.
        assert slot_positions("treble", "#") == [0, 3, -1, 2, 5, 1, 4]

    def test_treble_flats(self):
        # B4 E5 A4 D5 G4 C5 F4
        assert slot_positions("treble", "b") == [4, 1, 5, 2, 6, 3, 7]

    def test_bass_is_treble_shifted_down_two_steps(self):
        # A bass clef names pitches two diatonic steps below a treble clef at
        # the same staff position, so its signature sits two steps lower.
        treble = slot_positions("treble", "#")
        assert slot_positions("bass", "#") == [p + 2 for p in treble]

    def test_third_sharp_sits_above_the_staff_in_treble(self):
        # G#5 is printed above the top line. Standard engraving, and the one
        # position in the treble table that looks like a bug.
        assert slot_positions("treble", "#")[2] == -1

    def test_seventh_flat_sits_below_the_staff_in_bass(self):
        # Fb2, below the bottom line (pos 8). Also standard.
        assert slot_positions("bass", "b")[6] == 9

    def test_tenor_first_sharp_breaks_the_octave_pattern(self):
        # F#3, not the F#4 transposition would give — which would sit above
        # the staff. The reason the tables are written out per clef.
        assert SHARP_PITCHES["tenor"][0] == "F3"
        assert 0 <= slot_positions("tenor", "#")[0] <= 8

    def test_every_tabled_position_is_near_the_staff(self):
        # No accidental in any table strays more than one step off the staff.
        for clef in ("treble", "bass", "alto", "tenor"):
            for acc in ("#", "b"):
                for pos in slot_positions(clef, acc):
                    assert -1 <= pos <= 9, (clef, acc, pos)

    def test_pitch_letters_follow_the_standard_order(self):
        for clef, pitches in SHARP_PITCHES.items():
            assert [p[0] for p in pitches] == ["F", "C", "G", "D", "A", "E", "B"], clef
        for clef, pitches in FLAT_PITCHES.items():
            assert [p[0] for p in pitches] == ["B", "E", "A", "D", "G", "C", "F"], clef

    def test_octave_suffix_does_not_move_the_printed_signature(self):
        # An 8vb marker changes what the staff sounds, not where its key
        # signature is printed.
        assert slot_positions("treble_8vb", "b") == slot_positions("treble", "b")

    def test_unknown_clef_abstains(self):
        assert slot_positions("soprano", "b") is None
        assert slot_positions(None, "b") is None


# ─── fitting ────────────────────────────────────────────────────────────────

class TestFit:
    def test_exact_three_flats(self):
        read = fit_key_signature(slot_positions("treble", "b")[:3], "treble", "b")
        assert read.fifths == -3
        assert read.matched_slots == (1, 2, 3)
        assert read.inferred_slots == ()

    def test_uniform_anchor_offset_is_absorbed(self):
        # A flat's box centre sits about a step above the pitch it alters. The
        # fit solves for that offset instead of needing it calibrated.
        shifted = [p - 0.9 for p in slot_positions("treble", "b")[:3]]
        read = fit_key_signature(shifted, "treble", "b")
        assert read.fifths == -3
        assert read.offset == pytest.approx(-0.9, abs=1e-6)

    def test_missed_interior_accidental_is_recovered(self):
        # THE case this module exists for: flats seen at slots 1, 2 and 4 mean
        # four flats with the third missed — not three flats.
        slots = slot_positions("treble", "b")
        read = fit_key_signature([slots[0], slots[1], slots[3]], "treble", "b")
        assert read.fifths == -4
        assert read.matched_slots == (1, 2, 4)
        assert read.inferred_slots == (3,)

    def test_trailing_accidentals_are_never_invented(self):
        # A clean three-flat signature stays three flats; the fit may fill an
        # interior gap but must never extend past the last observation.
        read = fit_key_signature(slot_positions("treble", "b")[:3], "treble", "b")
        assert read.count == 3

    def test_empty_observation_is_no_key_signature(self):
        read = fit_key_signature([], "treble", "b")
        assert read.fifths == 0 and read.accidental is None

    def test_off_pattern_ink_abstains(self):
        assert fit_key_signature([0.0, 0.3, 7.7], "treble", "b") is None

    def test_more_accidentals_than_slots_abstains(self):
        assert fit_key_signature([0.0] * 8, "treble", "b") is None

    def test_unknown_clef_abstains(self):
        assert fit_key_signature([4.0], "soprano", "b") is None

    def test_sharps_and_flats_are_distinguishable_by_pattern(self):
        # The zigzags run in opposite directions, which is what lets the
        # locator tell a sharp signature from a flat one without reading the
        # glyphs. Real sharp positions must fit sharps better than flats.
        sharps = slot_positions("treble", "#")[:3]
        sharp_fit = fit_key_signature(sharps, "treble", "#")
        flat_fit = fit_key_signature(sharps, "treble", "b")
        assert sharp_fit.residual == pytest.approx(0.0)
        assert flat_fit is None or flat_fit.residual > sharp_fit.residual

    @pytest.mark.parametrize("clef", ["treble", "bass", "alto", "tenor"])
    @pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6, 7])
    def test_every_signature_round_trips_under_every_tabled_clef(self, clef, n):
        for acc, sign in (("#", 1), ("b", -1)):
            observed = slot_positions(clef, acc)[:n]
            read = fit_key_signature(observed, clef, acc)
            assert read.fifths == sign * n, (clef, acc, n)


# ─── alteration map ─────────────────────────────────────────────────────────

class TestAlterations:
    def test_three_flats(self):
        assert alterations_for_fifths(-3) == {"B": "b", "E": "b", "A": "b"}

    def test_two_sharps(self):
        assert alterations_for_fifths(2) == {"F": "#", "C": "#"}

    def test_zero_is_empty(self):
        assert alterations_for_fifths(0) == {}
