"""The per-measure aligner: tokens, LCS pairs, the class the truth names,
and where on the staff a pitch sits."""

from __future__ import annotations

import pytest

from tools.omr.training.measure_align import (
    Token,
    align_tokens,
    detection_position,
    event_tokens,
    staff_position,
    expected_head_class,
    expected_rest_class,
    head_kind_for_type,
    merge_truth_parts,
    on_line_or_in_space,
    staff_y_for_pitch,
    tremolo_runs,
    abbreviation_type,
    collapse_tremolo_runs,
    truth_tokens,
)
from tools.omr.training.musicxml_truth import TruthNote

pytestmark = pytest.mark.omr_training


def _tn(pitch: str | None, onset: float, dur: float, ntype: str, *, rest=False,
        grace=False, dots=0, measure_rest=False, clef=None) -> TruthNote:
    step = octave = None
    alter = 0
    if pitch:
        step = pitch[0]
        octave = int(pitch[-1])
        alter = pitch.count("#") - pitch.count("b")
    return TruthNote(onset_ql=onset, duration_ql=dur, pitch=pitch, step=step, alter=alter,
                     octave=octave, type=ntype, dots=dots, rest=rest, chord=False,
                     grace=grace, voice="1", tuplet_actual=None, tuplet_normal=None,
                     tie_start=False, tie_stop=False, unpitched=False,
                     measure_rest=measure_rest, clef=clef)


def _det(cls: str, pitch: str | None, x: int, **extra) -> dict:
    d = {"class": cls, "category": "rest" if cls.startswith("rest") else "notehead",
         "bbox": [x, 100, 20, 20], "confidence": 0.9, "pitch": pitch}
    d.update(extra)
    return d


def _events(*dets: dict) -> list[dict]:
    """Minimal `group_chords_in_measure`-shaped events: one per detection."""
    out = []
    for d in dets:
        if d["category"] == "rest":
            out.append({"kind": "rest", "x_position": d["bbox"][0], "duration_beats": 1.0,
                        "duration_type": "quarter", "dots": 0, "noteheads": [], "rest": d})
        else:
            out.append({"kind": "chord", "x_position": d["bbox"][0], "duration_beats": 1.0,
                        "duration_type": "quarter", "dots": 0, "noteheads": [d], "rest": None})
    return out


def test_step_key_ignores_the_accidental_and_exact_does_not() -> None:
    notes = [_tn("F#4", 0, 1, "quarter"), _tn("Bb3", 1, 1, "quarter")]
    assert [t.key for t in truth_tokens(notes, match="step")] == ["F4", "B3"]
    assert [t.key for t in truth_tokens(notes, match="exact")] == ["F#4", "Bb3"]
    dets = [_det("noteheadBlackOnLine", "F4", 10), _det("noteheadBlackInSpace", "B3", 40)]
    assert [t.key for t in event_tokens(_events(*dets), match="step")] == ["F4", "B3"]
    assert [t.key for t in event_tokens(_events(*dets), match="exact")] == ["F4", "B3"]


def test_grace_notes_are_skipped_and_rests_can_be() -> None:
    notes = [_tn("C5", 0, 0, "16th", grace=True), _tn("C5", 0, 1, "quarter"),
             _tn(None, 1, 1, "quarter", rest=True)]
    assert [t.key for t in truth_tokens(notes, match="step")] == ["C5", "R"]
    assert [t.key for t in truth_tokens(notes, match="step", include_rests=False)] == ["C5"]


def test_alignment_returns_pairs_and_the_leftovers() -> None:
    truth = truth_tokens([_tn("C4", 0, 1, "quarter"), _tn("E4", 1, 2, "half"),
                          _tn("G4", 3, 1, "quarter")], match="step")
    pred = event_tokens(_events(_det("noteheadBlackOnLine", "C4", 10),
                                _det("noteheadBlackInSpace", "A4", 40),
                                _det("noteheadBlackInSpace", "G4", 70)), match="step")
    al = align_tokens(truth, pred)
    assert al.pairs == [(0, 0), (2, 2)]
    assert al.truth_unmatched == [1]
    assert al.pred_unmatched == [1]
    assert al.strength == pytest.approx(2 / 3)
    # The pair carries the detection object itself, so the caller can find
    # the box by identity in `measure["detections"]`.
    assert pred[al.pairs[0][1]].ref["class"] == "noteheadBlackOnLine"


def test_alignment_is_order_preserving() -> None:
    truth = truth_tokens([_tn("C4", 0, 1, "quarter"), _tn("G4", 1, 1, "quarter")], match="step")
    pred = event_tokens(_events(_det("noteheadBlackOnLine", "G4", 10),
                                _det("noteheadBlackOnLine", "C4", 40)), match="step")
    al = align_tokens(truth, pred)
    assert al.matched == 1  # one of the two, never both crossed


