"""ROADMAP 2.19 -- `size_measure_rest` counts only what is still IN the bar.

CLAUDE.md §10: a whole rest means the BAR whatever the meter. The EVALUATE
rule that marks it (`consequences.size_measure_rest`) fires only where the
rest is the cell's ONE standing duration, so that a bar holding anything
else is never inflated. Until 2.19 "anything else" included glyphs a DECIDED
verdict had already taken out of the bar -- a notehead box refused as
`not_a_notehead` (the width floor, a clipped fragment), a rest box refused as
a duplicate of the very rest being sized (2.15), a head the ownership contest
gave to the neighbouring staff. EXPORT never writes any of those, so the bar
held ONE whole rest, the rule declined to mark it, 2.8 summed it as four
quarters against the meter and held the bar out. On Breitkopf p1 (FINDINGS
§15) that is the shape of every whole-rest bar in system 0.

The positive controls (a lone rest fires; the rule still refuses a real note,
a narrowed note, an abstained rest, an abstained refusal, a head its own
staff kept, and a missing meter) pass on both sides of the change; the four
`*_LEFT_THE_BAR` tests are RED on the unrepaired tree.
"""
from __future__ import annotations

import unittest

from tools.omr.staged import consequences
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, Verdict

CELL = R.cell(0, 0, 1, 3)
OTHER_STAFF = R.staff(0, 0, 2).to_key()
OWN_STAFF = R.staff(0, 0, 1).to_key()


def _v(log, sub, q, outcome, value, reason="t", detail=None, candidates=()):
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=sub, quantity=q, outcome=outcome,
        value=value, decider="test", reason=reason, detail=detail or {},
        candidates=candidates))


def _whole_rest(log, g=0):
    sub = R.glyph(0, 0, 1, 3, g)
    _v(log, sub, Q.DURATION, Outcome.DECIDED,
       {"beats": 4.0, "written": 4.0, "dots": 0, "is_rest": True},
       reason="rest_class", detail={"rest": "restWhole"})
    return sub


def _quarter_head(log, g):
    sub = R.glyph(0, 0, 1, 3, g)
    _v(log, sub, Q.DURATION, Outcome.DECIDED,
       {"beats": 1.0, "written": 1.0, "dots": 0}, reason="head_and_marks")
    return sub


def _meter(log, num=6, den=8):
    return _v(log, R.system(0, 0), Q.METER, Outcome.DECIDED,
              {"numerator": num, "denominator": den, "raw": f"{num}/{den}"})


def _fire(log, meter):
    return consequences.size_measure_rest(log, CELL, meter)


class TestTheRuleStillDoesWhatItDid(unittest.TestCase):
    """Positive and negative controls: GREEN before and after 2.19."""

    def test_a_lone_whole_rest_is_the_bar(self):
        log = Log()
        rest = _whole_rest(log)
        out = _fire(log, _meter(log))
        self.assertEqual(len(out), 1)
        now = log.verdict(Q.DURATION, rest)
        self.assertTrue(now.value["measure_rest"])
        self.assertEqual(now.value["beats"], 3.0)

    def test_a_real_note_beside_it_keeps_the_bar_unsized(self):
        log = Log()
        _whole_rest(log)
        _quarter_head(log, 1)
        self.assertEqual(_fire(log, _meter(log)), [])

    def test_a_NARROWED_note_beside_it_keeps_the_bar_unsized(self):
        """A head we could not time is still a head: the bar is not silent."""
        log = Log()
        _whole_rest(log)
        from tools.omr.staged.record import Candidate
        _v(log, R.glyph(0, 0, 1, 3, 1), Q.DURATION, Outcome.NARROWED, None,
           reason="beams_ambiguous",
           candidates=(Candidate({"beats": 0.5}, 2.0),
                       Candidate({"beats": 0.25}, 1.0)))
        self.assertEqual(_fire(log, _meter(log)), [])

    def test_an_ABSTAINED_rest_beside_it_keeps_the_bar_unsized(self):
        """Rule 8: a rest box we could not read may be a second voice's rest.
        Nothing DECIDED says it is not in the bar."""
        log = Log()
        _whole_rest(log)
        _v(log, R.glyph(0, 0, 1, 3, 1), Q.DURATION, Outcome.ABSTAINED, None,
           reason="rest_stands_where_no_rest_hangs")
        self.assertEqual(_fire(log, _meter(log)), [])

    def test_an_ABSTAINED_not_a_notehead_verdict_removes_nothing(self):
        log = Log()
        _whole_rest(log)
        head = _quarter_head(log, 1)
        _v(log, head, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Outcome.ABSTAINED, None,
           reason="no_evidence")
        self.assertEqual(_fire(log, _meter(log)), [])

    def test_a_head_its_OWN_staff_kept_is_still_in_the_bar(self):
        log = Log()
        _whole_rest(log)
        head = _quarter_head(log, 1)
        _v(log, head, Q.GLYPH_OWNER, Outcome.DECIDED, OWN_STAFF,
           reason="no_contest")
        self.assertEqual(_fire(log, _meter(log)), [])

    def test_no_meter_no_assertion(self):
        log = Log()
        _whole_rest(log)
        undecided = _v(log, R.system(0, 0), Q.METER, Outcome.ABSTAINED, None,
                       reason="carry_not_corroborated")
        self.assertEqual(_fire(log, undecided), [])


