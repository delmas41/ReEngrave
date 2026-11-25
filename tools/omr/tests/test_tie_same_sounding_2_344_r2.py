"""ROADMAP 2.344 round 2 (Sean 2026-11-24, DECISIONS "AN ARC BETWEEN THE SAME NOTES IS A TIE, PRINTED ACCIDENTAL OR NOT"): "the same notes" in full.

    "The rule should be as simple as the same notes. And if the tie carries over to the next measure, there may or may not be an accidental but if there is not one, it is implied."

Round 1 (`test_tie_same_notes_2_344.py`) decided only where BOTH notes print an accidental. Round 2 -- STAGED ADJUDICATE `arc_kind` (`ownership._two_note_reading`, `_page_binding`) and STAGED EVALUATE
`consequences.settle_arc_by_sounding` -- covers the rest:

  (b) the start prints one, the stop none (across a barline)  -> a tie: the tie carries it (decided in ADJUDICATE; the page-binding path always did).
  (a) the stop prints one, the start none                      -> what each note SOUNDS decides, and that is filed at EVALUATE (the key, an earlier accidental in the bar): the same
                                                                  sounding pitch is a tie (a courtesy accidental), a different one a slur. ADJUDICATE says `same_pitch_awaits_sounding`.
  (c) an accidental glyph nobody read, or a key nobody read   -> nothing is decided; the detector's class is NOT the answer.

THE CONTROLS ARE REAL ROWS (fixtures cut, unchanged, from the 20261123-night Litolff record's GATHER rows, the staff's own rows plus its bar 0 (key) and the two bars of the arc):
  `rule_tie_sounding_p3s6_2_344_r2.json`  Litolff p3 system 1 staff 6 bars 10-11: E4 under a 3-flat key (no printed accidental), then a printed NATURAL on E4 under one arc -- the pitch
                                          CHANGES (E-flat to E-natural): a slur, and the NEVER-case (never a tie between different sounding pitches). Written as a slur today by the
                                          detector's class, which here is right; it is the control that the rule does not call it a tie.
  `rule_tie_carried_p1s3_2_344_r2.json`   Litolff p1 system 0 staff 3 bars 10-11: B3 with a printed natural, then B3 with none, under one arc across the barline (key: 3 flats). A slur by the
                                          detector's class today; the tie carries the natural, so the notes are the same: a tie.
  `rule_tie_unread_p7s9_2_344_r2.json`    Litolff p7 system 0 staff 9: an arc whose stop has an accidental-shaped glyph nobody read; the old rule wrote the class (a tie) with it unread.
The courtesy tie (a printed accidental on the stop that says what the start already sounds) has NO real case in the 20261123-night Litolff movement (all six (a) arcs change the pitch), so
its control is the p3 s6 rows with ONE fact changed: the stop's printed alteration is the key's flat instead of the natural -- stated here, not drawn from the page.
"""
import copy
import json
import os

import pytest

from tools.omr.staged import arc_claim as AC
from tools.omr.staged import consequences as CQ
from tools.omr.staged import evaluate as EV
from tools.omr.staged import export as EXP
from tools.omr.staged.record import Q
from tools.omr.staged.review import rerun as RR

DATA = os.path.join(os.path.dirname(__file__), "data")


def _fx(name):
    with open(os.path.join(DATA, name)) as f:
        return json.load(f)


P3 = _fx("rule_tie_sounding_p3s6_2_344_r2.json")
P1 = _fx("rule_tie_carried_p1s3_2_344_r2.json")
P7 = _fx("rule_tie_unread_p7s9_2_344_r2.json")

P3_PIECES = ("glyph/3/1/6/10/0", "glyph/3/1/6/11/3")            # the two cells' pieces of the one printed arc
P3_START, P3_STOP = "glyph/3/1/6/10/1", "glyph/3/1/6/11/0"
P3_ACC_STOP = "glyph/3/1/6/11/360000"
P1_PIECES = ("glyph/1/0/3/10/0", "glyph/1/0/3/11/6")
P1_START, P1_STOP = "glyph/1/0/3/10/1", "glyph/1/0/3/11/1"
P7_UNREAD = ("glyph/7/0/9/11/8", "glyph/7/0/9/12/8")


def _run(monkeypatch, fx, on, edit=None):
    monkeypatch.setenv(AC.ENV_TIE_SAME_SOUNDING, "1" if on else "0")
    rows = copy.deepcopy(fx["observations"])
    if edit:
        edit(rows)
    log, _ = RR.rebuild_gather({"observations": rows, "abstentions": copy.deepcopy(fx["abstentions"]), "verdicts": []})
    RR.run_stages(log)
    vs = log.to_json()["verdicts"]
    superseded = {v["supersedes"] for v in vs if v.get("supersedes")}
    return {(v["quantity"], v["subject"]): v for v in vs if v["id"] not in superseded}


def _kinds(vs, pieces):
    return [vs[("arc_kind", p)]["value"] for p in pieces]