def test_empty_sides_have_no_strength() -> None:
    assert align_tokens([], []).strength is None
    al = align_tokens(truth_tokens([_tn("C4", 0, 1, "quarter")], match="step"), [])
    assert al.strength == 0.0 and al.truth_unmatched == [0]


def test_head_kind_and_expected_class_keep_position_and_size() -> None:
    assert head_kind_for_type("half") == "Half"
    assert head_kind_for_type("whole") == "Whole"
    assert head_kind_for_type("breve") == "DoubleWhole"
    assert head_kind_for_type("eighth") == "Black"
    assert head_kind_for_type(None) == "Black"
    assert expected_head_class("half", "noteheadBlackOnLine") == "noteheadHalfOnLine"
    assert expected_head_class("quarter", "noteheadHalfInSpaceSmall") == "noteheadBlackInSpaceSmall"
    assert expected_head_class("half", "restQuarter") is None
    assert expected_head_class("half", None) is None


def test_expected_rest_class() -> None:
    assert expected_rest_class(_tn(None, 0, 1, "quarter", rest=True)) == "restQuarter"
    assert expected_rest_class(_tn(None, 0, 0.5, "eighth", rest=True)) == "rest8th"
    assert expected_rest_class(_tn(None, 0, 4, None, rest=True, measure_rest=True)) == "restWhole"
    assert expected_rest_class(_tn(None, 0, 2, None, rest=True)) == "restHalf"


def test_merge_condensed_parts_collapses_unisons_and_drops_rests() -> None:
    fl1 = [_tn("G5", 0, 2, "half"), _tn(None, 2, 2, "half", rest=True)]
    fl2 = [_tn("G5", 0, 2, "half"), _tn("E5", 2, 2, "half")]
    merged = merge_truth_parts([fl1, fl2])
    assert [(n.pitch, n.onset_ql) for n in merged] == [("G5", 0.0), ("E5", 2.0)]
    # A single part keeps its rests.
    assert [n.rest for n in merge_truth_parts([fl1])] == [False, True]


@pytest.mark.parametrize("pitch,clef,y,pos", [
    ("F5", "treble", 100.0, "OnLine"),    # top line
    ("E4", "treble", 500.0, "OnLine"),    # bottom line
    ("G4", "treble", 400.0, "OnLine"),    # second line
    ("F4", "treble", 450.0, "InSpace"),   # first space
    ("C4", "treble", 600.0, "OnLine"),    # first ledger below
    ("A3", "bass", 100.0, "OnLine"),
    ("G2", "bass", 500.0, "OnLine"),
    ("C4", "alto", 300.0, "OnLine"),
    ("A3", "tenor", 300.0, "OnLine"),
    ("E4", "treble_8vb", 150.0, "InSpace"),
])
def test_staff_position_from_pitch_and_clef(pitch, clef, y, pos) -> None:
    lines = [100.0, 200.0, 300.0, 400.0, 500.0]
    assert staff_y_for_pitch(pitch, clef, lines) == pytest.approx(y)
    assert on_line_or_in_space(pitch, clef) == pos


def test_staff_position_abstains_without_a_clef() -> None:
    assert staff_y_for_pitch("E4", None, [1, 2, 3, 4, 5]) is None
    assert staff_y_for_pitch("E4", "percussion", [1, 2, 3, 4, 5]) is None
    assert staff_y_for_pitch("E4", "treble", []) is None
    assert on_line_or_in_space(None, "treble") is None


def test_staff_position_counts_half_steps_from_the_top_line() -> None:
    assert staff_position("F5", "treble") == 0
    assert staff_position("E4", "treble") == 8
    assert staff_position("G5", "treble") == -1
    assert staff_position("G3", "bass") == 1
    assert staff_position("C4", "alto") == 4
    assert staff_position("C4", None) is None


def test_position_match_survives_a_misread_clef() -> None:
    """The reference says bass clef, G3 then B3. The pipeline called the
    staff treble and spelled the heads B4 and D5 — wrong pitches, right
    boxes. On step keys nothing matches; on positions both do."""
    lines = [100.0, 200.0, 300.0, 400.0, 500.0]
    truth = [_tn("G3", 0, 2, "half", clef="bass"), _tn("B3", 2, 2, "half", clef="bass")]
    d1 = _det("noteheadBlackOnLine", "B4", 10)
    d1["bbox"] = [10, 130, 40, 40]      # centre y 150 → position 1 (G3 in bass)
    d2 = _det("noteheadBlackInSpace", "D5", 60)
    d2["bbox"] = [60, 30, 40, 40]       # centre y 50 → position -1 (B3 in bass)
    step = align_tokens(truth_tokens(truth, match="step"),
                        event_tokens(_events(d1, d2), match="step"))
    assert step.matched == 0
    pos = align_tokens(truth_tokens(truth),
                       event_tokens(_events(d1, d2), line_ys=lines))
    assert pos.pairs == [(0, 0), (1, 1)]
    assert detection_position(d1, lines) == 1 and detection_position(d2, lines) == -1


