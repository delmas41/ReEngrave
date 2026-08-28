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
    _stem_direction,
)


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
        # Stem extends upward — notehead's y_center is BELOW stem's y_mid
        nh = FakeNH(x_canonical=100, y_canonical=180, height_canonical=20)
        # y_center of notehead = 190
        stem = FakeStem(x_canonical=125, y_canonical=50, height_canonical=140)
        # y_mid of stem = 50 + 70 = 120
        # 190 > 120 → stem-up
        assert _stem_direction(nh, stem) == "up"

    def test_stem_down_notehead_at_top(self):
        # Stem extends downward — notehead's y_center is ABOVE stem's y_mid
        nh = FakeNH(x_canonical=100, y_canonical=40, height_canonical=20)
        # y_center = 50
        stem = FakeStem(x_canonical=125, y_canonical=50, height_canonical=140)
        # y_mid = 120
        # 50 < 120 → stem-down
        assert _stem_direction(nh, stem) == "down"


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
