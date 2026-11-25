"""ROADMAP 2.344 (Sean 2026-11-24, DECISIONS "AN ARC BETWEEN THE SAME NOTES IS A TIE, PRINTED ACCIDENTAL OR NOT"). STAGED ADJUDICATE `arc_kind`.

    "That is definitely a tie. Those are the same notes. The rule should be as simple as the same notes. And if the tie carries over to the next
    measure, there may or may not be an accidental but if there is not one, it is implied."

WHY THE OLD RULE EXISTED (2.75, 2026-10-09): two notes at one staff position are one PITCH only if no accidental changes it (C then C-sharp under a slur is
one position, two pitches), and ADJUDICATE could not say what a printed accidental said -- so a printed accidental on the stop "had no opinion" and the
detector's class stood (a slur, where the detector drew the half-arc of a tie as one). It was quiet while the fused naturals were unread (2.336 made both read).

THE CONTROL is the REAL case (fixture `data/rule_tie_same_notes_2_344.json`: the GATHER rows of Litolff p6 system 1 staff 11, bars 160-161 = cells 2-3, copied
unchanged from the 20261123-night slice): both half notes carry a natural, the arc between them is read as a slur. It fails with `OMR_ARC_TIE_SAME_NOTES=0`.
THE NEVER: the same real rows with the stop's printed accidental changed to a sharp (one fact changed; the five sample pages hold no real slur with a
pitch-changing accidental at its stop) stays a slur; a stop accidental with NO printed accidental on the start stays as it was (no opinion).
"""
import copy
import json
import os

import pytest

from tools.omr.staged import arc_claim as AC
from tools.omr.staged.review import rerun as RR

with open(os.path.join(os.path.dirname(__file__), "data", "rule_tie_same_notes_2_344.json")) as _f:
    FX = json.load(_f)

PIECES = ("glyph/6/1/11/2/1", "glyph/6/1/11/3/4")         # the two cells' pieces of the one printed arc
HEAD_A, HEAD_B = "glyph/6/1/11/2/4", "glyph/6/1/11/3/1"
ACC_A, ACC_B = "glyph/6/1/11/2/360000", "glyph/6/1/11/3/360000"


def _run(monkeypatch, on, edit=None):
    monkeypatch.setenv(AC.ENV_TIE_SAME_NOTES, "1" if on else "0")
    rows = copy.deepcopy(FX["observations"])
    if edit:
        edit(rows)
    log, _ = RR.rebuild_gather({"observations": rows, "abstentions": copy.deepcopy(FX["abstentions"]), "verdicts": []})
    RR.run_stages(log)
    return {(v["quantity"], v["subject"]): v for v in log.to_json()["verdicts"]}


def _kinds(vs):
    return [vs[("arc_kind", p)]["value"] for p in PIECES]


def _set_alteration(subject, alteration):
    def edit(rows):
        hit = 0
        for r in rows:
            if r["subject"] == subject and r["quantity"] == "accidental_staff_position":
                r["detail"]["alteration"] = alteration
                hit += 1
        assert hit == 1
    return edit


def _drop_accidental(subject):
    def edit(rows):
        rows[:] = [r for r in rows if r["subject"] != subject]
    return edit


def test_the_control_can_fail_the_old_reading_was_a_slur(monkeypatch):
    vs = _run(monkeypatch, on=False)
    assert _kinds(vs) == ["slur", "slur"]
    assert vs[("accidental_owner", ACC_A)]["value"] == HEAD_A and vs[("accidental_owner", ACC_B)]["value"] == HEAD_B
    assert vs[("accidental_owner", ACC_A)]["detail"]["alteration"] == "natural"


def test_real_naturals_on_both_half_notes_make_the_arc_a_tie(monkeypatch):
    vs = _run(monkeypatch, on=True)
    assert _kinds(vs) == ["tie", "tie"]
    for p in PIECES:
        assert vs[("arc_kind", p)]["detail"]["grammar"]["page_binding"]["rule"] == "page_binding_same_pitch_restated"
        assert vs[("tie_pair", p)]["value"] == {"start": HEAD_A, "stop": HEAD_B}


def test_never_a_tie_where_the_stop_accidental_changes_the_pitch(monkeypatch):
    vs = _run(monkeypatch, on=True, edit=_set_alteration(ACC_B, "sharp"))
    assert _kinds(vs) == ["slur", "slur"]
    assert vs[("arc_kind", PIECES[0])]["detail"]["grammar"]["page_binding"]["rule"] == "page_binding_pitch_changed_by_accidental"
    assert vs[("tie_pair", PIECES[0])]["outcome"] != "decided"


def test_no_accidental_printed_on_the_start_is_no_opinion_the_old_behaviour_stands(monkeypatch):
    # ROUND 1's boundary: with round 2 (`OMR_ARC_TIE_SAME_SOUNDING`, `test_tie_same_sounding_2_344_r2.py`) off, a start with no printed accidental is no opinion. With it ON that
    # case waits for what the two notes sound (EVALUATE) and is no longer the detector's class.
    monkeypatch.setenv(AC.ENV_TIE_SAME_SOUNDING, "0")
    on = _run(monkeypatch, on=True, edit=_drop_accidental(ACC_A))
    off = _run(monkeypatch, on=False, edit=_drop_accidental(ACC_A))
    assert _kinds(on) == _kinds(off)


def test_the_flag_off_is_the_old_behaviour_even_for_a_changed_pitch(monkeypatch):
    vs = _run(monkeypatch, on=False, edit=_set_alteration(ACC_B, "sharp"))
    assert _kinds(vs) == ["slur", "slur"]