def _set_alteration(subject, alteration):
    def edit(rows):
        hit = [r for r in rows if r["subject"] == subject and r["quantity"] == "accidental_staff_position"]
        assert len(hit) == 1
        hit[0]["detail"]["alteration"] = alteration
    return edit


def _drop_key(rows):
    rows[:] = [r for r in rows if not r["quantity"].startswith("keysig")
               and not (r["quantity"] == "accidental_staff_position" and r["subject"].startswith("glyph/3/1/6/0/"))]


# ── (a) the stop prints one, the start none: what each SOUNDS decides ────────────────────────────────────────────────────────────────────────────────

def test_the_control_can_fail_the_old_reading_was_the_detectors_class(monkeypatch):
    vs = _run(monkeypatch, P3, on=False)
    assert _kinds(vs, P3_PIECES) == ["slur", "slur"]
    assert vs[("arc_kind", P3_PIECES[0])]["decider"] == "adjudicate_arc_kind" and vs[("arc_kind", P3_PIECES[0])]["detail"]["detector_class"] == "slur"


def test_never_a_tie_where_the_pitch_changes_real_flat_then_natural(monkeypatch):
    vs = _run(monkeypatch, P3, on=True)
    assert vs[("key_signature", "staff/3/1/6")]["value"] == -3 and vs[("pitch", P3_START)]["value"] == "E4" == vs[("pitch", P3_STOP)]["value"]
    assert vs[("accidental", P3_START)]["value"] == "b" and vs[("accidental", P3_STOP)]["value"] == "natural"        # the key's flat; the printed natural
    assert _kinds(vs, P3_PIECES) == ["slur", "slur"]
    for p in P3_PIECES:
        v = vs[("arc_kind", p)]
        assert v["decider"] == "settle_arc_by_sounding" and v["detail"]["grammar"]["sounding"]["rule"] == "sounding_pitch_changed_by_accidental"
        assert vs[("tie_pair", p)]["outcome"] != "decided"


def test_a_printed_accidental_that_restates_what_the_start_sounds_is_a_courtesy_and_a_tie(monkeypatch):
    # ONE fact changed on the real rows: the stop prints the key's flat instead of a natural
    edit = _set_alteration(P3_ACC_STOP, "b")
    on = _run(monkeypatch, P3, on=True, edit=edit)
    assert _kinds(on, P3_PIECES) == ["tie", "tie"]
    for p in P3_PIECES:
        assert on[("tie_pair", p)]["value"] == {"start": P3_START, "stop": P3_STOP} and on[("tie_pair", p)]["reason"] == "paired_by_page_binding"
        assert on[("arc_kind", p)]["detail"]["grammar"]["sounding"]["start_sounds"] == ["E", 4, "b"]
    off = _run(monkeypatch, P3, on=False, edit=edit)
    assert _kinds(off, P3_PIECES) == ["slur", "slur"]            # the old reading: the class decided, whatever the glyph said


def _log_with_a_run(monkeypatch, edit=None):
    """The real p3 s6 rows through every stage, then ONE page-pass verdict (`Q.PAGE_ARC_BINDING`) recorded by hand whose run names the real two heads and was left awaiting their sounding --
    exactly what `adjudicate_page_arc_binding` files for that arc (the page's own ink rows are not in the fixture)."""
    from tools.omr.staged.record import Outcome, Subject, Verdict
    monkeypatch.setenv(AC.ENV_TIE_SAME_SOUNDING, "1")
    rows = copy.deepcopy(P3["observations"])
    if edit:
        edit(rows)
    log, _ = RR.rebuild_gather({"observations": rows, "abstentions": copy.deepcopy(P3["abstentions"]), "verdicts": []})
    RR.run_stages(log)
    run = {"row": "obs:run", "status": "abstained", "why": "same_pitch_awaits_sounding", "witnesses": list(P3_PIECES),
           "kind_evidence": {"start": P3_START, "stop": P3_STOP, "crosses_barline": True}}
    page = Subject.from_key("page/3")
    v = log.record(Verdict(id=log._next_id("vrd"), subject=page, quantity=Q.PAGE_ARC_BINDING, outcome=Outcome.DECIDED,
                           value={"runs": 1, "written": 0, "abstained": 1, "not_witnessed": 0}, decider="t", reason="none_bound", detail={"runs": [run]}))
    return log, page, v


def test_the_page_pass_run_is_settled_by_what_its_notes_sound(monkeypatch):
    # with the page pass ON a tie or slur is written from its RUN: the real E-flat to E-natural run becomes a WRITTEN slur, never a tie
    log, page, v = _log_with_a_run(monkeypatch)
    (new,) = CQ.settle_page_arc_by_sounding(log, page, v)
    (r,) = new.detail["runs"]
    assert (r["status"], r["kind"], r["start"], r["stop"]) == ("written", "slur", P3_START, P3_STOP) and r["sounds"] == [["E", 4, "b"], ["E", 4, ""]]
    assert new.value["written"] == 1 and new.value["abstained"] == 0 and log.verdict(Q.PAGE_ARC_BINDING, page).id == new.id
    # the courtesy case (one fact changed on the real rows) is a written TIE
    log, page, v = _log_with_a_run(monkeypatch, edit=_set_alteration(P3_ACC_STOP, "b"))
    (new,) = CQ.settle_page_arc_by_sounding(log, page, v)
    assert new.detail["runs"][0]["kind"] == "tie" and new.detail["runs"][0]["status"] == "written"


