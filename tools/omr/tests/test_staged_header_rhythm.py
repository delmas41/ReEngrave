"""The key signature and the meter — the two header facts, adjudicated.

⚠️ COHERENCE, NOT ACCURACY.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import rhythm as rhythm_mod
from tools.omr.staged.record import (ABSTAIN, Log, Outcome, Q, READERS, Scope,
                                     State)

SUB = R.staff(0, 0, 0)


def _with_clef(log, clef="treble", sub=SUB):
    log.observe(sub, Q.CLEF_GLYPH, {"treble": "clefG", "bass": "clefF"}[clef],
                reader=READERS.DETECTOR, frame="cell:0", score=0.95)


class TestKeySignatureNeedsASettledClef(unittest.TestCase):
    """⚠️ The guard MOVED, it was not removed. Fitting three flats against a
    guessed clef once returned TWO SHARPS."""

    def test_no_clef_means_no_key(self):
        """⚠️ The run is READ and the key is still refused. Note it carries no
        `Q.KEYSIG_CLEF_FIT`: a fit IS clef evidence, so supplying one would
        settle the clef and the test would prove nothing."""
        log = Log()
        log.observe(SUB, Q.KEYSIG_RUN_POSITION, [10, 20, 30],
                    reader=READERS.CV_HEADER, frame="header_window",
                    n_accidentals=3)
        adjudicate.run(log)
        v = log.verdict(Q.KEY_SIGNATURE, SUB)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "needs_clef")

    def test_the_fit_for_the_SETTLED_clef_is_the_answer(self):
        log = Log()
        _with_clef(log, "treble")
        log.observe(SUB, Q.KEYSIG_CLEF_FIT, "treble", reader=READERS.CV_HEADER,
                    frame="header_window", n_accidentals=3, fifths=-3)
        log.observe(SUB, Q.KEYSIG_CLEF_FIT, "bass", reader=READERS.CV_HEADER,
                    frame="header_window", n_accidentals=2, fifths=2)
        adjudicate.run(log)
        v = log.verdict(Q.KEY_SIGNATURE, SUB)
        self.assertEqual(v.value, -3)

    def test_a_run_fitting_no_slot_table_of_the_settled_clef_is_a_CONTRADICTION(self):
        """⚠️ Recorded as its own reason, not as a gap: it says the clef and
        the key disagree, and `implicates` names both."""
        log = Log()
        _with_clef(log, "treble")
        log.observe(SUB, Q.KEYSIG_CLEF_FIT, "bass", reader=READERS.CV_HEADER,
                    frame="header_window", n_accidentals=3, fifths=-3)
        adjudicate.run(log)
        v = log.verdict(Q.KEY_SIGNATURE, SUB)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "run_fits_no_slot_table")


class TestTheKeyFitTestsTheClef(unittest.TestCase):
    """⚠️ The implication test that needs NO identity -- and it reaches exactly
    the staves the written-range test cannot, because on a scan 29 of 29
    unresolved non-treble staves print no label at all."""

    def test_a_discriminating_fit_moves_the_clef(self):
        log = Log()
        log.observe(SUB, Q.CLEF_GLYPH, "clefC", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.9)
        log.observe(SUB, Q.CLEF_LOCATED, "alto", reader=READERS.CV_LOCATOR,
                    frame="header_window", score=0.7)
        log.observe(SUB, Q.CLEF_LOCATED, "tenor", reader=READERS.CV_LOCATOR,
                    frame="cell:0", score=0.7)
        # the run fits tenor only
        log.observe(SUB, Q.KEYSIG_CLEF_FIT, "tenor", reader=READERS.CV_HEADER,
                    frame="header_window", n_accidentals=3, fifths=-3)
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.CLEF, SUB).value, "tenor")

    def test_a_fit_that_discriminates_NOTHING_is_withheld(self):
        """A run fitting every candidate says nothing, and a 0-accidental key
        fits them all."""
        log = Log()
        log.observe(SUB, Q.CLEF_GLYPH, "clefG", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.9)
        for c in ("treble", "bass", "alto", "tenor"):
            log.observe(SUB, Q.KEYSIG_CLEF_FIT, c, reader=READERS.CV_HEADER,
                        frame="header_window", n_accidentals=2, fifths=2)
        adjudicate.run(log)
        # the detector alone decides it; the fit adds nothing either way
        self.assertEqual(log.verdict(Q.CLEF, SUB).value, "treble")

    def test_a_zero_accidental_fit_contributes_nothing(self):
        log = Log()
        log.observe(SUB, Q.CLEF_GLYPH, "clefG", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.9)
        log.observe(SUB, Q.KEYSIG_CLEF_FIT, "bass", reader=READERS.CV_HEADER,
                    frame="header_window", n_accidentals=0, fifths=0)
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.CLEF, SUB).value, "treble")


class TestTheMeterIsASystemFact(unittest.TestCase):
    def _system(self, readings):
        log = Log()
        for i, raw in enumerate(readings):
            if raw is None:
                continue
            n, d = (4, 4) if raw in ("C", "4/4") else (2, 4)
            log.observe(R.staff(0, 0, i), Q.METER_TEMPLATE, (n, d),
                        reader=READERS.TEMPLATE, frame="header_window",
                        score=0.8, raw=raw)
        return log

    def test_one_vote_per_staff(self):
        """⚠️ The fault this fixes: a single timeSig4 at confidence 0.42 on one
        staff of nineteen once arrived at a page vote as EIGHTEEN unanimous
        votes for common time."""
        log = self._system(["2/4"] * 11 + ["4/4"])
        adjudicate.run(log)
        v = log.verdict(Q.METER, R.system(0, 0))
        self.assertEqual(v.value["raw"], "2/4")
        self.assertEqual(v.detail["n_staves_spoke"], 12)

    def test_a_system_that_disagrees_ABSTAINS(self):
        """⚠️ 6-of-10 is BELOW the floor and abstains -- found by this test
        failing when it was written with a 6:4 split and expected to decide.
        A bare majority is not agreement."""
        log = self._system(["2/4", "2/4", "4/4", "4/4", "C"])
        adjudicate.run(log)
        v = log.verdict(Q.METER, R.system(0, 0))
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_agreement")

    def test_C_and_4_4_are_not_averaged_into_one_answer(self):
        """⚠️ One bar length, two engravings. musicdiff charges the difference
        at 3 edits per staff, so a page must not merge them."""
        log = self._system(["C"] * 8 + ["4/4"] * 2)
        adjudicate.run(log)
        v = log.verdict(Q.METER, R.system(0, 0))
        self.assertEqual(v.value["raw"], "C")

    def test_the_agreement_floor_is_declared(self):
        self.assertGreater(rhythm_mod.METER_AGREEMENT_FLOOR, 0.5)


if __name__ == "__main__":
    unittest.main()
