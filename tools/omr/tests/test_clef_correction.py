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
    recs = correct_clefs_from_instruments(
        [_page(staff)], {0: BASSOON}, {(0, 0, 0): 0}, apply=True)
    assert len(recs) == 1
    assert recs[0]["clef_was_read"] and not recs[0]["applied"]
    assert staff["clef"] == "treble", "a read clef must not be overwritten"


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


# ── a part keeps its clef between systems ───────────────────────────────────


class TestSlotClefContinuity:
    """A staff that read no clef can borrow the one its own part read in
    another system (`contextual._fill_defaulted_clefs`).

    This is not the cross-system clef vote dropped in 2026-07. That one
    majority-voted each role's FINAL clef across same-sized systems, and failed
    two ways: same-sized systems are not the same instruments on a condensed
    score, and the majority reading can be the wrong one. Both objections are
    answered structurally here — parts come from slot ALIGNMENT rather than
    equal staff counts, and a reading is never overruled, only a silence
    filled. These tests hold that line.
    """

    @staticmethod
    def _pages(sys0_staff, sys1_staff):
        return [{
            "page_index": 0,
            "systems": [
                {"system_index": 0, "staves": [sys0_staff]},
                {"system_index": 1, "staves": [sys1_staff]},
            ],
        }]

    SLOTS = {(0, 0, 0): 3, (0, 1, 0): 3}    # both staves are the same part

    def test_a_defaulted_staff_takes_the_clef_its_part_read(self):
        from tools.omr.contextual import _fill_defaulted_clefs

        defaulted = _staff(["C4"], clef="treble")            # no clef_source
        read = _staff(["C3"], clef="bass")
        read["clef_source"] = "detector"
        pages = self._pages(defaulted, read)
        filled = _fill_defaulted_clefs(pages, self.SLOTS)
        assert len(filled) == 1
        assert defaulted["clef"] == "bass"
        assert defaulted["clef_source"] == "slot_continuity"

    def test_a_clef_that_was_read_is_never_overruled(self):
        """The 'majority ≠ correct' objection, made structural: whatever the
        other system says, a staff that was actually read keeps its reading."""
        from tools.omr.contextual import _fill_defaulted_clefs

        read_treble = _staff(["C4"], clef="treble")
        read_treble["clef_source"] = "detector"
        read_bass = _staff(["C3"], clef="bass")
        read_bass["clef_source"] = "detector"
        pages = self._pages(read_treble, read_bass)
        assert _fill_defaulted_clefs(pages, self.SLOTS) == []
        assert read_treble["clef"] == "treble"
        assert read_bass["clef"] == "bass"

    def test_disagreeing_readings_fill_nothing(self):
        """Three staves of one part, two of them read and disagreeing: the
        third stays on its default rather than following a coin flip."""
        from tools.omr.contextual import _fill_defaulted_clefs

        defaulted = _staff(["C4"], clef="treble")
        read_a = _staff(["C3"], clef="bass")
        read_a["clef_source"] = "detector"
        read_b = _staff(["C4"], clef="alto")
        read_b["clef_source"] = "detector"
        pages = [{
            "page_index": 0,
            "systems": [
                {"system_index": 0, "staves": [defaulted]},
                {"system_index": 1, "staves": [read_a]},
                {"system_index": 2, "staves": [read_b]},
            ],
        }]
        slots = {(0, 0, 0): 3, (0, 1, 0): 3, (0, 2, 0): 3}
        assert _fill_defaulted_clefs(pages, slots) == []
        assert defaulted["clef"] == "treble"
        assert "clef_source" not in defaulted

    def test_an_unaligned_staff_borrows_nothing(self):
        """Slot -1 is "this staff could not be placed". It is not a part, so it
        has no other systems to borrow from."""
        from tools.omr.contextual import _fill_defaulted_clefs

        defaulted = _staff(["C4"], clef="treble")
        read = _staff(["C3"], clef="bass")
        read["clef_source"] = "detector"
        pages = self._pages(defaulted, read)
        slots = {(0, 0, 0): -1, (0, 1, 0): 3}
        assert _fill_defaulted_clefs(pages, slots) == []
        assert defaulted["clef"] == "treble"


