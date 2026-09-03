"""The per-measure aligner: tokens, LCS pairs, the class the truth names,
and where on the staff a pitch sits."""

from __future__ import annotations

import pytest

from tools.omr.training.measure_align import (
    align_tokens,
    event_tokens,
    expected_head_class,
    expected_rest_class,
    head_kind_for_type,
    merge_truth_parts,
    on_line_or_in_space,
    staff_y_for_pitch,
    truth_tokens,
)
from tools.omr.training.musicxml_truth import TruthNote

pytestmark = pytest.mark.omr_training


def _tn(pitch: str | None, onset: float, dur: float, ntype: str, *, rest=False,
        grace=False, dots=0, measure_rest=False) -> TruthNote:
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
                     measure_rest=measure_rest)


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
    assert [t.key for t in truth_tokens(notes)] == ["F4", "B3"]
    assert [t.key for t in truth_tokens(notes, match="exact")] == ["F#4", "Bb3"]
    dets = [_det("noteheadBlackOnLine", "F4", 10), _det("noteheadBlackInSpace", "B3", 40)]
    assert [t.key for t in event_tokens(_events(*dets))] == ["F4", "B3"]
    assert [t.key for t in event_tokens(_events(*dets), match="exact")] == ["F4", "B3"]


def test_grace_notes_are_skipped_and_rests_can_be() -> None:
    notes = [_tn("C5", 0, 0, "16th", grace=True), _tn("C5", 0, 1, "quarter"),
             _tn(None, 1, 1, "quarter", rest=True)]
    assert [t.key for t in truth_tokens(notes)] == ["C5", "R"]
    assert [t.key for t in truth_tokens(notes, include_rests=False)] == ["C5"]


def test_alignment_returns_pairs_and_the_leftovers() -> None:
    truth = truth_tokens([_tn("C4", 0, 1, "quarter"), _tn("E4", 1, 2, "half"),
                          _tn("G4", 3, 1, "quarter")])
    pred = event_tokens(_events(_det("noteheadBlackOnLine", "C4", 10),
                                _det("noteheadBlackInSpace", "A4", 40),
                                _det("noteheadBlackInSpace", "G4", 70)))
    al = align_tokens(truth, pred)
    assert al.pairs == [(0, 0), (2, 2)]
    assert al.truth_unmatched == [1]
    assert al.pred_unmatched == [1]
    assert al.strength == pytest.approx(2 / 3)
    # The pair carries the detection object itself, so the caller can find
    # the box by identity in `measure["detections"]`.
    assert pred[al.pairs[0][1]].ref["class"] == "noteheadBlackOnLine"


def test_alignment_is_order_preserving() -> None:
    truth = truth_tokens([_tn("C4", 0, 1, "quarter"), _tn("G4", 1, 1, "quarter")])
    pred = event_tokens(_events(_det("noteheadBlackOnLine", "G4", 10),
                                _det("noteheadBlackOnLine", "C4", 40)))
    al = align_tokens(truth, pred)
    assert al.matched == 1  # one of the two, never both crossed


def test_empty_sides_have_no_strength() -> None:
    assert align_tokens([], []).strength is None
    al = align_tokens(truth_tokens([_tn("C4", 0, 1, "quarter")]), [])
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
