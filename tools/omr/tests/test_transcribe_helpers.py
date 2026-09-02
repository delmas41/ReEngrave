"""Unit tests for tools/omr/transcribe.py helpers.

Phase 4a-h logic: clef name mapping, key signature alterations, pitch
parsing, accidental priority, etc.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from tools.omr.transcribe import (
    _bbox_overlap_area,
    _build_pitch,
    _in_written_range,
    _dedupe_cross_staff_detections,
    _drop_unladdered_noteheads,
    _ledger_ladder,
    _pitch_midi,
    _clef_name_from_class,
    _ClefContinuity,
    _default_clef_for_position,
    _detect_key_sig_from_cell,
    _filter_stems_overlapping_tremolo,
    _flag_measure_count_inconsistency,
    _is_tremolo_or_ornament_det,
    _key_sig_alterations,
    _key_sig_summary,
    _measure_rhythm_sum_warning,
    _parse_diatonic_pitch,
    _resolve_clef_weights,
    _staff_geometry,
    _stem_direction,
)
from tools.omr.types import Staff


class TestResolveClefWeights:
    """`transcribe()`'s OMR_CLEF_WEIGHTS fallback (Blocker 4). An explicit
    argument always wins; None falls back to the environment, matching what
    `main()` already does for the CLI — this is what makes it reachable from
    a direct caller like backend/modules/local_omr.py, which never passes
    `clef_weights` at all."""

    def test_explicit_argument_wins_over_env(self, monkeypatch):
        monkeypatch.setenv("OMR_CLEF_WEIGHTS", "/env/weights.pt")
        assert _resolve_clef_weights("/explicit/weights.pt") == "/explicit/weights.pt"

    def test_falls_back_to_env_when_not_given(self, monkeypatch):
        monkeypatch.setenv("OMR_CLEF_WEIGHTS", "/env/weights.pt")
        assert _resolve_clef_weights(None) == "/env/weights.pt"

    def test_none_when_neither_is_set(self, monkeypatch):
        monkeypatch.delenv("OMR_CLEF_WEIGHTS", raising=False)
        assert _resolve_clef_weights(None) is None

    def test_empty_env_value_is_treated_as_unset(self, monkeypatch):
        monkeypatch.setenv("OMR_CLEF_WEIGHTS", "")
        assert _resolve_clef_weights(None) is None


@dataclass
class FakeDet:
    smufl_name: str = ""
    category: str = ""
    x_canonical: int = 0
    y_canonical: int = 0
    width_canonical: int = 10
    height_canonical: int = 200
    confidence: float = 0.9


@dataclass
class FakeNH:
    """A notehead-shaped object for stem-direction tests."""
    x_canonical: int
    y_canonical: int
    width_canonical: int = 30
    height_canonical: int = 20


@dataclass
class FakeStem:
    x_canonical: int
    y_canonical: int
    width_canonical: int = 5
    height_canonical: int = 150


# ─── _clef_name_from_class ──────────────────────────────────────────────────


class TestClefNameFromClass:
    @pytest.mark.parametrize("smufl, expected", [
        ("clefG", "treble"),
        ("clefF", "bass"),
        ("clefCAlto", "alto"),
        ("clefCTenor", "tenor"),
    ])
    def test_standard_clefs(self, smufl, expected):
        assert _clef_name_from_class(smufl) == expected

    def test_unpitched_returns_none(self):
        assert _clef_name_from_class("clefUnpitchedPercussion") is None

    def test_octave_marker_returns_none(self):
        assert _clef_name_from_class("clef8") is None
        assert _clef_name_from_class("clef15") is None

    def test_generic_c_clef(self):
        # Without Alto/Tenor specifier, fall back to alto
        assert _clef_name_from_class("clefC") == "alto"

    def test_empty(self):
        assert _clef_name_from_class("") is None


# ─── _default_clef_for_position ────────────────────────────────────────────


class TestDefaultClefForPosition:
    def test_single_staff_is_treble(self):
        assert _default_clef_for_position(0, 1) == "treble"

    def test_piano_top_is_treble(self):
        assert _default_clef_for_position(0, 2) == "treble"

    def test_piano_bottom_is_bass(self):
        assert _default_clef_for_position(1, 2) == "bass"

    def test_three_staff_all_treble(self):
        # Anything with 3+ staves defaults to treble for unknown positions
        assert _default_clef_for_position(0, 3) == "treble"
        assert _default_clef_for_position(2, 3) == "treble"


# ─── _ClefContinuity ───────────────────────────────────────────────────────


def _run_system(cc, size, detections):
    """Drive one system through the continuity tracker. `detections` is a list
    (one per staff position) of a detected clef or None (missed). Returns the
    effective clef used at each position (detection wins, else inherited/default).
    """
    cc.start_system(size)
    effective = []
    for pos in range(size):
        start = cc.starting_clef(pos, _default_clef_for_position(pos, size))
        eff = detections[pos] if detections[pos] is not None else start
        cc.record(pos, eff)
        effective.append(eff)
    cc.end_system()
    return effective


class TestClefContinuity:
    def test_first_system_uses_position_default(self):
        cc = _ClefContinuity()
        # nothing to inherit yet -> position defaults (treble/bass for 2-staff)
        assert _run_system(cc, 2, [None, None]) == ["treble", "bass"]

    def test_missed_clef_inherits_by_role(self):
        cc = _ClefContinuity()
        # sys0: a viola (alto, pos 2) and cello (bass, pos 3) are detected
        _run_system(cc, 4, ["treble", "treble", "alto", "bass"])
        # sys1: pos 2,3 clefs MISSED -> inherit alto,bass instead of treble
        assert _run_system(cc, 4, ["treble", "treble", None, None]) == \
            ["treble", "treble", "alto", "bass"]

    def test_detection_overrides_inheritance(self):
        cc = _ClefContinuity()
        _run_system(cc, 3, ["treble", "alto", "bass"])
        # a real clef change on pos 1 (alto -> treble) still wins over inherit
        assert _run_system(cc, 3, [None, "treble", None]) == \
            ["treble", "treble", "bass"]

    def test_layout_change_blocks_inheritance(self):
        cc = _ClefContinuity()
        _run_system(cc, 4, ["treble", "treble", "alto", "bass"])
        # next system has a different staff count -> roles don't line up, so
        # fall back to position defaults (no wrong alto/bass carryover)
        assert _run_system(cc, 3, [None, None, None]) == \
            ["treble", "treble", "treble"]

    def test_inheritance_carries_across_pages(self):
        # No page concept inside the tracker — it just keeps threading, which
        # is exactly cross-page continuity when the next page's first system is
        # the same size.
        cc = _ClefContinuity()
        _run_system(cc, 2, ["treble", "bass"])       # page 0, last system
        # page 1, first system, bass clef missed -> inherits bass (not default,
        # which for 2-staff pos1 also happens to be bass; use a 3-staff case):
        cc2 = _ClefContinuity()
        _run_system(cc2, 3, ["treble", "bass", "bass"])   # e.g. bassoons on pos1,2
        assert _run_system(cc2, 3, [None, None, None]) == \
            ["treble", "bass", "bass"]

    def test_updates_to_latest_clef_each_system(self):
        cc = _ClefContinuity()
        _run_system(cc, 2, ["treble", "bass"])
        # pos1 changes to tenor via detection; the NEXT system should inherit tenor
        _run_system(cc, 2, [None, "tenor"])
        assert _run_system(cc, 2, [None, None]) == ["treble", "tenor"]


# ─── _key_sig_alterations + summary ────────────────────────────────────────


class TestKeySigAlterations:
    def test_c_major_empty(self):
        assert _key_sig_alterations(0, 0) == {}

    def test_one_sharp(self):
        assert _key_sig_alterations(1, 0) == {"F": "#"}

    def test_two_sharps(self):
        assert _key_sig_alterations(2, 0) == {"F": "#", "C": "#"}

    def test_seven_sharps(self):
        result = _key_sig_alterations(7, 0)
        assert set(result.keys()) == {"F", "C", "G", "D", "A", "E", "B"}
        assert all(v == "#" for v in result.values())

    def test_one_flat(self):
        assert _key_sig_alterations(0, 1) == {"B": "b"}

    def test_three_flats(self):
        assert _key_sig_alterations(0, 3) == {"B": "b", "E": "b", "A": "b"}


class TestKeySigFromDetectionPositions:
    """The slot fit applied to the DETECTOR's own key-signature markers.

    This is the path that matters on clean engravings, where the detector fires
    and its count is believed. Measured on WTC p.17 (E major, four sharps on
    every staff) counting read 6 of 10 staves right, failing as +1, +1, +2 and
    +5 — truncated counts and one spurious extra.
    """

    @staticmethod
    def _cell(spacing=100):
        @dataclass
        class FakeCell:
            staff_line_ys_canonical: list
        return FakeCell([400 + i * spacing for i in range(5)])

    @staticmethod
    def _markers(positions, spacing=100, accidental="keySharp"):
        """Detections centred at `positions` (steps below the top staff line)."""
        out = []
        for i, pos in enumerate(positions):
            centre = 400 + pos * (spacing / 2.0)
            out.append(FakeDet(
                smufl_name=accidental, category="accidental",
                x_canonical=100 + 60 * i, y_canonical=int(centre - 25),
                width_canonical=40, height_canonical=50,
            ))
        return out

    def test_all_four_sharps_seen(self):
        # treble sharp slots: F5 C5 G5 D5 -> 0, 3, -1, 2
        dets = self._markers([0, 3, -1, 2])
        assert _detect_key_sig_from_cell(dets, self._cell(), "treble") == \
            _key_sig_alterations(4, 0)

    def test_missed_interior_sharp_is_recovered(self):
        # Slots 1, 2 and 4 seen: FOUR sharps with the third missed, not three.
        # Counting these gives 3 — the WTC failure shape.
        dets = self._markers([0, 3, 2])
        assert _detect_key_sig_from_cell(dets, self._cell(), "treble") == \
            _key_sig_alterations(4, 0)

    def test_off_slot_marker_does_not_inflate_the_count(self):
        # Three real sharps plus one detection sitting on no slot at all.
        # Counting gives 4; the fit refuses to place the stray one.
        dets = self._markers([0, 3, -1, 6.5])
        result = _detect_key_sig_from_cell(dets, self._cell(), "treble")
        assert result == _key_sig_alterations(3, 0)

    def test_falls_back_to_counting_without_staff_geometry(self):
        dets = self._markers([0, 3, -1])
        assert _detect_key_sig_from_cell(dets, None, "treble") == \
            _key_sig_alterations(3, 0)

    def test_falls_back_to_counting_for_a_clef_with_no_slot_table(self):
        dets = self._markers([0, 3, -1])
        assert _detect_key_sig_from_cell(dets, self._cell(), "soprano") == \
            _key_sig_alterations(3, 0)

    def test_no_markers_returns_none(self):
        assert _detect_key_sig_from_cell([], self._cell(), "treble") is None

    def test_flats_are_read_the_same_way(self):
        # treble flat slots: B4 E5 A4 -> 4, 1, 5
        dets = self._markers([4, 1, 5], accidental="keyFlat")
        assert _detect_key_sig_from_cell(dets, self._cell(), "treble") == \
            _key_sig_alterations(0, 3)


class TestKeySigSummary:
    def test_empty(self):
        summary = _key_sig_summary({})
        assert summary == {"sharps": 0, "flats": 0, "alterations": {}}

    def test_sharps(self):
        summary = _key_sig_summary({"F": "#", "C": "#"})
        assert summary["sharps"] == 2
        assert summary["flats"] == 0

    def test_flats(self):
        summary = _key_sig_summary({"B": "b", "E": "b", "A": "b"})
        assert summary["sharps"] == 0
        assert summary["flats"] == 3


# ─── _detect_key_sig_from_cell ─────────────────────────────────────────────


class TestDetectKeySigFromCell:
    def test_no_key_markers_returns_none(self):
        # When no keySharp/keyFlat detections appear, return None (caller
        # should keep the previous active key sig).
        dets = [FakeDet(smufl_name="clefG", category="clef")]
        assert _detect_key_sig_from_cell(dets) is None

    def test_2_sharps(self):
        dets = [
            FakeDet(smufl_name="keySharp", category="accidental"),
            FakeDet(smufl_name="keySharp", category="accidental"),
        ]
        result = _detect_key_sig_from_cell(dets)
        assert result == {"F": "#", "C": "#"}

    def test_3_flats(self):
        dets = [
            FakeDet(smufl_name="keyFlat", category="accidental"),
            FakeDet(smufl_name="keyFlat", category="accidental"),
            FakeDet(smufl_name="keyFlat", category="accidental"),
        ]
        result = _detect_key_sig_from_cell(dets)
        assert result == {"B": "b", "E": "b", "A": "b"}

    def test_mixed_uses_larger_count(self):
        # In invalid notation (model emits both), trust the larger count.
        dets = [
            FakeDet(smufl_name="keySharp", category="accidental"),
            FakeDet(smufl_name="keySharp", category="accidental"),
            FakeDet(smufl_name="keySharp", category="accidental"),
            FakeDet(smufl_name="keyFlat", category="accidental"),
        ]
        result = _detect_key_sig_from_cell(dets)
        # 3 sharps wins
        assert result == {"F": "#", "C": "#", "G": "#"}


# ─── _parse_diatonic_pitch + _build_pitch ──────────────────────────────────


class TestParseDiatonicPitch:
    @pytest.mark.parametrize("pitch, expected", [
        ("C4", ("C", 4)),
        ("G5", ("G", 5)),
        ("A3", ("A", 3)),
    ])
    def test_valid(self, pitch, expected):
        assert _parse_diatonic_pitch(pitch) == expected

    def test_invalid_letter(self):
        assert _parse_diatonic_pitch("H4") is None

    def test_invalid_octave(self):
        assert _parse_diatonic_pitch("Cx") is None


class TestBuildPitch:
    def test_no_alteration(self):
        assert _build_pitch("C", None, 4) == "C4"

    def test_sharp(self):
        assert _build_pitch("F", "#", 5) == "F#5"

    def test_flat(self):
        assert _build_pitch("B", "b", 3) == "Bb3"

    def test_double_sharp(self):
        assert _build_pitch("G", "##", 4) == "G##4"


# ─── _measure_rhythm_sum_warning ───────────────────────────────────────────


def _nh(x, beats, duration_type, dots=0, stem=None):
    """A pitched, durationed notehead detection dict at canonical x=`x`,
    the shape voicing.group_chords_in_measure expects.
    """
    det = {
        "category": "notehead",
        "pitch": "C4",
        "bbox": [x, 0, 10, 10],
        "duration_beats": beats,
        "duration_type": duration_type,
        "dots": dots,
    }
    if stem is not None:
        det["stem_direction"] = stem
    return det


def _rest_det(x, beats, duration_type, dots=0):
    return {
        "category": "rest",
        "bbox": [x, 0, 10, 10],
        "duration_beats": beats,
        "duration_type": duration_type,
        "dots": dots,
    }


class TestMeasureRhythmSumWarning:
    def test_no_time_signature_is_skipped(self):
        # Only 3 quarters (3 beats) — would mismatch any 4/4-ish
        # expectation, but the check is skipped entirely without a known
        # time signature rather than assuming a default.
        dets = [_nh(x, 1.0, "quarter") for x in (0, 20, 40)]
        assert _measure_rhythm_sum_warning(dets, None) is None

    def test_missing_numerator_or_denominator_is_skipped(self):
        dets = [_nh(0, 1.0, "quarter")]
        assert _measure_rhythm_sum_warning(dets, {"numerator": None, "denominator": 4}) is None

    def test_exact_match_returns_none(self):
        time_sig = {"numerator": 4, "denominator": 4}
        dets = [_nh(x, 1.0, "quarter") for x in (0, 20, 40, 60)]
        assert _measure_rhythm_sum_warning(dets, time_sig) is None

    def test_within_tolerance_returns_none(self):
        time_sig = {"numerator": 4, "denominator": 4}
        # 3 full quarters + one a hair short of a quarter — total is off
        # by less than the 1/64-beat tolerance.
        dets = [_nh(x, 1.0, "quarter") for x in (0, 20, 40)]
        dets.append(_nh(60, 1.0 - 1.0 / 128, "quarter"))
        assert _measure_rhythm_sum_warning(dets, time_sig) is None

    def test_mismatch_returns_expected_and_actual_beats(self):
        time_sig = {"numerator": 4, "denominator": 4}
        # Only 3 quarters detected — a dropped note, e.g. a missed rest.
        dets = [_nh(x, 1.0, "quarter") for x in (0, 20, 40)]
        warning = _measure_rhythm_sum_warning(dets, time_sig)
        assert warning == {"expected_beats": 4.0, "actual_beats": 3.0}

    def test_rest_only_measure_uses_rest_duration(self):
        time_sig = {"numerator": 3, "denominator": 4}
        dets = [_rest_det(0, 2.0, "half")]  # only 2 of 3 beats rested
        warning = _measure_rhythm_sum_warning(dets, time_sig)
        assert warning == {"expected_beats": 3.0, "actual_beats": 2.0}

    def test_multi_voice_warns_on_max_deviation_voice(self):
        # Stem-up "melody" voice matches 4/4 exactly; stem-down "bass"
        # voice is missing two beats. group_chords_in_measure keeps each
        # note a separate event (x-spacing exceeds the chord tolerance),
        # split_events_into_voices then separates by stem direction.
        time_sig = {"numerator": 4, "denominator": 4}
        up_notes = [_nh(x, 1.0, "quarter", stem="up") for x in (0, 20, 40, 60)]
        down_notes = [_nh(x, 1.0, "quarter", stem="down") for x in (10, 30)]
        warning = _measure_rhythm_sum_warning(up_notes + down_notes, time_sig)
        assert warning == {"expected_beats": 4.0, "actual_beats": 2.0}


# ─── _stem_direction ────────────────────────────────────────────────────────


class TestStemDirection:
    def test_stem_up_notehead_at_bottom(self):
        # The stem projects far above the note and not below it.
        nh = FakeNH(x_canonical=100, y_canonical=180, height_canonical=20)
        stem = FakeStem(x_canonical=125, y_canonical=50, height_canonical=140)
        assert _stem_direction(stem, [nh]) == "up"

    def test_stem_down_notehead_at_top(self):
        # ...and here below it and not above.
        nh = FakeNH(x_canonical=100, y_canonical=40, height_canonical=20)
        stem = FakeStem(x_canonical=125, y_canonical=50, height_canonical=140)
        assert _stem_direction(stem, [nh]) == "down"

    def test_a_lone_notehead_may_be_passed_unwrapped(self):
        nh = FakeNH(x_canonical=100, y_canonical=180, height_canonical=20)
        stem = FakeStem(x_canonical=125, y_canonical=50, height_canonical=140)
        assert _stem_direction(stem, nh) == _stem_direction(stem, [nh])

    def test_a_double_stop_gets_ONE_direction(self):
        """Brahms's Viola: two noteheads an octave apart on one stem.

        Resolved a notehead at a time against the stem's midpoint, the lower
        note came out `up` and the upper `down` — which reads as divisi, and
        `voicing` then splits the chord into two voices.
        """
        # Stem runs from the lower note up past the upper one.
        lower = FakeNH(x_canonical=100, y_canonical=560, height_canonical=40)
        upper = FakeNH(x_canonical=100, y_canonical=290, height_canonical=40)
        stem = FakeStem(x_canonical=138, y_canonical=180, height_canonical=400)
        assert _stem_direction(stem, [lower, upper]) == "up"
        # Both members get the SAME answer, whichever order they arrive in.
        assert _stem_direction(stem, [upper, lower]) == "up"

    def test_a_stem_down_double_stop_too(self):
        lower = FakeNH(x_canonical=100, y_canonical=560, height_canonical=40)
        upper = FakeNH(x_canonical=100, y_canonical=290, height_canonical=40)
        # Stem hangs below the pair instead.
        stem = FakeStem(x_canonical=96, y_canonical=300, height_canonical=400)
        assert _stem_direction(stem, [lower, upper]) == "down"


# ─── _bbox_overlap_area / _is_tremolo_or_ornament_det /
#     _filter_stems_overlapping_tremolo ────────────────────────────────────
#
# Audit follow-up (2026-07): the classical-CV stem detector picks up
# tremolo/arpeggiato/ornament ink as phantom "stems" because it's also a
# tall, narrow, near-vertical run. Verified on real orchestral pages
# (Debussy "La Mer") that these phantom stems really do get selected by
# _stem_for_notehead / _find_attached_stem in some cells, changing the
# resolved duration or stem direction. These tests cover the geometric
# filter that rejects them.


def _stem(x, y, w=10, h=200):
    return FakeDet(smufl_name="stem", category="stem",
                    x_canonical=x, y_canonical=y,
                    width_canonical=w, height_canonical=h)


def _ornament(name, x, y, w=40, h=100):
    return FakeDet(smufl_name=name, category="ornament",
                    x_canonical=x, y_canonical=y,
                    width_canonical=w, height_canonical=h)


class TestBboxOverlapArea:
    def test_disjoint_boxes_zero_overlap(self):
        a = FakeDet(x_canonical=0, y_canonical=0, width_canonical=10, height_canonical=10)
        b = FakeDet(x_canonical=100, y_canonical=100, width_canonical=10, height_canonical=10)
        assert _bbox_overlap_area(a, b) == 0

    def test_full_containment(self):
        a = FakeDet(x_canonical=10, y_canonical=10, width_canonical=5, height_canonical=5)
        b = FakeDet(x_canonical=0, y_canonical=0, width_canonical=100, height_canonical=100)
        assert _bbox_overlap_area(a, b) == 25  # a's full area

    def test_partial_overlap(self):
        a = FakeDet(x_canonical=0, y_canonical=0, width_canonical=10, height_canonical=10)
        b = FakeDet(x_canonical=5, y_canonical=5, width_canonical=10, height_canonical=10)
        assert _bbox_overlap_area(a, b) == 25  # 5x5 overlap square


class TestIsTremoloOrOrnamentDet:
    @pytest.mark.parametrize("name", [
        "tremolo1", "tremolo2", "tremolo3", "tremolo4", "tremolo5",
        "arpeggiato",
        "ornamentTrill", "ornamentTurn", "ornamentTurnInverted", "ornamentMordent",
    ])
    def test_recognized_classes(self, name):
        assert _is_tremolo_or_ornament_det(FakeDet(smufl_name=name)) is True

    def test_case_and_punctuation_insensitive(self):
        assert _is_tremolo_or_ornament_det(FakeDet(smufl_name="TREMOLO-1")) is True

    @pytest.mark.parametrize("name", [
        "fermataAbove", "articStaccatoAbove", "graceNoteAppoggiaturaStemDown",
        "caesura", "fingering1", "stringsUpBow", "keyboardPedalPed",
        "noteheadBlackInSpace", "beam", "",
    ])
    def test_other_ornament_category_classes_not_matched(self, name):
        # These are also mapped to category="ornament" by
        # yolo_detector._CATEGORY_MAP, but they're not the tall/narrow
        # tremolo-or-arpeggio shapes the stem detector confuses itself
        # with — rejecting stems near them would be overly aggressive
        # (e.g. a staccato dot or fingering number sitting right next to
        # a real stem is extremely common).
        assert _is_tremolo_or_ornament_det(FakeDet(smufl_name=name)) is False


class TestFilterStemsOverlappingTremolo:
    def test_no_stems_is_noop(self):
        dets = [_ornament("arpeggiato", 0, 0)]
        assert _filter_stems_overlapping_tremolo([], dets) == []

    def test_no_ornament_dets_returns_stems_unchanged(self):
        # The common case: most cells have zero tremolo/arpeggiato/ornament
        # detections, so the filter must be a complete no-op.
        stems = [_stem(10, 10), _stem(50, 50)]
        dets = [FakeDet(smufl_name="noteheadBlackInSpace", category="notehead")]
        result = _filter_stems_overlapping_tremolo(stems, dets)
        assert result == stems

    def test_stem_mostly_inside_arpeggiato_is_rejected(self):
        # A phantom "stem" that the CV detector found INSIDE an arpeggio
        # squiggle's bbox — the real-world failure mode (Debussy "La Mer").
        stem = _stem(x=10, y=10, w=10, h=50)  # area 500
        arpeggiato = _ornament("arpeggiato", x=0, y=0, w=40, h=200)  # fully covers stem
        result = _filter_stems_overlapping_tremolo([stem], [arpeggiato])
        assert result == []

    def test_stem_barely_grazing_ornament_is_kept(self):
        # Overlap well under the 0.3-of-stem-area threshold — conservative
        # behavior: don't reject a real stem that just happens to be near
        # an ornament glyph.
        stem = _stem(x=0, y=0, w=10, h=100)  # area 1000
        # Overlap is a 10x5 = 50px^2 sliver -> 5% of the stem's area.
        arpeggiato = _ornament("arpeggiato", x=0, y=95, w=10, h=50)
        result = _filter_stems_overlapping_tremolo([stem], [arpeggiato])
        assert result == [stem]

    def test_stem_far_from_ornament_is_kept(self):
        stem = _stem(x=500, y=500, w=10, h=100)
        arpeggiato = _ornament("arpeggiato", x=0, y=0)
        result = _filter_stems_overlapping_tremolo([stem], [arpeggiato])
        assert result == [stem]

    def test_only_overlapping_stem_removed_others_kept(self):
        overlapping = _stem(x=10, y=10, w=10, h=50)
        distant = _stem(x=500, y=500, w=10, h=50)
        arpeggiato = _ornament("arpeggiato", x=0, y=0, w=40, h=200)
        result = _filter_stems_overlapping_tremolo([overlapping, distant], [arpeggiato])
        assert result == [distant]

    def test_non_ornament_notehead_does_not_trigger_rejection(self):
        # A stem sitting inside a NOTEHEAD's bbox (totally normal —
        # stems touch noteheads) must not be rejected.
        stem = _stem(x=10, y=10, w=10, h=50)
        notehead = FakeDet(smufl_name="noteheadBlackInSpace", category="notehead",
                            x_canonical=0, y_canonical=0, width_canonical=40, height_canonical=200)
        result = _filter_stems_overlapping_tremolo([stem], [notehead])
        assert result == [stem]


# ─── _flag_measure_count_inconsistency ─────────────────────────────────────
#
# Cross-staff measure-count consistency: barlines run through every staff of a
# system, so all staves must share the same measure count. A staff deviating
# from the strict-majority mode is flagged; near-even splits abstain.


def _staff(n_measures, *, staff_index=0, phase1=None):
    """A staff dict shaped like transcribe.py's page_dict staves: `n_measures`
    measure dicts. `phase1` marks the last cell a >2×-median (phase1) outlier:
      - "dense": phase1 cell WITH noteheads   (a fused pair of real measures)
      - "empty": phase1 cell with NO noteheads (a multi-measure rest / tacet)
      - None:    no phase1 cell
    """
    measures = [{"measure_index": j, "detections": []} for j in range(n_measures)]
    if phase1 and measures:
        measures[-1]["phase1_warning"] = "measure width is >2× the staff median"
        if phase1 == "dense":
            measures[-1]["detections"] = [{"category": "notehead"} for _ in range(6)]
    return {"staff_index": staff_index, "n_measures": n_measures, "measures": measures}


def _system(counts, *, dense=(), empty=()):
    """A system dict from a list of per-staff measure counts. `dense`/`empty` are
    sets of staff indices whose staff carries a dense / note-empty phase1 cell.
    """
    def kind(i):
        return "dense" if i in dense else ("empty" if i in empty else None)
    return {"staves": [
        _staff(c, staff_index=i, phase1=kind(i)) for i, c in enumerate(counts)
    ]}


def _run(counts, **kw):
    system = _system(counts, **kw)
    _flag_measure_count_inconsistency(system)
    return system


def _warnings(system):
    """staff_index -> its measure_count_warning (or None)."""
    return {st["staff_index"]: st.get("measure_count_warning")
            for st in system["staves"]}


class TestFlagMeasureCountInconsistency:
    def test_all_agree_writes_nothing(self):
        # The clean case: every staff has the same count -> byte-identical (no
        # measure_count_warning key added anywhere).
        system = _run([4, 4, 4])
        assert all("measure_count_warning" not in st for st in system["staves"])

    def test_single_staff_is_noop_even_with_phase1(self):
        # One staff has no sibling to cross-check against, so even a fused
        # (phase1) measure does NOT produce a measure_count_warning — this check
        # is purely about cross-staff disagreement.
        system = _run([4], dense={0})
        assert "measure_count_warning" not in system["staves"][0]

    def test_empty_system_is_noop(self):
        system = {"staves": []}
        _flag_measure_count_inconsistency(system)   # must not raise
        assert system == {"staves": []}

    def test_missing_staves_key_is_noop(self):
        system = {}
        _flag_measure_count_inconsistency(system)   # must not raise
        assert system == {}

    def test_lone_dissenter_short_flags_high(self):
        # 7 of 8 staves agree on 5 measures; one has 4 -> flag the deviant with
        # high confidence (consensus 0.875 >= 0.8), signed deviation -1 ("too
        # few" = a missed/fused barline).
        w = _warnings(_run([5, 5, 5, 5, 5, 5, 5, 4]))
        assert all(w[i] is None for i in range(7))
        assert w[7] == {
            "staff_measures": 4, "system_mode": 5, "agreement": "7/8",
            "deviation": -1, "confidence": 0.875, "confidence_label": "high",
            "phase1_corroborated": False, "likely_multimeasure_rest": False,
        }

    def test_dense_phase1_cell_sets_corroborated_high(self):
        # Same lone dissenter, but its shortfall coincides with a >2×-median
        # (phase1) cell that CONTAINS noteheads -> a fused pair of real measures
        # -> phase1_corroborated True, high (and NOT a multi-measure rest).
        w = _warnings(_run([5, 5, 5, 5, 5, 5, 5, 4], dense={7}))
        assert w[7]["phase1_corroborated"] is True
        assert w[7]["likely_multimeasure_rest"] is False
        assert w[7]["confidence_label"] == "high"

    def test_empty_phase1_cell_downweighted_as_mmr(self):
        # The dominant orchestral FP: the short staff's gap is a wide NOTE-EMPTY
        # cell -> a condensed multi-measure rest / tacet staff. Still flagged (it
        # IS a cross-staff disagreement), but NOT corroborated and DOWN-WEIGHTED
        # to low despite the strong 0.875 consensus.
        w = _warnings(_run([5, 5, 5, 5, 5, 5, 5, 4], empty={7}))
        assert w[7]["phase1_corroborated"] is False
        assert w[7]["likely_multimeasure_rest"] is True
        assert w[7]["confidence_label"] == "low"

    def test_mmr_downweight_overrides_strong_consensus(self):
        # A lone resting instrument among 15 playing staves: consensus is a
        # near-unanimous 0.9375, but a note-empty wide gap must never read as a
        # high-confidence missed barline.
        w = _warnings(_run([5] * 15 + [1], empty={15}))
        assert w[15]["confidence"] == round(15 / 16, 3)   # strong consensus…
        assert w[15]["likely_multimeasure_rest"] is True
        assert w[15]["confidence_label"] == "low"          # …still down-weighted

    def test_too_many_flags_positive_deviation_not_corroborated(self):
        # A staff with an EXTRA measure (spurious barline). deviation is +1 and
        # note-content corroboration only applies to SHORT staves, so even a
        # dense phase1 cell on this staff must not set corroborated or mmr.
        w = _warnings(_run([5, 5, 5, 6], dense={3}))
        assert w[3]["deviation"] == 1
        assert w[3]["phase1_corroborated"] is False
        assert w[3]["likely_multimeasure_rest"] is False

    def test_mmr_signature_needs_short_direction(self):
        # An empty wide cell on a too-MANY staff is not an MMR signature
        # (deviation > 0), so likely_multimeasure_rest stays False.
        w = _warnings(_run([5, 5, 5, 6], empty={3}))
        assert w[3]["likely_multimeasure_rest"] is False

    def test_promotion_needs_short_direction(self):
        # Guard: phase1 on a too-MANY staff does not promote via corroboration.
        # 3-of-4 majority -> consensus 0.75 -> medium (not high).
        w = _warnings(_run([5, 5, 5, 6], dense={3}))
        assert w[3]["confidence_label"] == "medium"

    def test_quartet_majority_medium(self):
        # 3 of 4 agree -> consensus 0.75 -> medium.
        w = _warnings(_run([6, 6, 6, 5]))
        assert w[3]["confidence_label"] == "medium"
        assert w[3]["deviation"] == -1 and w[3]["agreement"] == "3/4"

    def test_two_to_one_majority_medium_boundary(self):
        # consensus == 2/3 exactly -> medium (>= boundary).
        w = _warnings(_run([5, 5, 4]))
        assert w[2]["confidence"] == round(2 / 3, 3)
        assert w[2]["confidence_label"] == "medium"

    def test_bare_majority_is_low(self):
        # 3 of 5 agree -> consensus 0.6 (< 2/3) -> low; both dissenters flagged.
        w = _warnings(_run([2, 2, 2, 3, 3]))
        assert w[0] is None and w[1] is None and w[2] is None
        for i in (3, 4):
            assert w[i]["confidence_label"] == "low"
            assert w[i]["deviation"] == 1 and w[i]["agreement"] == "3/5"

    def test_piano_tie_abstains(self):
        # 2 staves disagree 1-1 -> no majority -> abstain (never guess which
        # hand is right). This is the honest ceiling the dossier layer resolves.
        assert all(v is None for v in _warnings(_run([5, 4])).values())

    def test_even_split_abstains(self):
        # 2-2 tie -> abstain.
        assert all(v is None for v in _warnings(_run([6, 6, 5, 5])).values())

    def test_plurality_without_majority_abstains(self):
        # mode 4 has only 3 of 6 (exactly half) -> not a strict majority -> abstain.
        assert all(v is None for v in _warnings(_run([4, 4, 4, 5, 5, 6])).values())

    def test_multiple_deviants_all_flagged(self):
        # Strong consensus (14/16); two different deviants both get flagged.
        counts = [5] * 14 + [4, 6]
        w = _warnings(_run(counts))
        assert w[14]["deviation"] == -1 and w[15]["deviation"] == 1
        assert w[14]["confidence_label"] == "high"   # consensus 0.875
        assert w[15]["confidence_label"] == "high"


# ─── _staff_geometry ────────────────────────────────────────────────────────


class TestStaffGeometry:
    """The staff frame emitted into the output JSON.

    Every geometric reading the pipeline makes — clef line, notehead pitch,
    key-signature slot — is measured against a staff's five lines, and until
    this block existed those lines were discarded at the file boundary: the
    readings shipped, the frame they were measured in did not.
    """

    @staticmethod
    def _staff(line_ys=(100, 120, 140, 160, 180), x_start=50, x_end=900):
        return Staff(
            page_index=0,
            staff_index=0,
            line_ys=list(line_ys),
            x_start=x_start,
            x_end=x_end,
        )

    def test_emits_the_five_lines_in_page_pixels(self):
        g = _staff_geometry(self._staff())
        assert g["line_ys_page"] == [100, 120, 140, 160, 180]
        assert g["line_spacing_px"] == 20.0
        assert g["x_start"] == 50 and g["x_end"] == 900

    def test_lines_are_ordered_top_to_bottom(self):
        # The clef table and the slot tables number lines 1=bottom..5=top off
        # this ordering; a reversed list would mis-number every reading.
        g = _staff_geometry(self._staff())
        assert g["line_ys_page"] == sorted(g["line_ys_page"])

    def test_uneven_spacing_reports_the_mean(self):
        g = _staff_geometry(self._staff(line_ys=(100, 121, 140, 159, 180)))
        assert g["line_spacing_px"] == 20.0

    def test_json_serializable(self):
        # numpy ints from Phase 1 would serialize-fail at the very end of a
        # long run; the cast has to happen here.
        import json

        g = _staff_geometry(self._staff())
        assert json.loads(json.dumps(g)) == g
        assert all(type(y) is int for y in g["line_ys_page"])

    def test_none_staff_abstains(self):
        assert _staff_geometry(None) is None

    def test_non_five_line_staff_abstains(self):
        # Same abstain-when-blind rule the geometric readers follow: line
        # numbering is only defined on a 5-line staff.
        assert _staff_geometry(self._staff(line_ys=(100, 120, 140, 160))) is None


# ─── Cross-staff attribution of ledger notes ────────────────────────────────


class TestPitchMidi:
    @pytest.mark.parametrize("pitch, midi", [
        ("C4", 60), ("A4", 69), ("Ab1", 32), ("C#4", 61),
        ("Bb1", 34), ("A6", 93), ("Cb4", 59), ("F##3", 55),
    ])
    def test_known(self, pitch, midi):
        assert _pitch_midi(pitch) == midi

    @pytest.mark.parametrize("pitch", [None, "", "H4", "C", "Cx", "4"])
    def test_unparseable(self, pitch):
        assert _pitch_midi(pitch) is None


class TestInWrittenRange:
    """The bassoon case, which is what this exists for: two adjacent bassoon
    staves contested one notehead and the reading kept was `Ab1` — MIDI 32,
    below the bassoon's written range of (34, 72) — while the one discarded was
    C4, squarely inside it."""

    def test_below_the_range(self):
        assert _in_written_range("Ab1", (34, 72)) is False

    def test_inside_the_range(self):
        assert _in_written_range("C4", (34, 72)) is True

    def test_an_unknown_part_gives_no_verdict(self):
        assert _in_written_range("C4", None) is None

    def test_an_unreadable_pitch_gives_no_verdict(self):
        assert _in_written_range(None, (34, 72)) is None

    def test_the_edges_are_inside(self):
        assert _in_written_range("Bb1", (34, 72)) is True
        assert _in_written_range("C5", (34, 72)) is True


class TestLedgerLadder:
    """Which staff a ledger note is JOINED to.

    Brahms's Violin 1 plays up to B6, and its cells carry three rungs per
    note-column at exactly the 1st/2nd/3rd ledger positions above a top line at
    7580, while nothing at all stands between those notes and the timpani staff
    above them.
    """

    TOP, BOTTOM, SPACING = 7580.0, 7743.0, 41.0
    BAND = (TOP, BOTTOM, SPACING)

    @staticmethod
    def _note(y_centre, x=3000, w=80, h=60):
        return [x, y_centre - h / 2, w, h]

    def _rungs_above(self, n, x=3000, w=80):
        return [(x, x + w, self.TOP - k * self.SPACING) for k in range(1, n + 1)]

    def test_a_complete_ladder_is_complete(self):
        note = self._note(self.TOP - 4.6 * self.SPACING)   # A6
        assert _ledger_ladder(note, self.BAND, self._rungs_above(4)) == (1, 4)

    def test_no_rungs_is_no_claim(self):
        note = self._note(self.TOP - 4.6 * self.SPACING)
        assert _ledger_ladder(note, self.BAND, []) == (0, 0)

    def test_a_broken_ladder_loses_to_a_complete_one(self):
        note = self._note(self.TOP - 4.6 * self.SPACING)
        broken = self._rungs_above(4)[:1] + self._rungs_above(4)[2:]   # rung 2 gone
        assert _ledger_ladder(note, self.BAND, broken) == (0, 3)
        assert _ledger_ladder(note, self.BAND, broken) < \
            _ledger_ladder(note, self.BAND, self._rungs_above(4))

    def test_rungs_under_a_different_note_do_not_count(self):
        note = self._note(self.TOP - 4.6 * self.SPACING, x=3000)
        elsewhere = [(500.0, 580.0, self.TOP - k * self.SPACING)
                     for k in range(1, 5)]
        assert _ledger_ladder(note, self.BAND, elsewhere) == (0, 0)

    def test_a_note_inside_the_staff_needs_no_ladder(self):
        note = self._note((self.TOP + self.BOTTOM) / 2)
        assert _ledger_ladder(note, self.BAND, self._rungs_above(4)) == (0, 0)

    def test_below_the_staff_reads_downwards(self):
        note = self._note(self.BOTTOM + 2.4 * self.SPACING)
        below = [(3000.0, 3080.0, self.BOTTOM + k * self.SPACING)
                 for k in range(1, 3)]
        assert _ledger_ladder(note, self.BAND, below) == (1, 2)

    def test_a_band_with_no_spacing_gives_no_verdict(self):
        note = self._note(self.TOP - 4.6 * self.SPACING)
        assert _ledger_ladder(note, (self.TOP, self.BOTTOM),
                              self._rungs_above(4)) == (0, 0)

    def test_a_note_on_the_first_ledger_needs_that_rung(self):
        """The truncation cliff the Beethoven bassoon pair sat on: a note ON
        the first ledger line measures ~1.0 spacings out, and int() read
        0.994 as needing NO rungs — so the same note was complete-with-one-
        rung in one bar and no-claim in the bar beside it, one pixel apart.
        """
        for jitter in (-0.006, 0.0, +0.018):
            note = self._note(self.TOP - (1.0 + jitter) * self.SPACING)
            assert _ledger_ladder(note, self.BAND,
                                  self._rungs_above(1)) == (1, 1)
            # And with the rung missing, that is a BROKEN ladder, not silence.
            assert _ledger_ladder(note, self.BAND, []) == (0, 0)


class TestBrokenLaddersAreNotEvidence:
    """The bar-7 inversion on the Beethoven bassoon pair: the ghost's one
    found rung was the real note's own ledger line counted from the wrong
    staff's anchor, and comparing broken ladders by rung count handed the
    contest to the ghost. Unless exactly one side's ladder is unbroken the
    pair must fall through to range/distance.
    """

    @staticmethod
    def _page(staff_a_dets, staff_b_dets, ledger_dets=()):
        def staff(idx, dets):
            return {"staff_index": idx,
                    "measures": [{"measure_index": 0,
                                  "detections": list(dets)}]}
        extra = {"staff_index": 2,
                 "measures": [{"measure_index": 0,
                               "detections": list(ledger_dets)}]}
        return {"systems": [{"staves": [staff(0, staff_a_dets),
                                        staff(1, staff_b_dets), extra]}]}

    @staticmethod
    def _note(y, conf=0.9):
        box = [50, y - 15, 30, 30]
        return {"category": "notehead", "class": "noteheadBlackOnLine",
                "confidence": conf, "bbox": box, "bbox_page": box,
                "pitch": "C4"}

    @staticmethod
    def _ledger(y):
        box = [45, y - 2, 40, 4]
        return {"category": "other", "class": "ledgerLine",
                "confidence": 0.9, "bbox": box, "bbox_page": box}

    def test_broken_vs_broken_falls_through_to_distance(self):
        # Bands 25px apart in spacing terms: staff 0 at 100..200, staff 1 at
        # 400..500. The ink sits at y=350 — 6 spacings below staff 0 (one
        # stray rung found at its 5th position, a BROKEN ladder) and 2
        # spacings above staff 1 (no rungs at all). Counting rungs kept the
        # far copy; distance keeps the near one.
        a, b = self._note(350), self._note(350)
        pg = self._page([a], [b], ledger_dets=[self._ledger(325)])
        bands = {0: (100, 200, 25), 1: (400, 500, 25), 2: (700, 800, 25)}
        assert _dedupe_cross_staff_detections(pg, bands) == 1
        kept = [s["measures"][0]["detections"]
                for s in pg["systems"][0]["staves"]]
        assert kept[0] == [] and kept[1] == [b]

    def test_a_complete_ladder_still_wins_over_distance(self):
        # Same geometry, but staff 0's copy carries EVERY rung it calls for:
        # the ladder joins it to staff 0 even though staff 1 is nearer.
        a, b = self._note(350), self._note(350)
        rungs = [self._ledger(200 + k * 25) for k in range(1, 7)]
        pg = self._page([a], [b], ledger_dets=rungs)
        bands = {0: (100, 200, 25), 1: (400, 500, 25), 2: (700, 800, 25)}
        assert _dedupe_cross_staff_detections(pg, bands) == 1
        kept = [s["measures"][0]["detections"]
                for s in pg["systems"][0]["staves"]]
        assert kept[0] == [a] and kept[1] == []


class TestDropUnladderedNoteheads:
    """A letter bowl between staves is whole, notehead-sized and interior, so
    the edge-fragment rule cannot see it. What separates it from music is the
    pairing: no ledger rung where a real outside-staff note hangs on one, AND
    detector doubt — measured 0.45-0.53 for the four fakes against 0.76+ for
    every real outside-staff notehead on the three benchmark works.
    """

    BANDS = {0: (100, 200, 25)}

    @staticmethod
    def _page(dets):
        return {"systems": [{"staves": [
            {"staff_index": 0,
             "measures": [{"measure_index": 0, "detections": list(dets)}]}]}]}

    @staticmethod
    def _note(y, conf):
        box = [50, y - 12, 30, 24]
        return {"category": "notehead", "class": "noteheadWholeInSpace",
                "confidence": conf, "bbox": box, "bbox_page": box}

    @staticmethod
    def _ledger(y):
        box = [45, y - 2, 40, 4]
        return {"category": "other", "class": "ledgerLine",
                "confidence": 0.9, "bbox": box, "bbox_page": box}

    def test_a_doubted_unladdered_outside_notehead_goes(self):
        pg = self._page([self._note(50, conf=0.53)])
        assert _drop_unladdered_noteheads(pg, self.BANDS) == 1
        assert pg["systems"][0]["staves"][0]["measures"][0]["detections"] == []

    def test_confidence_alone_saves_it(self):
        pg = self._page([self._note(50, conf=0.82)])
        assert _drop_unladdered_noteheads(pg, self.BANDS) == 0

    def test_one_rung_saves_it(self):
        pg = self._page([self._note(50, conf=0.53), self._ledger(75)])
        assert _drop_unladdered_noteheads(pg, self.BANDS) == 0

    def test_inside_the_staff_is_never_touched(self):
        pg = self._page([self._note(150, conf=0.30)])
        assert _drop_unladdered_noteheads(pg, self.BANDS) == 0

    def test_just_off_the_edge_expects_no_rung_and_stays(self):
        # 0.6 spacings out: no ledger position between it and the staff.
        pg = self._page([self._note(85, conf=0.40)])
        assert _drop_unladdered_noteheads(pg, self.BANDS) == 0

    def test_abstains_without_spacing(self):
        pg = self._page([self._note(50, conf=0.40)])
        assert _drop_unladdered_noteheads(pg, {0: (100, 200)}) == 0


class TestContextualCallSeam:
    """`transcribe` -> `apply_contextual_analysis` is a kwargs seam that broke
    SILENTLY once: the callee renamed `vision_fallback` away and the caller's
    try/except filed the TypeError into `contextual.reason`, so the documented
    on-by-default pass was a no-op on every transcription (0 of 21 staves named
    on the Brahms benchmark page) while the suite stayed green. These tests make
    that failure loud: they bind the caller's actual kwargs against the callee's
    actual signature, and then make the call.
    """

    def test_kwargs_bind_against_the_real_signature(self):
        import inspect
        from pathlib import Path

        from tools.omr.contextual import apply_contextual_analysis
        from tools.omr.transcribe import _contextual_call_kwargs

        kwargs = _contextual_call_kwargs(
            pdf_path=Path("does-not-exist.pdf"), dpi=300,
            dossier=None, vision_fallback=False,
        )
        # Raises TypeError on any renamed/removed parameter — the exact class
        # of break the production try/except would swallow.
        inspect.signature(apply_contextual_analysis).bind(
            {"pages": []}, staved=None, **kwargs,
        )

    def test_the_call_itself_survives_and_reports_unavailable_not_typeerror(self):
        from pathlib import Path

        from tools.omr.contextual import apply_contextual_analysis
        from tools.omr.transcribe import _contextual_call_kwargs

        summary = apply_contextual_analysis(
            {"pages": []},
            staved=None,
            **_contextual_call_kwargs(
                pdf_path=Path("does-not-exist.pdf"), dpi=300,
                dossier=None, vision_fallback=False,
            ),
        )
        assert summary["available"] is False
        assert "TypeError" not in str(summary.get("reason"))

    def test_the_flag_maps_onto_the_assist_modes_that_spend_nothing_by_default(self):
        from pathlib import Path

        from tools.omr.transcribe import _contextual_call_kwargs

        off = _contextual_call_kwargs(
            pdf_path=Path("x.pdf"), dpi=300, dossier=None, vision_fallback=False)
        on = _contextual_call_kwargs(
            pdf_path=Path("x.pdf"), dpi=300, dossier=None, vision_fallback=True)
        assert off["assist"].mode == "none"
        assert on["assist"].mode == "vision"


class TestOptionalPassFailureIsLoudAboutBugs:
    """The contextual pass went dark behind an `except Exception`.

    Every check that existed said things were fine: the suite was green, the
    OMR-NED number did not move (contextual's two channels into the export —
    part names and clef fill — provably do not reach the metric on the dossier-
    seeded fixtures), and the one line of stderr that would have told anyone was
    gated on `progress`, which `orchestral_eval` sets to False. So the ONLY
    surviving signal was invisible in the benchmark everybody runs.

    These tests are about the swallow itself rather than about one renamed
    parameter: an optional enrichment may abstain quietly, but it may not fail
    like a defect quietly.
    """

    def test_the_exact_failure_that_hid_is_flagged_as_a_bug(self):
        from tools.omr.transcribe import _optional_pass_failure

        record = _optional_pass_failure(
            "contextual analysis",
            TypeError("apply_contextual_analysis() got an unexpected keyword "
                      "argument 'vision_fallback'"),
            progress=False,
        )
        assert record["available"] is False
        assert record["error_class"] == "TypeError"
        assert record["looks_like_a_bug"] is True

    def test_a_bug_is_announced_even_when_progress_is_silenced(self, capsys):
        """`orchestral_eval` runs progress=False. A caller who silences progress
        asked not to be told about NOTES, not about defects."""
        from tools.omr.transcribe import _optional_pass_failure

        _optional_pass_failure("contextual analysis",
                               TypeError("boom"), progress=False)
        err = capsys.readouterr().err
        assert "contextual analysis" in err
        assert "BUG" in err

    def test_a_missing_optional_dependency_stays_quiet(self, capsys):
        """The Surya and musicdiff venvs are meant to be absent on a fresh
        clone — that is an environment fact, not a defect, and shouting about
        it would train everyone to ignore the shouting."""
        from tools.omr.transcribe import _optional_pass_failure

        record = _optional_pass_failure(
            "contextual analysis", ImportError("No module named 'surya'"),
            progress=False)
        assert record["looks_like_a_bug"] is False
        assert capsys.readouterr().err == ""

    @pytest.mark.parametrize("exc", [
        TypeError("renamed parameter"),
        AttributeError("moved attribute"),
        NameError("typo"),
        KeyError("missing key"),
        IndexError("off by one"),
        ValueError("bad argument"),
    ])
    def test_the_defect_shaped_exceptions_are_all_flagged(self, exc):
        from tools.omr.transcribe import _optional_pass_failure

        assert _optional_pass_failure("p", exc, progress=False)["looks_like_a_bug"]

    def test_every_failure_still_records_available_false_and_a_reason(self):
        """The contract callers already depend on must not change: a failed
        enrichment reports itself, it does not raise and lose the
        transcription."""
        from tools.omr.transcribe import _optional_pass_failure

        for exc in (TypeError("x"), ImportError("y"), RuntimeError("z")):
            record = _optional_pass_failure("p", exc, progress=False)
            assert record["available"] is False
            assert type(exc).__name__ in record["reason"]

    def test_both_optional_passes_route_through_it(self):
        """Two copies of this swallow exist — contextual and direction text —
        and one of them has already gone dark this way. Neither may hand-roll
        the record again."""
        import inspect

        from tools.omr import transcribe as T

        src = inspect.getsource(T.transcribe)
        assert src.count("_optional_pass_failure(") == 2
        # the old hand-rolled shape, which is what hid the failure
        assert '"reason": f"{type(exc).__name__}: {exc}"' not in src
