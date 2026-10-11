"""ROADMAP 2.12m -- one printed mark, two owners: drop the loser (STAGED,
ADJUDICATE: `ownership.reconcile_articulation_twins`, run by `adjudicate.run`
right after `Q.ARTICULATION_OWNER`).

Sean (2026-10-11): *"Drop the losing owner."* A mark between two staves is
detected once in each staff's padded cell (`same_ink_twins`); each copy is
decided on its own cell, and where both decide on DIFFERENT heads the exporter
writes the mark twice. A resolved contest DROPS the loser, never relocates it
(CLAUDE.md §10); the loser's verdict is SUPERSEDED, never overwritten.

  1. the two owners are ONE printed head (page boxes one ink) -> keep one copy,
     the other `duplicate_of_twin`;
  2. both owners on the SAME side of the mark, different heads -> the nearer
     (page px) wins by more than the tie tolerance, else both
     `twin_owners_disagree`;
  3. owners on OPPOSITE sides -> the copy decided by the more specific rule wins
     (empty bar / shared head > two voices > long chord stem > notehead side);
     equal -> both `twin_owners_disagree` (rule 8: cannot tell is not an answer).
     CONVENTION ASSUMED for the order: Sean's tiles 1 (long chord beat notehead
     side) and 7 (shared head beat long chord) of `out/print/2.12m-review/`.

Written RED against `aed05e48` (the function did not exist). Controls beside
them: twins with the SAME owner, and a twin that is not decided, are untouched.

Page px frame, y down. Upper staff head at y 100, lower staff head at y 300,
the mark between at y 200.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import ownership as own
from tools.omr.staged.record import Log, Outcome, Q, READERS

UP_MARK = R.glyph(0, 0, 0, 0, 0)     # the copy in the upper staff's cell
LO_MARK = R.glyph(0, 0, 1, 0, 0)     # the copy in the lower staff's cell
UP_HEAD = R.glyph(0, 0, 0, 0, 1)
LO_HEAD = R.glyph(0, 0, 1, 0, 1)
MARK_BOX = [100.0, 195.0, 112.0, 205.0]


def _log(heads):
    """`heads`: {subject: page box}."""
    log = Log()
    for m in (UP_MARK, LO_MARK):
        log.observe(m, Q.ARTICULATION_MARK, "articAccentAbove",
                    reader=READERS.DETECTOR, frame="cell", score=0.8,
                    bbox_page_px=MARK_BOX)
    for h, box in heads.items():
        log.observe(h, Q.GLYPH_BOX, ("noteheadBlack", 0, 0, 10, 10),
                    reader=READERS.DETECTOR, frame="cell", score=0.9,
                    category="notehead", bbox_page_px=box)
    log.freeze()
    return log


def _decide(log, mark, head, twin, rule="notehead_side", shared=False):
    log.record(R.Verdict(
        id=log._next_id("vrd"), subject=mark, quantity=Q.ARTICULATION_OWNER,
        outcome=Outcome.DECIDED, value=head.to_key(), decider="test",
        reason="nearest_on_notehead_side",
        detail={"stem_rule": rule, "shared_head": shared,
                "same_ink_twins": [twin.to_key()]}))


def _abstain(log, mark, twin):
    log.record(R.Verdict(
        id=log._next_id("vrd"), subject=mark, quantity=Q.ARTICULATION_OWNER,
        outcome=Outcome.ABSTAINED, value=None, decider="test",
        reason="no_notehead", detail={"same_ink_twins": [twin.to_key()]}))


ABOVE = [100.0, 90.0, 112.0, 110.0]      # a head above the mark
BELOW = [100.0, 290.0, 112.0, 310.0]     # a head below it


class TestOneMarkTwoOwners(unittest.TestCase):
    def _run(self, log):
        own.reconcile_articulation_twins(log)
        return (log.verdict(Q.ARTICULATION_OWNER, UP_MARK),
                log.verdict(Q.ARTICULATION_OWNER, LO_MARK))

    def test_RED_one_printed_head_twice_keeps_one_copy(self):
        log = _log({UP_HEAD: BELOW, LO_HEAD: [101.0, 291.0, 113.0, 311.0]})
        _decide(log, UP_MARK, UP_HEAD, LO_MARK)
        _decide(log, LO_MARK, LO_HEAD, UP_MARK)
        up, lo = self._run(log)
        self.assertEqual(sorted([up.outcome.value, lo.outcome.value]),
                         ["abstained", "decided"])
        loser = up if up.outcome is Outcome.ABSTAINED else lo
        self.assertEqual(loser.reason, "duplicate_of_twin")
        self.assertIsNotNone(loser.supersedes)

    def test_RED_the_specific_rule_beats_the_default(self):
        """Sean's tile 1: long chord stem (below) beat notehead side (above)."""
        log = _log({UP_HEAD: ABOVE, LO_HEAD: BELOW})
        _decide(log, UP_MARK, UP_HEAD, LO_MARK, rule="notehead_side")
        _decide(log, LO_MARK, LO_HEAD, UP_MARK, rule="long_chord_stem")
        up, lo = self._run(log)
        self.assertEqual(lo.outcome, Outcome.DECIDED)
        self.assertEqual(up.outcome, Outcome.ABSTAINED)
        self.assertEqual(up.reason, "lost_to_twin")
        self.assertEqual(up.detail["winner"], LO_MARK.to_key())

    def test_RED_a_shared_head_beats_a_long_chord_stem(self):
        """Sean's tile 7."""
        log = _log({UP_HEAD: ABOVE, LO_HEAD: BELOW})
        _decide(log, UP_MARK, UP_HEAD, LO_MARK, rule="long_chord_stem")
        _decide(log, LO_MARK, LO_HEAD, UP_MARK, rule="stem_side", shared=True)
        up, lo = self._run(log)
        self.assertEqual((up.outcome, lo.outcome),
                         (Outcome.ABSTAINED, Outcome.DECIDED))

    def test_RED_equal_rules_on_opposite_sides_drop_both(self):
        log = _log({UP_HEAD: ABOVE, LO_HEAD: BELOW})
        _decide(log, UP_MARK, UP_HEAD, LO_MARK)
        _decide(log, LO_MARK, LO_HEAD, UP_MARK)
        up, lo = self._run(log)
        self.assertEqual((up.reason, lo.reason),
                         ("twin_owners_disagree", "twin_owners_disagree"))

    def test_RED_same_side_the_nearer_head_wins(self):
        far = [100.0, 390.0, 112.0, 410.0]
        log = _log({UP_HEAD: BELOW, LO_HEAD: far})
        _decide(log, UP_MARK, UP_HEAD, LO_MARK)
        _decide(log, LO_MARK, LO_HEAD, UP_MARK)
        up, lo = self._run(log)
        self.assertEqual((up.outcome, lo.outcome),
                         (Outcome.DECIDED, Outcome.ABSTAINED))
        self.assertEqual(lo.reason, "lost_to_twin")

    def test_same_side_about_equally_near_drops_both(self):
        beside = [140.0, 291.0, 152.0, 311.0]      # level, not the same ink
        log = _log({UP_HEAD: BELOW, LO_HEAD: beside})
        _decide(log, UP_MARK, UP_HEAD, LO_MARK)
        _decide(log, LO_MARK, LO_HEAD, UP_MARK)
        up, lo = self._run(log)
        self.assertEqual((up.reason, lo.reason),
                         ("twin_owners_disagree", "twin_owners_disagree"))


class TestNoContestIsLeftAlone(unittest.TestCase):
    def test_twins_with_the_same_owner_are_untouched(self):
        log = _log({UP_HEAD: BELOW})
        _decide(log, UP_MARK, UP_HEAD, LO_MARK)
        _decide(log, LO_MARK, UP_HEAD, UP_MARK)
        own.reconcile_articulation_twins(log)
        self.assertEqual(log.verdict(Q.ARTICULATION_OWNER, UP_MARK).outcome,
                         Outcome.DECIDED)
        self.assertEqual(log.verdict(Q.ARTICULATION_OWNER, LO_MARK).outcome,
                         Outcome.DECIDED)

    def test_an_undecided_twin_is_no_contest(self):
        log = _log({UP_HEAD: ABOVE, LO_HEAD: BELOW})
        _decide(log, UP_MARK, UP_HEAD, LO_MARK)
        _abstain(log, LO_MARK, UP_MARK)
        own.reconcile_articulation_twins(log)
        v = log.verdict(Q.ARTICULATION_OWNER, UP_MARK)
        self.assertEqual((v.outcome, v.value),
                         (Outcome.DECIDED, UP_HEAD.to_key()))


if __name__ == "__main__":
    unittest.main()