# ── OMR_INSTRUMENT_CLEF_DEFAULT: the treble-override tier ───────────────────
#
# Verified sites and refusals: benchmarks/omr-clef-string-staves-2026-09.
# Everything here is OFF unless the caller passes treble_override=True (wired
# from the env flag through contextual), and every gate below is one a real
# staff in the scan pool earned.

from tools.omr.clef_correction import (  # noqa: E402
    MID_STAFF_CHANGE_VETOES,
    TREBLE_OVERRIDE_INSTRUMENTS,
    veto_implausible_clef_changes,
)

VIOLIN = lookup("Violino I").instrument
CELLO = lookup("Vc.").instrument


def _clef_det(cls="clefG"):
    return {"category": "clef", "class": cls, "bbox": [0, 0, 10, 10]}


def _viola_staff_read_treble():
    """575951-p1 s9 in miniature: a viola staff whose alto glyph the detector
    read as treble — register fits both readings, the label says Viola."""
    staff = _staff(["C5", "D5", "E5", "F5", "G5", "A4",
                    "B4", "C5", "D5", "E5", "F5", "G4"],
                   extra=[_clef_det("clefG")])
    staff["clef_source"] = "detector"
    return staff


class TestTrebleOverride:
    def test_the_table_holds_only_verified_instruments(self):
        # Membership is a REVIEWABLE decision, not a convenience — widening it
        # must be a deliberate diff. Contrabassoon added 2026-09-05 against the
        # table's own standard (a verified treble-misread site with register
        # evidence): both Brahms p4 Kontrafagott staves propose treble->bass at
        # fit 1.000 with current_fit 0.000, i.e. the clef in effect places not
        # one of their 13 and 18 noteheads inside the written range. It had been
        # covered only by accident, via `K-Fag.` mis-resolving to Bassoon, until
        # the lexicon was corrected the same day.
        assert set(TREBLE_OVERRIDE_INSTRUMENTS) == {
            "Viola", "Bassoon", "Contrabassoon", "Timpani"}
        for name in TREBLE_OVERRIDE_INSTRUMENTS:
            inst = lookup(name).instrument
            assert inst.default_clef != "treble", (
                "the override applies the instrument's default clef; a treble "
                "default would make it a no-op that still claims a record")

    def test_label_named_viola_read_treble_is_overridden(self):
        staff = _viola_staff_read_treble()
        recs = correct_clefs_from_instruments(
            [_page(staff)], {0: VIOLA}, {(0, 0, 0): 0}, apply=True,
            treble_override=True, instrument_source_by_slot={0: "label"})
        assert recs and recs[0]["applied"] and recs[0]["override"] == "treble_misread"
        assert staff["clef"] == "alto"
        # treble → alto is −6 diatonic steps: the C5 opening lands on D4.
        assert staff["measures"][0]["detections"][0]["pitch"] == "D4"

    def test_flag_off_is_the_shipped_behavior(self):
        staff = _viola_staff_read_treble()
        recs = correct_clefs_from_instruments(
            [_page(staff)], {0: VIOLA}, {(0, 0, 0): 0}, apply=True,
            instrument_source_by_slot={0: "label"})
        assert recs and not recs[0]["applied"] and "override" not in recs[0]
        assert staff["clef"] == "treble"

    def test_score_order_identity_never_drives_an_override(self):
        """The p2 violas are named 'Violin' by the score-order prior — the
        measured failure this gate exists for (Beethoven 5 p.15)."""
        staff = _viola_staff_read_treble()
        recs = correct_clefs_from_instruments(
            [_page(staff)], {0: VIOLA}, {(0, 0, 0): 0}, apply=True,
            treble_override=True, instrument_source_by_slot={0: "score_order"})
        assert recs and not recs[0]["applied"]
        assert staff["clef"] == "treble"

    def test_score_order_ambiguity_is_not_label_either(self):
        staff = _viola_staff_read_treble()
        recs = correct_clefs_from_instruments(
            [_page(staff)], {0: VIOLA}, {(0, 0, 0): 0}, apply=True,
            treble_override=True,
            instrument_source_by_slot={0: "score_order_ambiguity"})
        assert recs and not recs[0]["applied"]

    def test_a_detected_non_treble_clef_is_never_overridden(self):
        """brahms-p1's cello reads TENOR correctly while the convention says
        bass (fit ties 1.0/1.0). Treble-only is what keeps it safe — asserted
        on Bassoon, which IS in the override table."""
        staff = _staff(["C4", "D4", "E4", "F4", "G3", "A3",
                        "B3", "C4", "D4", "E4", "F4", "G4"],
                       clef="tenor", extra=[_clef_det("clefCTenor")])
        staff["clef_source"] = "detector"
        recs = correct_clefs_from_instruments(
            [_page(staff)], {0: BASSOON}, {(0, 0, 0): 0}, apply=True,
            treble_override=True, instrument_source_by_slot={0: "label"})
        assert staff["clef"] == "tenor", "a read non-treble clef stands"
        assert not any(r["applied"] for r in recs)

    def test_a_mid_staff_change_blocks_the_header_override(self):
        """A one-delta restatement of a mixed staff would shift the measures
        resolved under the other clef too — that staff belongs to the veto."""
        staff = _viola_staff_read_treble()
        staff["measures"].append({
            "measure_index": 1, "clef": "bass", "key_signature": None,
            "detections": [_notehead("E3")]})
        recs = correct_clefs_from_instruments(
            [_page(staff)], {0: VIOLA}, {(0, 0, 0): 0}, apply=True,
            treble_override=True, instrument_source_by_slot={0: "label"})
        assert staff["clef"] == "treble"
        assert not any(r["applied"] for r in recs)

    def test_off_table_instruments_stay_gap_only(self):
        """Cello is deliberately absent: no verified treble-misread site, and
        the pool's one cello clef error is one the convention agrees with."""
        staff = _staff(["C4", "D4", "E4", "F4", "G3", "A3",
                        "B3", "C4", "D4", "E4", "F4", "G4"],
                       extra=[_clef_det("clefG")])
        staff["clef_source"] = "detector"
        recs = correct_clefs_from_instruments(
            [_page(staff)], {0: CELLO}, {(0, 0, 0): 0}, apply=True,
            treble_override=True, instrument_source_by_slot={0: "label"})
        assert staff["clef"] == "treble"
        assert not any(r["applied"] for r in recs)