def test_position_match_falls_back_to_steps_without_geometry() -> None:
    truth = [_tn("G3", 0, 2, "half")]               # no clef in the reference
    d = _det("noteheadBlackOnLine", "G3", 10)
    al = align_tokens(truth_tokens(truth), event_tokens(_events(d), line_ys=None))
    assert al.matched == 1 and truth_tokens(truth)[0].key == "G3"


def test_alignment_tolerates_a_half_space_of_rounding_but_prefers_exact() -> None:
    """Sean's p3-sys0-s5-m5: truth P13 P6 P10 P3 P10 P3, read P13 P5 P10 P2
    P9 P2 — every upper note's box centre rounded half a space high."""
    lines = [100.0, 200.0, 300.0, 400.0, 500.0]
    def tk(key, i):
        return Token(key=key, pitch=None, is_rest=False, duration_ql=None, type=None,
                     dots=0, onset_ql=None, ref=None, index=i)
    truth = [tk(k, i) for i, k in enumerate(["P13", "P6", "P10", "P3", "P10", "P3"])]
    pred = [tk(k, i) for i, k in enumerate(["P13", "P5", "P10", "P2", "P9", "P2"])]
    al = align_tokens(truth, pred)
    assert al.pairs == [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5)]
    assert align_tokens(truth, pred, tolerance=0).matched == 2
    # An exact candidate wins over a near one: truth P4, read P5 then P4.
    truth = [tk("P4", 0)]
    pred = [tk("P5", 0), tk("P4", 1)]
    assert align_tokens(truth, pred).pairs == [(0, 1)]
    # Tolerance never crosses a rest or a step key.
    assert align_tokens([tk("R", 0)], [tk("P8", 0)]).matched == 0
    assert align_tokens([tk("G3", 0)], [tk("A3", 0)]).matched == 0


def test_tremolo_runs_and_their_abbreviation() -> None:
    six = [_tn("G2", k * 0.5, 0.5, "eighth") for k in range(6)]
    runs = tremolo_runs(six)
    assert len(runs) == 6 and runs[id(six[0])][:3] == (0, 6, 3.0) and runs[id(six[5])][0] == 5
    assert runs[id(six[5])][3] == id(six[0])
    assert abbreviation_type(3.0) == ("half", 1) and abbreviation_type(4.0) == ("whole", 0)
    assert abbreviation_type(2.5) is None
    # Two eighths are not a run; a change of pitch breaks one; a rest breaks one.
    assert tremolo_runs(six[:2]) == {}
    mixed = six[:3] + [_tn("A2", 1.5, 0.5, "eighth")] + six[4:]
    assert set(v[1] for v in tremolo_runs(mixed).values()) == set()   # 3 eighths = 1.5 < half
    four = [_tn("C4", k * 0.5, 0.5, "eighth") for k in range(4)]
    assert tremolo_runs(four)[id(four[0])][:3] == (0, 4, 2.0)
    broken = four[:2] + [_tn(None, 1.0, 0.5, "eighth", rest=True)] + four[2:]
    assert tremolo_runs(broken) == {}


def test_collapse_follows_the_reading() -> None:
    six = [_tn("G2", k * 0.5, 0.5, "eighth", clef="bass") for k in range(6)]   # P8 in bass
    one = collapse_tremolo_runs(six, [8])
    assert len(one) == 1 and one[0].tremolo_of == 6 and (one[0].type, one[0].dots) == ("half", 1)
    assert one[0].duration_ql == 3.0 and one[0].pitch == "G2" and one[0].clef == "bass"
    assert len(collapse_tremolo_runs(six, [8, 8, 8])) == 6            # printed out
    assert len(collapse_tremolo_runs(six, [])) == 1                   # nothing read: still one note
    three = [_tn("C4", k * 0.5, 0.5, "eighth", clef="treble") for k in range(3)]
    q = collapse_tremolo_runs(three, [10])
    assert len(q) == 1 and (q[0].type, q[0].dots) == ("quarter", 1)  # a dotted-quarter tremolo
