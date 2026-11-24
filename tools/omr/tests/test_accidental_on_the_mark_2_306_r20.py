"""ROADMAP 2.306 r20 -- AN ACCIDENTAL BELONGS TO THE NOTE IT STANDS BEFORE, whichever box the detector read the note with
(STAGED EVALUATE `consequences.apply_printed_accidental`, flag `OMR_ACCIDENTAL_ON_THE_MARK`, default OFF).
NEVER: never to another staff's view of the same ink, never to a box another identity grouped, never to a box whose pitch differs.

Control from the REAL record rows of Litolff 6/0/1/12 (fixture `accidental_on_the_mark_2_306_r20.json`, cut from the r20 merged-tree
gather): a sharp before an F5 half whose head is boxed twice (one `page_head` mark). The sharp's owner is the less confident box; EXPORT
writes the more confident one (one mark, one note, 2.58b); the in-bar carry skips it because it stands at the SAME x, not to the right.
So the written note was F5 with the sharp printed in front of it -- the fault the stem reader's ON arm exposed by making the bar plain.
The control fails with the flag off (the old code).
"""
from __future__ import annotations

import json
import os

import pytest

from tools.omr.staged import adjudicate, evaluate, export as E
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import consequences as C
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q

FX = os.path.join(os.path.dirname(__file__), "fixtures", "accidental_on_the_mark_2_306_r20.json")
REAL = "6/0/1/12"
CELL = R.cell(0, 0, 0, 0)
STAFF = R.staff(0, 0, 0)


def _here(key: str) -> str:
    return key.replace(REAL, "0/0/0/0")


def _log(edit=None) -> Log:
    rows = json.load(open(FX))["rows"]
    if edit:
        rows = edit(json.loads(json.dumps(rows)))
    log = Log()
    for r in rows:
        det = dict(r["detail"])
        if "members" in det:
            det["members"] = [_here(m) for m in det["members"]]
        if "rep" in det:
            det["rep"] = _here(det["rep"])
        sub = R.Subject.from_key(_here(r["subject"]))
        v = r["value"]
        if r["quantity"] == "glyph_box":
            v = tuple(v)
        log.observe(sub, r["quantity"], v, reader=r["reader"], frame="cell:0", **det)
    for gi in ("5", "6"):
        log.record(R.Verdict(id=log._next_id("vrd"), subject=R.Subject.from_key("glyph/0/0/0/0/" + gi), quantity=Q.DURATION,
                             outcome=R.Outcome.DECIDED, value={"beats": 2.0, "written": 2.0, "dots": 0}, decider="t", reason="fixture"))
    log.freeze()
    adjudicate.run(log, order=(Q.ACCIDENTAL_OWNER,))
    for q, v in ((Q.CLEF, "treble"), (Q.KEY_SIGNATURE, -3), (Q.MEASURE_PARTITION, 1)):
        log.record(R.Verdict(id=log._next_id("vrd"), subject=STAFF, quantity=q, outcome=R.Outcome.DECIDED, value=v, decider="t", reason="fixture"))
    log.record(R.Verdict(id=log._next_id("vrd"), subject=R.system(0, 0), quantity=Q.SYSTEM_STAFF_COUNT, outcome=R.Outcome.DECIDED, value=1,
                         decider="t", reason="fixture"))
    log.record(R.Verdict(id=log._next_id("vrd"), subject=R.DOCUMENT, quantity=Q.PART_PARTITION, outcome=R.Outcome.DECIDED,
                         value={"join": "ordinal", "staves_per_system": 1}, decider="t", reason="ordinal"))
    evaluate.run(log)
    return log


def _written(log):
    xml, report = E.to_musicxml({"record": log.to_json(), "summary": log.summary()})
    return xml


def test_real_mark_the_owner_is_the_box_that_is_not_written():
    """The cause, as the real rows stand: the sharp owns box 6, box 5 is the mark's more confident box."""
    log = _log()
    owner = [v for v in log.to_json()["verdicts"] if v["quantity"] == "accidental_owner" and v["outcome"] == "decided"]
    assert [v["value"] for v in owner] == ["glyph/0/0/0/0/6"]


def test_real_mark_the_written_f5_half_carries_its_sharp(monkeypatch):
    monkeypatch.setenv(C.ACCIDENTAL_ON_THE_MARK_ENV, "1")
    xml = _written(_log())
    assert xml.count("<note") == 1                      # one mark, one note
    assert "<step>F</step>" in xml and "<alter>1</alter>" in xml and "<octave>5</octave>" in xml
    assert "<accidental>sharp</accidental>" in xml


def test_control_with_the_rule_off_the_sharp_is_lost(monkeypatch):
    """The control that fails on the old code: F5 written with no alteration."""
    monkeypatch.setenv(C.ACCIDENTAL_ON_THE_MARK_ENV, "0")
    xml = _written(_log())
    assert xml.count("<note") == 1
    assert "<alter>1</alter>" not in xml and "<accidental>sharp</accidental>" not in xml


def _members_of(log, key):
    head = R.Subject.from_key(key)
    return [m.to_key() for m in C._boxes_of_the_same_head(log, head, log.verdict(Q.PITCH, head).value)]


def test_the_other_box_of_the_same_head_is_found(monkeypatch):
    monkeypatch.setenv(C.ACCIDENTAL_ON_THE_MARK_ENV, "1")
    assert _members_of(_log(), "glyph/0/0/0/0/6") == ["glyph/0/0/0/0/5"]


def test_never_a_box_whose_pitch_differs(monkeypatch):
    monkeypatch.setenv(C.ACCIDENTAL_ON_THE_MARK_ENV, "1")

    def move(rows):
        for r in rows:
            if r["subject"].endswith("/5") and r["quantity"] == "notehead_staff_position":
                r["value"], r["detail"]["rounded"] = 1.9, 2           # a step lower: another pitch
        return rows
    assert _members_of(_log(move), "glyph/0/0/0/0/6") == []


def test_never_a_box_another_identity_grouped(monkeypatch):
    monkeypatch.setenv(C.ACCIDENTAL_ON_THE_MARK_ENV, "1")

    def other(rows):
        for r in rows:
            if r["quantity"] == "mark_group":
                r["detail"]["identity"] = "overlap"
        return rows
    assert _members_of(_log(other), "glyph/0/0/0/0/6") == []


def test_never_another_staffs_view_of_the_ink(monkeypatch):
    monkeypatch.setenv(C.ACCIDENTAL_ON_THE_MARK_ENV, "1")

    def cross(rows):
        for r in rows:
            if r["quantity"] == "mark_group" and "members" in r["detail"]:
                r["detail"]["members"] = [m.replace("6/0/1/12/5", "6/0/2/12/5") for m in r["detail"]["members"]]
        return rows
    assert _members_of(_log(cross), "glyph/0/0/0/0/6") == []