# ── OMR_INSTRUMENT_CLEF_DEFAULT: the mid-staff change veto ──────────────────


def _measures(*specs):
    """[(clef, [pitches-as-resolved-under-that-clef]), ...] → measure dicts."""
    out = []
    for i, (clef, pitches) in enumerate(specs):
        out.append({"measure_index": i, "clef": clef, "key_signature": None,
                    "detections": [_notehead(p, (20 + 40 * j, 0, 10, 10))
                                   for j, p in enumerate(pitches)]})
    return out


def _staffm(clef, *specs, staff_index=0):
    return {"staff_index": staff_index, "clef": clef, "key_signature": None,
            "clef_source": "detector", "measures": _measures(*specs)}


class TestMidStaffChangeVeto:
    def test_the_table_holds_only_verified_changes(self):
        assert MID_STAFF_CHANGE_VETOES == {
            ("Violin", "treble", "bass"), ("Viola", "alto", "bass")}

    def test_violin_to_bass_is_vetoed_and_restated(self):
        """brahms-p1 s9 in miniature: clefF 0.32 at m3 flips a violin staff to
        bass for the rest of the line; truth D-family read F-family, −12."""
        staff = _staffm("treble",
                        ("treble", ["D4", "D4"]),
                        ("bass", ["F2", "G2"]),   # as-resolved under the bogus bass
                        ("bass", ["A2"]))
        recs = veto_implausible_clef_changes(
            [_page(staff)], {0: VIOLIN}, {(0, 0, 0): 0}, {0: "label"})
        assert len(recs) == 1 and recs[0]["noteheads_restated"] == 3
        assert [m["clef"] for m in staff["measures"]] == ["treble"] * 3
        assert [d["pitch"] for d in staff["measures"][1]["detections"]] == ["D4", "E4"]
        assert [d["pitch"] for d in staff["measures"][2]["detections"]] == ["F4"]

    def test_viola_to_bass_is_vetoed(self):
        """984073-p1 s9: alto header read correctly, clefF 0.59 at m4."""
        staff = _staffm("alto",
                        ("alto", ["C4"]),
                        ("bass", ["E3"]))
        recs = veto_implausible_clef_changes(
            [_page(staff)], {0: VIOLA}, {(0, 0, 0): 0}, {0: "label"})
        assert recs and staff["measures"][1]["clef"] == "alto"
        # bass → alto is +6: the E3 resolved under the bogus bass returns to D4.
        assert staff["measures"][1]["detections"][0]["pitch"] == "D4"

    def test_viola_to_treble_is_a_real_move_and_stands(self):
        """Violas go to treble for high passages in real engraving; the one
        spurious alto→treble in the pool (575951-p2 s20) is score-order-named
        and thus outside the gate anyway."""
        staff = _staffm("alto", ("alto", ["C4"]), ("treble", ["B4"]))
        recs = veto_implausible_clef_changes(
            [_page(staff)], {0: VIOLA}, {(0, 0, 0): 0}, {0: "label"})
        assert recs == [] and staff["measures"][1]["clef"] == "treble"

    def test_cello_changes_are_never_touched(self):
        staff = _staffm("bass", ("bass", ["C3"]), ("tenor", ["A3"]))
        recs = veto_implausible_clef_changes(
            [_page(staff)], {0: CELLO}, {(0, 0, 0): 0}, {0: "label"})
        assert recs == [] and staff["measures"][1]["clef"] == "tenor"

    def test_score_order_identity_never_drives_a_veto(self):
        staff = _staffm("treble", ("treble", ["D4"]), ("bass", ["F2"]))
        recs = veto_implausible_clef_changes(
            [_page(staff)], {0: VIOLIN}, {(0, 0, 0): 0}, {0: "score_order"})
        assert recs == [] and staff["measures"][1]["clef"] == "bass"

    def test_an_accepted_change_resets_the_carried_clef(self):
        """After a REAL change is accepted, later changes are judged from the
        new clef — a viola that went to treble and then shows bass is now a
        (Viola, treble, bass) triple, which is not in the table."""
        staff = _staffm("alto",
                        ("alto", ["C4"]),
                        ("treble", ["B4"]),
                        ("bass", ["D3"]))
        recs = veto_implausible_clef_changes(
            [_page(staff)], {0: VIOLA}, {(0, 0, 0): 0}, {0: "label"})
        assert recs == [] and staff["measures"][2]["clef"] == "bass"

    def test_clef_final_is_recomputed_after_a_veto(self):
        staff = _staffm("treble", ("treble", ["D4"]), ("bass", ["F2"]))
        staff["clef_final"] = "bass"
        veto_implausible_clef_changes(
            [_page(staff)], {0: VIOLIN}, {(0, 0, 0): 0}, {0: "label"})
        assert "clef_final" not in staff, (
            "every change was vetoed, so the staff ends in its own clef and "
            "the 'final differs' marker must go")


