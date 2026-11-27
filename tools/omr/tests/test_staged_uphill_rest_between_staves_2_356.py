"""ROADMAP 2.356 -- a whole-movement run stopped at Brahms p21 with `UphillConsequence` (STAGED ADJUDICATE `rhythm._bar_lengths_for`,
EVALUATE `consequences.reinstate_rest_between_staves`).

CAUSE: since 2.346 (`OMR_BAR_SUM_SKIPS_REFUSED`, default ON) the meter's bar sum asks each box's not-a-rest refusal, so a refusal
enters the METER verdict's basis. `reinstate_rest_between_staves` takes the meter as its cause and overturns one of those same
refusals -- meter -> rest -> meter, the fixpoint `Log.record` refuses. The dependency that should not exist is the meter's read of
a refusal that a meter-caused rule may overturn (the whole-rest precedent in `_corroborate`: a bar whose content the meter may
rewrite cannot corroborate that meter). FIX: a bar holding a rest contested with another staff (GATHER rows: `Q.REST` +
`Q.GLYPH_BAND_DISTANCE` naming another staff) is left out of the meter's bar sum before anything in it is asked.

CONTROL FROM REAL ROWS (CLAUDE.md rule 7): `fixtures/uphill_rest_between_staves_2_356_brahms_p21_s0.json` -- the rows of Brahms
system/21/0 as the 20261123-night record filed them, and the carry source's meter (system/1/0). The real meter decision runs on
them, then the real rule on glyph/21/0/4/1/2 (a rest8th about two spaces under staff 4, refused `rest_outside_its_staff`, contested
with staff 5). Old behaviour (the helper answering "not contested", i.e. main): RAISES. Fixed: the meter is still DECIDED carried
6/8 without reading the refusal, and the rest is reinstated as staff 4's missing second-voice eighth (the trace's look agrees; the
rule's own conclusion is unchanged -- only the cycle is gone).

NEVERS: an uncontested refused rest still leaves its bar (2.346 unchanged); a contested NOTEHEAD takes no bar out; flag off the
contested bar is summed exactly as before.
"""
from __future__ import annotations

import json
import os
import pathlib
import unittest
from unittest import mock

from tools.omr.staged import adjudicate, consequences
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged.adjudicate import Candidate
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import Kind, Log, Outcome, Q, Subject, UphillConsequence, Verdict

FIX = pathlib.Path(__file__).parent / "fixtures" / "uphill_rest_between_staves_2_356_brahms_p21_s0.json"
ENV = rhythm.BAR_SUM_SKIPS_REFUSED_ENV
SYSTEM = Subject.from_key("system/21/0")
REST = Subject.from_key("glyph/21/0/4/1/2")
ON = {ENV: "1", "OMR_NARROWED_BAR_LENGTH_UNKNOWN": "1"}


def _real_log():
    fx = json.loads(FIX.read_text())
    log = Log()
    basis_of: dict = {}
    for o in fx["observations"]:
        row = log.observe(Subject.from_key(o["subject"]), o["quantity"], o["value"], reader=o["reader"], frame=o["frame"],
                          **o["detail"])
        if o.get("basis_of"):           # the carry source's own template readings, its meter's basis
            basis_of.setdefault(o["basis_of"], []).append(row.id)
    for v in fx["verdicts"]:
        b = tuple(basis_of.get(v["subject"], ())) if v["quantity"] == "meter" else ()
        log.record(Verdict(id=log._next_id("vrd"), subject=Subject.from_key(v["subject"]), quantity=v["quantity"],
                           outcome=Outcome(v["outcome"]), value=v["value"], decider="night_record", reason=v["reason"] or "t",
                           candidates=tuple(Candidate(c[0], support=c[1]) for c in v.get("candidates") or ()),
                           considered=b, basis=b, detail=v.get("detail") or {}))
    log.freeze()
    adjudicate._ensure_decisions()
    return log


def _meter(log):
    with mock.patch.dict(os.environ, ON, clear=False):
        return adjudicate.adjudicate_one(log, adjudicate.REGISTRY[Q.METER], SYSTEM)


def _refusal(log):
    return log.verdict(Q.REST_IS_NOT_A_REST, REST)


