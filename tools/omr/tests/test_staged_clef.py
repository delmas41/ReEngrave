"""The clef adjudicator — five readers, a floor, and no guessing at C.

⚠️ COHERENCE, NOT ACCURACY.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import clef as clef_mod
from tools.omr.staged.record import (ABSTAIN, Log, Outcome, Q, READERS, State)

SUB = R.staff(0, 0, 0)


def _log():
    return Log()


class TestAClassNameCannotNameACClef(unittest.TestCase):
    """⚠️ A-CLEF-4, and the fix is not a better placeholder -- it is refusing
    to place one.

    Alto, tenor, soprano, mezzo and baritone are THE SAME GLYPH on different
    lines. `clefC` says a C clef is present and nothing about which.
    """

    def test_clefC_alone_ABSTAINS_rather_than_guessing_alto(self):
        log = _log()
        log.observe(SUB, Q.CLEF_GLYPH, "clefC", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.95)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_candidates")

    def test_clefC_SUPPORTS_the_clef_the_locator_named(self):
        """It is evidence, just not evidence about WHICH."""
        log = _log()
        log.observe(SUB, Q.CLEF_GLYPH, "clefC", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.95)
        log.observe(SUB, Q.CLEF_LOCATED, "tenor", reader=READERS.CV_LOCATOR,
                    frame="header_window", score=0.88, family="C", line=4)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertEqual(v.value, "tenor")

    def test_the_placeholder_would_have_OUTVOTED_the_locator(self):
        """⚠️ Why the first cut was worse than it looked: a detector clef at
        high confidence weighs 3.0 and the locator's MEASURED name weighs 2.0,
        so `clefC -> alto` would have beaten the only reader that can answer
        the question -- and any measurement taken then would have priced the
        placeholder rather than the mechanism."""
        self.assertGreater(clef_mod.W_DETECTOR_HIGH, clef_mod.W_LOCATOR)
        self.assertNotIn("clefC", clef_mod._GLYPH_TO_CLEF)


class TestBothCropsAreEvidence(unittest.TestCase):
    def test_two_crops_agreeing_are_two_signals(self):
        """⚠️ Deliberately unlike the two DETECTOR rungs, which are the same
        call on the same list object -- measured divergent on 0 of 396 staves.
        Two crops are genuinely two looks."""
        log = _log()
        for frame in ("header_window", "cell:0"):
            log.observe(SUB, Q.CLEF_LOCATED, "alto", reader=READERS.CV_LOCATOR,
                        frame=frame, score=0.8)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertEqual(v.value, "alto")
        self.assertEqual(v.correlated, ())

    def test_a_crop_that_refused_carries_the_readers_own_word(self):
        """`locate_clef(trace=)` has always been able to say which branch
        ended it, and NEITHER pipeline call site passes a trace -- so today
        every refusal is an indistinguishable None."""
        log = _log()
        log.abstain(SUB, Q.CLEF_LOCATED, reader=READERS.CV_LOCATOR,
                    frame="cell:0", reason=ABSTAIN.OCCUPIED,
                    locator_branch="occupied")
        self.assertIs(log.state(Q.CLEF_LOCATED, SUB), State.DECLINED)
        (row,) = log.refusals(Q.CLEF_LOCATED, SUB)
        self.assertEqual(row.detail["locator_branch"], "occupied")


class TestTheFloor(unittest.TestCase):
    def test_a_close_contest_NARROWS_and_keeps_both_readings(self):
        """⚠️ Today the measure-cell argmax wins at ANY confidence -- there is
        no floor anywhere in the chain. The floor's EXISTENCE is the change.

        ⚠️ AND SINCE CANDIDATE SETS, THE CONTEST SURVIVES THE FLOOR. Before,
        `margin_below_floor` discarded it, so *"the readers disagreed between
        treble and bass"* and *"nothing was read at all"* arrived at a
        consumer as the same answer. Now the survivors travel with the verdict
        and a later decision can settle them on its own evidence.
        """
        log = _log()
        log.observe(SUB, Q.CLEF_GLYPH, "clefG", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.20)
        log.observe(SUB, Q.CLEF_GLYPH, "clefF", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.20)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertIs(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "margin_below_floor")
        self.assertEqual(v.margin, 0.0)
        self.assertIsNone(v.value, "it still refuses to pick one")
        self.assertEqual({c.value for c in v.candidates}, {"treble", "bass"})

    def test_a_narrowed_clef_still_produces_NO_pitches(self):
        """⚠️ Narrowing is not deciding. A consequence may not fire on a set
        it cannot resolve -- and EVALUATE records `cause_narrowed` apart from
        `cause_abstained`, because a rule that COULD choose among survivors on
        its own evidence is an opportunity, not a dead end."""
        from tools.omr.staged import evaluate
        log = _log()
        for glyph_class, score in (("clefG", 0.2), ("clefF", 0.2)):
            log.observe(SUB, Q.CLEF_GLYPH, glyph_class,
                        reader=READERS.DETECTOR, frame="cell:0", score=score)
        log.observe(R.glyph(0, 0, 0, 0, 0), Q.NOTEHEAD_STAFF_POSITION, 4.0,
                    reader=READERS.GEOMETRY, frame="cell:0")
        adjudicate.run(log)
        report = evaluate.run(log)
        self.assertEqual([f for f in report.fired if f[0] == "restate_pitch"],
                         [])
        self.assertTrue(any(s[2] == "cause_narrowed" for s in report.skipped))

    def test_a_clear_winner_decides_and_records_its_margin(self):
        log = _log()
        log.observe(SUB, Q.CLEF_GLYPH, "clefG", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.95)
        log.observe(SUB, Q.CLEF_GLYPH, "clefF", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.10)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertEqual(v.value, "treble")
        self.assertGreater(v.margin, clef_mod.MARGIN_FLOOR)


class TestWeakEvidenceIsKept(unittest.TestCase):
    """⚠️ Not dropped. A low-confidence reading is weak evidence, not no
    evidence -- and dropping it is how the incumbent chain ends up with an
    argmax over one survivor. But KEPT is not the same as SUFFICIENT."""

    def test_a_lone_weak_reading_abstains(self):
        """⚠️ A DESIGN PROPERTY FOUND BY WRITING THIS TEST, not designed in:
        with a single candidate the runner-up is 0, so `MARGIN_FLOOR` doubles
        as an ABSOLUTE floor on a lone reading as well as a separation floor
        between two. That is defensible and is now deliberate -- a solitary
        clef at confidence 0.05 with nothing corroborating it should not take
        a staff -- but it means the constant carries two jobs and a sweep of
        it moves both. Recorded as A-CLEF-6."""
        log = _log()
        log.observe(SUB, Q.CLEF_GLYPH, "clefG", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.05)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "margin_below_floor")

    def test_but_it_COUNTS_toward_a_corroborated_answer(self):
        """The same weak reading, with an independent crop agreeing, decides
        -- which is what "kept, not dropped" has to mean to be worth
        anything."""
        log = _log()
        log.observe(SUB, Q.CLEF_GLYPH, "clefG", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.05)
        log.observe(SUB, Q.CLEF_LOCATED, "treble", reader=READERS.CV_LOCATOR,
                    frame="header_window", score=0.7)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertEqual(v.value, "treble")


if __name__ == "__main__":
    unittest.main()