def test_the_env_flag_reaches_direct_contextual_callers(monkeypatch):
    """eval_pipeline_clefs calls apply_contextual_analysis directly, not via
    transcribe's kwargs builder — a None param must resolve from the env so a
    benchmark exercises the same configuration a transcription would."""
    import inspect
    from tools.omr.contextual import apply_contextual_analysis
    sig = inspect.signature(apply_contextual_analysis)
    assert sig.parameters["instrument_clef_default"].default is None


# ── restatement alteration sourcing (the 575951-p1 lesson) ──────────────────
#
# The override restated every letter correctly and OMR-NED still ROSE by 2:
# the staff's own signature read 1 flat, the vote rejected it ("differs from
# the system's 3 flats"), zero was carried — and every restated E/A/B lost the
# flat C minor gives it. An UNREAD signature on a concert-pitch staff now
# takes the system majority among READ staves; read signatures, transposing
# instruments and percussion keep their own.

def _sibling(flats, read=True, staff_index=1):
    return {"staff_index": staff_index, "clef": "treble",
            "key_signature": {"sharps": 0, "flats": flats},
            "key_signature_read": read, "measures": []}


def _viola_treble_A4s(read_key=False):
    staff = _staff(["A4"] * 12, extra=[_clef_det("clefG")],
                   key_signature={"sharps": 0, "flats": 0})
    staff["clef_source"] = "detector"
    staff["key_signature_read"] = read_key
    staff["measures"][0]["key_signature"] = staff["key_signature"]
    return staff