class TestRealP21(unittest.TestCase):

    def test_the_fixture_is_the_traced_case(self):
        log = _real_log()
        r = _refusal(log)
        self.assertEqual((r.outcome, r.value, r.reason), (Outcome.DECIDED, True, "rest_outside_its_staff"))
        cands = {x.detail.get("candidate") for x in log.rows(Q.GLYPH_BAND_DISTANCE, REST)}
        self.assertIn("staff/21/0/5", cands)

    def test_old_reading_RAISES_uphill(self):
        """The control that can fail: with the contest test answering "no" (main's bar sum), the meter reads the refusal and the
        rule stands on its own conclusion."""
        log = _real_log()
        with mock.patch.object(rhythm, "_rest_contested_between_staves", lambda *a, **k: False):
            meter = _meter(log)
        self.assertIs(meter.outcome, Outcome.DECIDED)
        self.assertIn(_refusal(log).id, meter.considered)
        with mock.patch.dict(os.environ, ON, clear=False):
            with self.assertRaises(UphillConsequence):
                consequences.reinstate_rest_between_staves(log, REST, meter)

    def test_fixed_the_meter_never_reads_the_refusal_and_the_rest_is_reinstated(self):
        log = _real_log()
        meter = _meter(log)
        self.assertIs(meter.outcome, Outcome.DECIDED)
        self.assertEqual((meter.value["numerator"], meter.value["denominator"]), (6, 8))
        refusal = _refusal(log)
        self.assertNotIn(refusal.id, log.closure(meter.id))
        with mock.patch.dict(os.environ, ON, clear=False):
            out = consequences.reinstate_rest_between_staves(log, REST, meter)
        self.assertEqual(len(out), 1)
        self.assertEqual((out[0].value, out[0].reason, out[0].supersedes), (False, "rest_reinstated_missing_voice", refusal.id))
        self.assertEqual(out[0].detail["candidate"], "staff/21/0/5")

    def test_invariant_no_contested_rest_refusal_in_the_meter_basis(self):
        """The invariant the fix establishes, over the whole real system: the meter's basis holds no refusal of any rest that
        `reinstate_rest_between_staves` could overturn (refused `rest_outside_its_staff`, contested with another staff)."""
        log = _real_log()
        meter = _meter(log)
        closure = log.closure(meter.id)
        rewritable = []
        for v in log.verdicts(Q.REST_IS_NOT_A_REST, SYSTEM, scope=R_SCOPE):
            own = v.subject.at(Kind.STAFF).to_key()
            if any(r.detail.get("candidate") != own for r in log.rows(Q.GLYPH_BAND_DISTANCE, v.subject)):
                rewritable.append(v.id)
        self.assertTrue(rewritable)
        self.assertEqual([i for i in rewritable if i in closure], [])


from tools.omr.staged.record import Scope  # noqa: E402
R_SCOPE = Scope.SELF_AND_DESCENDANTS


class TestNevers(unittest.TestCase):

    def _bar(self, *, contested_rest=False, contested_head=False, refused_rest=True):
        log = Log()
        cell = Subject.from_key("cell/0/0/0/0")
        rest = Subject.from_key("glyph/0/0/0/0/2")
        head = Subject.from_key("glyph/0/0/0/0/1")
        log.observe(rest, Q.REST, "rest8th", reader="detector", frame="page")
        for g, contested in ((rest, contested_rest), (head, contested_head)):
            log.observe(g, Q.GLYPH_BAND_DISTANCE, 1.0, reader="geometry", frame="page", candidate="staff/0/0/0", own=True)
            if contested:
                log.observe(g, Q.GLYPH_BAND_DISTANCE, 3.0, reader="geometry", frame="page", candidate="staff/0/0/1", own=False)

        def put(sub, q, val, out=Outcome.DECIDED, reason="t"):
            log.record(Verdict(id=log._next_id("vrd"), subject=sub, quantity=q, outcome=out, value=val, decider="t", reason=reason))
        put(head, Q.DURATION, {"beats": 1.0, "written": 1.0, "dots": 0})
        put(rest, Q.DURATION, {"beats": 0.5, "written": 0.5, "dots": 0, "is_rest": True})
        put(rest, Q.REST_IS_NOT_A_REST, refused_rest, reason="rest_outside_its_staff" if refused_rest else "rest")
        put(cell, Q.EVENT, {"events": [{"glyphs": [1], "x": 1.0}, {"glyphs": [2], "x": 2.0}]})
        log.freeze()
        adjudicate._ensure_decisions()
        return log, adjudicate.Evidence(log, Subject.from_key("system/0/0"), adjudicate.REGISTRY[Q.METER])

    def _len(self, ev, on=True):
        with mock.patch.dict(os.environ, {ENV: "1" if on else "0"}, clear=False):
            return rhythm._bar_lengths_for(ev).get(0)

    def test_an_uncontested_refused_rest_still_leaves_its_bar(self):
        _, ev = self._bar()
        self.assertEqual(self._len(ev), [1.0])                 # 2.346 unchanged

    def test_a_contested_rest_takes_its_bar_out_and_its_refusal_is_never_asked(self):
        log, ev = self._bar(contested_rest=True)
        self.assertIsNone(self._len(ev))
        refusal = log.verdict(Q.REST_IS_NOT_A_REST, Subject.from_key("glyph/0/0/0/0/2"))
        self.assertNotIn(refusal.id, ev._seen)

    def test_a_contested_head_takes_no_bar_out(self):
        _, ev = self._bar(contested_head=True)
        self.assertEqual(self._len(ev), [1.0])

    def test_a_contested_rest_kept_on_its_staff_still_takes_the_bar_out(self):
        """Cannot tell from GATHER rows whether the refusal stands, so the bar is silent (never read either way)."""
        _, ev = self._bar(contested_rest=True, refused_rest=False)
        self.assertIsNone(self._len(ev))

    def test_flag_off_the_contested_bar_is_summed_as_before(self):
        _, ev = self._bar(contested_rest=True)
        self.assertEqual(self._len(ev, on=False), [1.5])


if __name__ == "__main__":
    unittest.main()
