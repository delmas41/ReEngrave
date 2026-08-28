"""Clef proposal from an instrument's written range (tools/omr/clef_correction.py)."""
from __future__ import annotations

import pytest

from tools.omr.clef_correction import (
    _explicit_accidentals,
    _key_alterations,
    apply_proposal,
    correct_clefs_from_instruments,
    propose_clef,
    range_fit,
    restate_pitch,
    clef_was_read,
)
from tools.omr.instruments import lookup
from tools.omr.pitch_resolver import clef_diatonic_shift, pitch_to_midi

BASSOON = lookup("Fag.").instrument
VIOLA = lookup("Vla.").instrument
FLUTE = lookup("Fl.").instrument
PERCUSSION = lookup("Gran Cassa").instrument


def _notehead(pitch, bbox=(0, 0, 10, 10)):
    return {"category": "notehead", "class": "noteheadBlack", "pitch": pitch,
            "bbox": list(bbox)}


def _staff(pitches, clef="treble", staff_index=0, key_signature=None,
           extra=None):
    dets = [_notehead(p, (20 + 40 * i, 0, 10, 10)) for i, p in enumerate(pitches)]
    dets += extra or []
    return {
        "staff_index": staff_index,
        "clef": clef,
        "key_signature": key_signature,
        "measures": [{"measure_index": 0, "clef": clef,
                      "key_signature": key_signature, "detections": dets}],
    }


# ── the shift arithmetic ────────────────────────────────────────────────────

def test_clef_shift_is_the_inverse_of_itself():
    for a in ("treble", "bass", "alto", "tenor"):
        for b in ("treble", "bass", "alto", "tenor"):
            assert clef_diatonic_shift(a, b) == -clef_diatonic_shift(b, a)


def test_treble_to_bass_is_twelve_diatonic_steps_down():
    assert clef_diatonic_shift("treble", "bass") == -12


def test_restate_pitch_moves_the_letter_and_reapplies_the_key():
    # C5 read under bass clef instead of treble drops 12 diatonic steps -> E3.
    assert restate_pitch("C5", -12, {}, None) == "E3"
    # ...and takes the new letter's key-signature alteration.
    assert restate_pitch("C5", -12, {"E": -1}, None) == "Eb3"


def test_restate_pitch_keeps_an_explicitly_written_accidental():
    """An engraved accidental is a fact about the ink; the key signature is not."""
    assert restate_pitch("C5", -12, {"E": -1}, 1) == "E#3"
    assert restate_pitch("C5", -12, {"E": -1}, 0) == "E3"


def test_restate_pitch_on_junk():
    assert restate_pitch("wat", -12, {}, None) is None


# ── range fit ───────────────────────────────────────────────────────────────

def test_range_fit_counts_notes_inside_the_written_range():
    assert range_fit([40, 50, 60], 45, 65) == pytest.approx(2 / 3)
    assert range_fit([], 45, 65) == 0.0


def test_key_alterations_from_both_shapes():
    assert _key_alterations({"sharps": 2, "flats": 0}) == {"F": 1, "C": 1}
    assert _key_alterations({"sharps": 0, "flats": 3}) == {"B": -1, "E": -1, "A": -1}
    assert _key_alterations({"alterations": {"F": "#"}}) == {"F": 1}
    assert _key_alterations(None) == {}


# ── proposals ───────────────────────────────────────────────────────────────

def test_bassoon_defaulted_to_treble_is_proposed_bass():
    """The documented failure: a missed clef defaults to treble and transposes
    the whole staff. Under treble these notes sit far above a bassoon."""
    staff = _staff(["C5", "D5", "E5", "F5", "G5", "A5",
                    "B5", "C6", "D5", "E5", "F5", "G5"])
    p = propose_clef(staff, BASSOON)
    assert p is not None
    assert (p.from_clef, p.to_clef) == ("treble", "bass")
    assert p.current_fit < 0.2 and p.fit > 0.9


def test_viola_defaulted_to_treble_is_proposed_alto():
    """Range alone cannot separate these — a viola's range admits both readings
    — so the instrument's own default clef decides."""
    staff = _staff(["C5", "D5", "E5", "F5", "G5", "A4",
                    "B4", "C5", "D5", "E5", "F5", "G4"])
    p = propose_clef(staff, VIOLA)
    assert p is not None and p.to_clef == "alto"


def test_a_correct_treble_staff_is_left_alone():
    staff = _staff(["C5", "D5", "E5", "F5", "G5", "A5",
                    "B4", "C5", "D5", "E5", "F5", "G4"])
    assert propose_clef(staff, FLUTE) is None


def test_register_vetoes_the_instrument_convention():
    """A staff labelled bassoon whose notes really do sit in treble register
    must not be dragged to bass on the label's say-so."""
    staff = _staff(["C4", "D4", "E4", "F4", "G4", "A4",
                    "B3", "C4", "D4", "E4", "F4", "G3"], clef="bass")
    p = propose_clef(staff, BASSOON)
    # bass is already in effect and fits; nothing to propose
    assert p is None