def _page_with_siblings(staff, *siblings):
    return {"page_index": 0,
            "systems": [{"system_index": 0, "staves": [staff, *siblings]}]}


class TestRestatementAlterations:
    def test_unread_signature_takes_the_system_majority(self):
        staff = _viola_treble_A4s(read_key=False)
        page = _page_with_siblings(staff, _sibling(3, staff_index=1),
                                   _sibling(3, staff_index=2))
        correct_clefs_from_instruments(
            [page], {0: VIOLA}, {(0, 0, 0): 0}, apply=True,
            treble_override=True, instrument_source_by_slot={0: "label"})
        # A4 under treble → B3 under alto, and the system's 3 flats flat it.
        assert staff["measures"][0]["detections"][0]["pitch"] == "Bb3"

    def test_a_read_signature_outranks_the_majority(self):
        staff = _viola_treble_A4s(read_key=True)   # its own 0 flats WAS read
        page = _page_with_siblings(staff, _sibling(3, staff_index=1),
                                   _sibling(3, staff_index=2))
        correct_clefs_from_instruments(
            [page], {0: VIOLA}, {(0, 0, 0): 0}, apply=True,
            treble_override=True, instrument_source_by_slot={0: "label"})
        assert staff["measures"][0]["detections"][0]["pitch"] == "B3"

    def test_percussion_never_takes_the_majority(self):
        """Timpani are conventionally written unsigned — the system's flats
        must not be forced onto them."""
        from tools.omr.clef_correction import _restatement_alterations
        TIMPANI = lookup("Pauken").instrument
        staff = {"staff_index": 0, "key_signature": {"sharps": 0, "flats": 0},
                 "key_signature_read": False, "measures": []}
        siblings = [_sibling(3, staff_index=1), _sibling(3, staff_index=2)]
        assert _restatement_alterations(
            staff, [staff, *siblings], TIMPANI) is None

    def test_a_transposing_staff_keeps_its_own(self):
        from tools.omr.clef_correction import _restatement_alterations
        CLARINET = lookup("Cl.").instrument
        assert CLARINET.chromatic != 0
        staff = {"staff_index": 0, "key_signature": {"sharps": 0, "flats": 0},
                 "key_signature_read": False, "measures": []}
        assert _restatement_alterations(
            staff, [staff, _sibling(3, staff_index=1)], CLARINET) is None

    def test_no_read_siblings_means_no_opinion(self):
        from tools.omr.clef_correction import _restatement_alterations
        staff = {"staff_index": 0, "key_signature": {"sharps": 0, "flats": 0},
                 "key_signature_read": False, "measures": []}
        assert _restatement_alterations(
            staff, [staff, _sibling(3, read=False, staff_index=1)], VIOLA) is None