def test_a_page_pass_run_whose_key_is_unread_stays_unsettled(monkeypatch):
    log, page, v = _log_with_a_run(monkeypatch, edit=_drop_key)
    assert CQ.settle_page_arc_by_sounding(log, page, v) == []
    assert log.verdict(Q.PAGE_ARC_BINDING, page).id == v.id


def test_a_key_nobody_read_decides_nothing(monkeypatch):
    # the start prints nothing, so what it sounds is the KEY's alteration; with the key unread the arc is neither kind
    vs = _run(monkeypatch, P3, on=True, edit=_drop_key)
    assert vs[("key_signature", "staff/3/1/6")]["outcome"] != "decided"
    for p in P3_PIECES:
        v = vs[("arc_kind", p)]
        assert v["outcome"] == "abstained" and v["reason"] == "same_pitch_awaits_sounding"
        assert vs[("tie_pair", p)]["outcome"] != "decided"


# ── (b) the stop prints none, the start prints one: the tie carries it ─────────────────────────────────────────────────────────────────────────────

def test_the_real_carried_accidental_was_a_slur_and_is_a_tie(monkeypatch):
    off = _run(monkeypatch, P1, on=False)
    assert _kinds(off, P1_PIECES) == ["slur", "slur"]
    on = _run(monkeypatch, P1, on=True)
    assert _kinds(on, P1_PIECES) == ["tie", "tie"]
    for p in P1_PIECES:
        assert on[("tie_pair", p)]["value"] == {"start": P1_START, "stop": P1_STOP}
        assert on[("arc_kind", p)]["detail"]["grammar"]["tie_slur_rule"]["rule"] == "two_notes_same_pitch_carried"


# ── (c) an accidental nobody read: the class is not the answer ─────────────────────────────────────────────────────────────────────────────────────

def test_an_unread_accidental_glyph_abstains_where_the_class_used_to_write_a_tie(monkeypatch):
    off = _run(monkeypatch, P7, on=False)
    assert [off[("arc_kind", p)]["value"] for p in P7_UNREAD] == ["tie", "tie"]
    on = _run(monkeypatch, P7, on=True)
    for p in P7_UNREAD:
        v = on[("arc_kind", p)]
        assert v["outcome"] == "abstained" and v["reason"] == "same_pitch_accidental_unread"
    # the same printed arc's other pieces, bound by the page pass, are untouched: it is still written once
    assert on[("arc_kind", "glyph/7/0/9/11/3")]["value"] == "tie" and on[("tie_pair", "glyph/7/0/9/11/3")]["outcome"] == "decided"


# ── the rule's own wiring ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_the_rule_runs_downhill_after_the_rules_that_file_a_notes_pitch():
    EV.check_downhill(Q.ARC_KIND, Q.TIE_PAIR)
    order = [r.consequence for r in EV.execution_order()]
    me = order.index(EV.Consequence.SETTLE_ARC_BY_SOUNDING)
    for earlier in (EV.Consequence.RESTATE_PITCH, EV.Consequence.RESPELL_ACCIDENTAL, EV.Consequence.MOVE_GLYPH, EV.Consequence.APPLY_PRINTED_ACCIDENTAL):
        assert order.index(earlier) < me


class _Rec:
    def __init__(self, decided):
        self.decided = decided

    def verdict(self, quantity, subject):
        return self.decided.get(subject)


def test_an_unsettled_run_is_marked_unread_and_a_settled_one_is_not(monkeypatch):
    monkeypatch.setenv(AC.ENV_TIE_SAME_SOUNDING, "1")
    run = {"row": "obs:1", "status": "abstained", "why": "same_pitch_awaits_sounding", "witnesses": ["glyph/3/1/6/10/0"],
           "kind_evidence": {"start": "glyph/3/1/6/10/1", "stop": "glyph/3/1/6/11/0"}}
    other = {"row": "obs:2", "status": "abstained", "why": "end_unbound", "witnesses": ["glyph/3/1/6/4/0"], "kind_evidence": {"start": "a", "stop": "b"}}
    out = EXP._kind_unread_same_pitch_runs(_Rec({}), {"runs": [run, other]})["runs"]
    assert out[0]["kind_unread"] is True and out[0]["start"] == "glyph/3/1/6/10/1" and out[0]["stop"] == "glyph/3/1/6/11/0"
    assert "kind_unread" not in out[1]
    settled = _Rec({"glyph/3/1/6/10/0": {"outcome": "decided", "value": "slur"}})
    assert "kind_unread" not in EXP._kind_unread_same_pitch_runs(settled, {"runs": [run]})["runs"][0]
