"""ROADMAP 2.22 -- `reconcile_duration` sums the bar EXPORT will write.

The EVALUATE rule that re-reads ONE note so a bar lands on its meter
(`consequences.reconcile_duration`) had two disconnections from EXPORT, found
by attributing every held bar of Litolff 1/i (FINDINGS §17):

1. It summed every standing duration in the cell, including boxes a DECIDED
   verdict had already taken OUT of the bar (not a notehead, not a rest, a
   contest's losing copy) -- 2.19's fault in `size_measure_rest`, in the
   second rule that sums a cell. EXPORT writes none of them.
2. A narrowed note entered the total at its best candidate, and a bar that
   fitted only THROUGH that candidate was "already fits": the note stayed
   NARROWED, EXPORT refused it (`duration_narrowed`), and 2.8 held the bar.

Positive and negative controls (an all-DECIDED bar that fits is left alone;
two narrowed notes that both fit refuse; an ABSTAINED refusal removes
nothing; a head its own staff kept is still in the bar; no meter, no repair)
pass on both sides. The tests named `*_RED` fail on the unrepaired tree.
"""
from __future__ import annotations

import unittest

from tools.omr.staged import consequences
from tools.omr.staged import record as R
from tools.omr.staged.record import Candidate, Log, Outcome, Q, Verdict

CELL = R.cell(0, 0, 1, 3)
OWN_STAFF = R.staff(0, 0, 1).to_key()


def _v(log, sub, q, outcome, value, reason="t", detail=None, candidates=()):
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=sub, quantity=q, outcome=outcome,
        value=value, decider="test", reason=reason, detail=detail or {},
        candidates=candidates))


def _dur(beats, levels):
    return {"beats": beats, "written": beats, "dots": 0,
            "beam_levels": levels}


def _decided(log, g, beats, levels=0):
    sub = R.glyph(0, 0, 1, 3, g)
    _v(log, sub, Q.DURATION, Outcome.DECIDED, _dur(beats, levels),
       reason="head_and_marks")
    return sub


def _narrowed(log, g, *options):
    sub = R.glyph(0, 0, 1, 3, g)
    _v(log, sub, Q.DURATION, Outcome.NARROWED, None, reason="beams_ambiguous",
       candidates=tuple(Candidate(_dur(b, lv), 2.0 - i)
                        for i, (b, lv) in enumerate(options)))
    return sub


def _events(log, *glyph_groups):
    """One DECIDED `Q.EVENT` for the cell: each group is one event."""
    _v(log, CELL, Q.EVENT, Outcome.DECIDED,
       {"events": [{"glyphs": list(g)} for g in glyph_groups]})


def _meter(log, num=2, den=4):
    return _v(log, R.system(0, 0), Q.METER, Outcome.DECIDED,
              {"numerator": num, "denominator": den, "raw": f"{num}/{den}"})


def _fire(log, meter):
    return consequences.reconcile_duration(log, CELL, meter)