class TestWhatADecidedVerdictTookOutOfTheBarIsNotInIt(unittest.TestCase):
    """RED on the unrepaired tree: each of these bars holds ONE whole rest."""

    def test_a_box_refused_as_NOT_A_NOTEHEAD_LEFT_THE_BAR(self):
        log = Log()
        rest = _whole_rest(log)
        for g in (1, 2, 3):          # the width floor's usual population
            head = _quarter_head(log, g)
            _v(log, head, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Outcome.DECIDED, True,
               reason="too_narrow")
        out = _fire(log, _meter(log))
        self.assertEqual(len(out), 1)
        self.assertTrue(log.verdict(Q.DURATION, rest).value["measure_rest"])

    def test_a_DUPLICATE_BOX_of_the_same_rest_LEFT_THE_BAR(self):
        """2.15 refuses the weaker box; its duration verdict still stands."""
        log = Log()
        rest = _whole_rest(log, 0)
        dup = _whole_rest(log, 1)
        _v(log, dup, Q.REST_IS_NOT_A_REST, Outcome.DECIDED, True,
           reason="rest_is_a_duplicate_box")
        out = _fire(log, _meter(log))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].subject, rest)
        self.assertTrue(log.verdict(Q.DURATION, rest).value["measure_rest"])
        self.assertNotIn("measure_rest", log.verdict(Q.DURATION, dup).value)

    def test_a_head_OWNED_BY_ANOTHER_STAFF_LEFT_THE_BAR(self):
        log = Log()
        rest = _whole_rest(log)
        head = _quarter_head(log, 1)
        _v(log, head, Q.GLYPH_OWNER, Outcome.DECIDED, OTHER_STAFF,
           reason="ladder_complete")
        out = _fire(log, _meter(log))
        self.assertEqual(len(out), 1)
        self.assertTrue(log.verdict(Q.DURATION, rest).value["measure_rest"])

    def test_the_basis_NAMES_what_was_set_aside_LEFT_THE_BAR(self):
        """The marking must be traceable to the verdicts that cleared the
        bar, or a reviewer sees a whole-bar rest beside ink it never
        explains."""
        log = Log()
        _whole_rest(log)
        head = _quarter_head(log, 1)
        refusal = _v(log, head, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Outcome.DECIDED,
                     True, reason="too_narrow")
        out = _fire(log, _meter(log))
        self.assertEqual(len(out), 1)
        self.assertIn(refusal.id, out[0].basis)
        self.assertEqual(out[0].detail.get("set_aside"), [head.to_key()])

    def test_a_REAL_note_is_not_rescued_by_a_refused_twin(self):
        """Negative control in the SAME class: one refused box does not clear
        the bar of a second, unrefused head."""
        log = Log()
        _whole_rest(log)
        junk = _quarter_head(log, 1)
        _v(log, junk, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Outcome.DECIDED, True,
           reason="too_narrow")
        _quarter_head(log, 2)
        self.assertEqual(_fire(log, _meter(log)), [])


if __name__ == "__main__":
    unittest.main()
