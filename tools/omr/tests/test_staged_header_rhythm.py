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


class TestAMeterIsPrintedOnEVERYStaffOfItsSystem(unittest.TestCase):
    """⚠️ THE OTHER HALF OF THE LEGACY RULE, AND DROPPING IT SHIPPED A WRONG
    METER AT FULL AGREEMENT.

    `METER_AGREEMENT_FLOOR` divides by the staves that SPOKE, so three
    spurious readings that happen to agree score 3/3 = 1.0.
    `rhythm._dominant_detected_meter` says exactly this in its own docstring —
    *"two spurious readings that happen to agree are unanimous among
    themselves"* — and requires half the page's staves as well.

    Measured on Beethoven 5 / Litolff p.2, whose reference is 2/4 on all 18
    parts and which **prints no time signature at all** (it opens at bar 17):
    system 1 had **3 staves of 11** match a common-time `C`, agreed 1.0, and
    shipped 4/4; page 1 of the same run had **12 of 12** read the true 2/4.
    """

    def _system(self, n_staves, spoke, raw=(4, 4), rawname="C"):
        log = Log()
        sysj = R.system(0, 0)
        log.record(adjudicate.Verdict(
            id=log._next_id("vrd"), subject=sysj, quantity=Q.SYSTEM_STAFF_COUNT,
            outcome=Outcome.DECIDED, value=n_staves, decider="t",
            reason="counted"))
        for i in range(spoke):
            log.observe(R.staff(0, 0, i), Q.METER_TEMPLATE, raw,
                        reader=READERS.TEMPLATE, frame="header_window",
                        score=0.7, raw=rawname)
        log.freeze()
        adjudicate._ensure_decisions()
        return adjudicate.adjudicate_one(
            log, adjudicate.REGISTRY[Q.METER], sysj)

    def test_three_staves_of_eleven_do_not_carry_a_system(self):
        v = self._system(11, 3)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "too_few_staves_read_it")
        self.assertEqual(v.detail["n_staves_on_system"], 11)
        self.assertEqual(v.detail["would_have_been"], "C")

    def test_the_true_reading_on_every_staff_is_untouched(self):
        v = self._system(12, 12, raw=(2, 4), rawname="2/4")
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["numerator"], 2)
        self.assertEqual(v.value["denominator"], 4)

    def test_coverage_and_agreement_are_reported_APART(self):
        """⚠️ "Do the staves that spoke agree?" and "did enough of them
        speak?" are two facts, and a handful of spurious readings passes the
        first trivially. A page that shipped a wrong meter and a page whose
        staves disagreed must never be the same row."""
        few = self._system(11, 3)
        self.assertEqual(few.reason, "too_few_staves_read_it")

        log = Log()
        sysj = R.system(0, 0)
        log.record(adjudicate.Verdict(
            id=log._next_id("vrd"), subject=sysj, quantity=Q.SYSTEM_STAFF_COUNT,
            outcome=Outcome.DECIDED, value=4, decider="t", reason="counted"))
        for i, (raw, name) in enumerate([((4, 4), "C"), ((4, 4), "C"),
                                         ((3, 4), "3/4"), ((2, 4), "2/4")]):
            log.observe(R.staff(0, 0, i), Q.METER_TEMPLATE, raw,
                        reader=READERS.TEMPLATE, frame="header_window",
                        score=0.7, raw=name)
        log.freeze()
        disagree = adjudicate.adjudicate_one(
            log, adjudicate.REGISTRY[Q.METER], sysj)
        self.assertEqual(disagree.reason, "no_agreement")

    def test_with_no_staff_count_the_floor_declines_to_judge(self):
        """A system whose staff count never decided cannot be asked what share
        of it spoke, and inventing a denominator would be worse than the gap."""
        log = Log()
        sysj = R.system(0, 0)
        for i in range(3):
            log.observe(R.staff(0, 0, i), Q.METER_TEMPLATE, (4, 4),
                        reader=READERS.TEMPLATE, frame="header_window",
                        score=0.7, raw="C")
        log.freeze()
        adjudicate._ensure_decisions()
        v = adjudicate.adjudicate_one(log, adjudicate.REGISTRY[Q.METER], sysj)
        self.assertIs(v.outcome, Outcome.DECIDED)