class TestControls(unittest.TestCase):
    """GREEN before and after 2.22."""

    def test_an_all_DECIDED_bar_that_fits_is_left_alone(self):
        log = Log()
        _decided(log, 0, 1.0)
        _decided(log, 1, 1.0)
        _events(log, [0], [1])
        self.assertEqual(_fire(log, _meter(log)), [])

    def test_the_old_repair_still_fires(self):
        """1.0 + 0.5 in 2/4: only the eighth one level longer lands."""
        log = Log()
        _decided(log, 0, 1.0)
        e = _decided(log, 1, 0.5, levels=1)
        _events(log, [0], [1])
        out = _fire(log, _meter(log))
        self.assertEqual(len(out), 1)
        self.assertEqual(log.verdict(Q.DURATION, e).value["beats"], 1.0)

    def test_TWO_narrowed_notes_that_both_fit_are_not_unique(self):
        """1.0 + 1.0 in 2/4, both narrowed {1.0, 0.5}: each one's best
        candidate is a landing, so there are two and the rule refuses."""
        log = Log()
        a = _narrowed(log, 0, (1.0, 0), (0.5, 1))
        b = _narrowed(log, 1, (1.0, 0), (0.5, 1))
        _events(log, [0], [1])
        self.assertEqual(_fire(log, _meter(log)), [])
        for g in (a, b):
            self.assertIs(log.verdict(Q.DURATION, g).outcome,
                          Outcome.NARROWED)

    def test_an_ABSTAINED_refusal_removes_nothing(self):
        """Rule 8: a box nothing DECIDED took out of the bar is still in it.
        1.0 + 0.5 + a 1.0 box under an abstained refusal = 2.5: the two
        quarter-level readings (0.5 -> 0.25 is not enough; 1.0 -> 0.5 on
        either quarter) are two landings, so nothing fires."""
        log = Log()
        _decided(log, 0, 1.0)
        _decided(log, 1, 0.5, levels=1)
        junk = _decided(log, 2, 1.0)
        _v(log, junk, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Outcome.ABSTAINED, None,
           reason="no_evidence")
        _events(log, [0], [1], [2])
        self.assertEqual(_fire(log, _meter(log)), [])

    def test_a_head_its_OWN_staff_kept_is_still_in_the_bar(self):
        log = Log()
        _decided(log, 0, 1.0)
        _decided(log, 1, 0.5, levels=1)
        kept = _decided(log, 2, 1.0)
        _v(log, kept, Q.GLYPH_OWNER, Outcome.DECIDED, OWN_STAFF,
           reason="no_contest")
        _events(log, [0], [1], [2])
        self.assertEqual(_fire(log, _meter(log)), [])

    def test_no_meter_no_repair(self):
        log = Log()
        _narrowed(log, 0, (1.0, 0), (0.5, 1))
        _decided(log, 1, 1.0)
        _events(log, [0], [1])
        undecided = _v(log, R.system(0, 0), Q.METER, Outcome.ABSTAINED, None,
                       reason="carry_not_corroborated")
        self.assertEqual(_fire(log, undecided), [])

    def test_a_narrowed_REST_is_still_not_re_read(self):
        log = Log()
        _decided(log, 0, 1.0)
        sub = R.glyph(0, 0, 1, 3, 1)
        _v(log, sub, Q.DURATION, Outcome.NARROWED, None, reason="rest_value",
           candidates=(Candidate({**_dur(1.0, 0), "is_rest": True}, 2.0),
                       Candidate({**_dur(2.0, 0), "is_rest": True}, 1.0)))
        _events(log, [0], [1])
        self.assertEqual(_fire(log, _meter(log)), [])


class TestTheBarExportWillWrite(unittest.TestCase):
    """RED on the unrepaired tree."""

    def test_a_narrowing_the_meter_settles_is_DECIDED_RED(self):
        """1.0 + narrowed {1.0, 0.5} in 2/4: only 1.0 lands. EXPORT would
        refuse the narrowed note and hold the bar; the meter settles it."""
        log = Log()
        _decided(log, 0, 1.0)
        g = _narrowed(log, 1, (1.0, 0), (0.5, 1))
        _events(log, [0], [1])
        out = _fire(log, _meter(log))
        self.assertEqual(len(out), 1)
        now = log.verdict(Q.DURATION, g)
        self.assertIs(now.outcome, Outcome.DECIDED)
        self.assertEqual(now.value["beats"], 1.0)
        self.assertTrue(now.detail.get("bar_fit_only_through_this_narrowing"))

    def test_a_box_refused_NOT_A_NOTEHEAD_is_set_aside_RED(self):
        """1.0 + 0.5 + a 1.0 box DECIDED not a notehead. With the box, 2.5
        has two landings (either quarter halved); without it, 1.5 has one
        (the eighth one level longer)."""
        log = Log()
        _decided(log, 0, 1.0)
        e = _decided(log, 1, 0.5, levels=1)
        junk = _decided(log, 2, 1.0)
        refusal = _v(log, junk, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Outcome.DECIDED,
                     True, reason="too_narrow")
        _events(log, [0], [1], [2])
        out = _fire(log, _meter(log))
        self.assertEqual(len(out), 1)
        now = log.verdict(Q.DURATION, e)
        self.assertEqual(now.value["beats"], 1.0)
        self.assertIn(refusal.id, now.basis)
        self.assertEqual(now.detail.get("set_aside"), [junk.to_key()])

    def test_a_contest_s_LOSING_COPY_is_set_aside_RED(self):
        log = Log()
        _decided(log, 0, 1.0)
        e = _decided(log, 1, 0.5, levels=1)
        copy = _decided(log, 2, 1.0)
        _v(log, copy, Q.GLYPH_OWNER, Outcome.DECIDED,
           R.staff(0, 0, 2).to_key(), reason="distance")
        _events(log, [0], [1], [2])
        out = _fire(log, _meter(log))
        self.assertEqual(len(out), 1)
        self.assertEqual(log.verdict(Q.DURATION, e).value["beats"], 1.0)


if __name__ == "__main__":
    unittest.main()