def test_too_few_noteheads_abstains():
    assert propose_clef(_staff(["C5", "D5", "E5"]), BASSOON) is None


def test_unknown_clef_abstains():
    assert propose_clef(_staff(["C5"] * 12, clef="percussion"), BASSOON) is None


# ── applying ────────────────────────────────────────────────────────────────

def test_apply_proposal_restates_every_pitch_and_the_clef():
    staff = _staff(["C5"] * 12)
    p = propose_clef(staff, BASSOON)
    n = apply_proposal(staff, p)
    assert n == 12
    assert staff["clef"] == "bass"
    assert staff["measures"][0]["clef"] == "bass"
    pitches = {d["pitch"] for d in staff["measures"][0]["detections"]
               if d["category"] == "notehead"}
    assert pitches == {"E3"}


def test_apply_proposal_drops_stale_pitch_candidates():
    """M4 candidates were computed against the OLD clef's reading."""
    staff = _staff(["C5"] * 12)
    staff["measures"][0]["detections"][0]["pitch_candidates"] = [
        {"pitch": "C5", "weight": 1.0}]
    apply_proposal(staff, propose_clef(staff, BASSOON))
    assert "pitch_candidates" not in staff["measures"][0]["detections"][0]


def test_restated_pitches_land_inside_the_instrument_range():
    staff = _staff(["C5", "D5", "E5", "F5", "G5", "A5",
                    "B5", "C6", "D5", "E5", "F5", "G5"])
    apply_proposal(staff, propose_clef(staff, BASSOON))
    lo, hi = BASSOON.written_range
    midis = [pitch_to_midi(d["pitch"])
             for d in staff["measures"][0]["detections"]
             if d["category"] == "notehead"]
    assert all(lo <= m <= hi for m in midis)


# ── gating in the orchestrating pass ────────────────────────────────────────

def _page(staff):
    return {"page_index": 0,
            "systems": [{"system_index": 0, "staves": [staff]}]}


def test_a_staff_whose_clef_the_detector_read_is_flagged_but_not_changed():
    clef_det = {"category": "clef", "class": "clefG", "bbox": [0, 0, 10, 10]}
    staff = _staff(["C5"] * 12, extra=[clef_det])
    assert clef_was_read(staff)


def test_a_geometry_read_clef_counts_as_read_despite_no_clef_DETECTION():
    """clef_locator / clef_geometry read a clef by shape and by which staff line
    it sits on, emitting NO clef detection. Scanning detections would call this
    staff 'silent' and overwrite a confidently-read clef."""
    staff = _staff(["C5"] * 12)
    staff["clef_source"] = "cv_locator"
    assert clef_was_read(staff)
    recs = correct_clefs_from_instruments(
        [_page(staff)], {0: BASSOON}, {(0, 0, 0): 0}, apply=True)
    assert recs and not recs[0]["applied"]
    assert staff["clef"] == "treble", "a geometry-read clef must not be overwritten"


def test_absent_clef_source_means_defaulted():
    staff = _staff(["C5"] * 12)
    assert not clef_was_read(staff)
    recs = correct_clefs_from_instruments(
        [_page(staff)], {0: BASSOON}, {(0, 0, 0): 0}, apply=True)
    assert len(recs) == 1
    assert recs[0]["clef_was_read"] and not recs[0]["applied"]
    assert staff["clef"] == "treble", "a read clef must not be overwritten"


def test_a_staff_the_detector_was_silent_on_is_corrected():
    staff = _staff(["C5"] * 12)
    recs = correct_clefs_from_instruments(
        [_page(staff)], {0: BASSOON}, {(0, 0, 0): 0}, apply=True)
    assert recs[0]["applied"] and staff["clef"] == "bass"


def test_apply_false_reports_without_changing_anything():
    staff = _staff(["C5"] * 12)
    recs = correct_clefs_from_instruments(
        [_page(staff)], {0: BASSOON}, {(0, 0, 0): 0}, apply=False)
    assert recs and not recs[0]["applied"] and staff["clef"] == "treble"


def test_unpitched_staves_are_skipped():
    staff = _staff(["C5"] * 12)
    recs = correct_clefs_from_instruments(
        [_page(staff)], {0: PERCUSSION}, {(0, 0, 0): 0}, apply=True)
    assert recs == [] and staff["clef"] == "treble"


def test_a_staff_with_no_slot_is_skipped():
    staff = _staff(["C5"] * 12)
    assert correct_clefs_from_instruments([_page(staff)], {0: BASSOON}, {}) == []


def test_explicit_accidentals_pair_to_the_notehead_on_their_right():
    acc = {"category": "accidental", "class": "accidentalSharp", "bbox": [0, 0, 8, 20]}
    nh = _notehead("C5", (10, 5, 10, 10))
    far = _notehead("D5", (400, 5, 10, 10))
    got = _explicit_accidentals([acc, nh, far])
    assert got == {1: 1}
