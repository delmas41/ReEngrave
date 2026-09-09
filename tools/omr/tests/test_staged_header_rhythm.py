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


class TestTheMeterCarry(unittest.TestCase):
    """A meter is a fact of the MOVEMENT — printed at its start and nowhere
    else — so a system that reads none may take the last one that was READ.

    ⚠️ OFF BY DEFAULT, AND THE HAZARD IS MEASURED RATHER THAN FEARED. On
    Beethoven 5 / Litolff `984073`, page 17 is the *Andante con moto*: a NEW
    MOVEMENT printing `3/8` on every staff, whose three systems all abstain
    `no_evidence` because the template reader ran on all 20 staves and
    declined `below_threshold` — Litolff sets `3` over `8` as heavy
    nearly-touching digits. So an unconditional carry stamps movement 1's
    `2/4` onto the whole Andante, which is what `test_the_hazard` pins.
    """

    def _bars(self, log, page, *, beats, n_staves=4, n_bars=3):
        """Give a system BARS that measure `beats`, so the carry's second
        witness has something to say.

        ⚠️ A carried meter is a CANDIDATE and must be corroborated by the bars
        it claims to govern, so a log with NO bars carries nothing — which is
        `test_a_page_that_cannot_corroborate_does_not_carry`.
        """
        for st in range(n_staves):
            for c in range(n_bars):
                cell = R.cell(page, 0, st, c)
                g = R.glyph(page, 0, st, c, 0)
                log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                            reader=READERS.DETECTOR, frame="cell:%d" % c,
                            score=0.9)
                log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 100, 0, 20, 16),
                            reader=READERS.DETECTOR, frame="cell:%d" % c,
                            score=0.9)
                log.record(adjudicate.Verdict(
                    id=log._next_id("vrd"), subject=g, quantity=Q.DURATION,
                    outcome=Outcome.DECIDED,
                    value={"beats": beats, "written": beats,
                           "duration_type": "quarter", "dots": 0},
                    decider="t", reason="head_and_marks"))
                log.record(adjudicate.Verdict(
                    id=log._next_id("vrd"), subject=cell, quantity=Q.EVENT,
                    outcome=Outcome.DECIDED,
                    value={"events": [{"glyphs": [0], "x": 100.0,
                                       "kind": "chord"}]},
                    decider="t", reason="x_clustered"))

    def _log(self, carried_pages=(0, 1), dst_beats=2.0, bars=True):
        """Page 0 system 0 reads 2/4 on 12 of 12; page 1 system 0 reads no
        meter at all, and its BARS measure `dst_beats`."""
        log = Log()
        src = R.system(carried_pages[0], 0)
        dst = R.system(carried_pages[1], 0)
        for sysj, n in ((src, 12), (dst, 11)):
            log.record(adjudicate.Verdict(
                id=log._next_id("vrd"), subject=sysj,
                quantity=Q.SYSTEM_STAFF_COUNT, outcome=Outcome.DECIDED,
                value=n, decider="t", reason="counted"))
        for i in range(12):
            log.observe(R.staff(carried_pages[0], 0, i), Q.METER_TEMPLATE,
                        (2, 4), reader=READERS.TEMPLATE,
                        frame="header_window", score=0.7, raw="2/4")
        if bars:
            self._bars(log, carried_pages[1], beats=dst_beats)
        return log, src, dst

    def _run(self, log, on):
        """Adjudicate METER ONLY, over its systems in reading order.

        ⚠️ Deliberately not `adjudicate.run`: these logs pre-record the staff
        counts the carry needs, and the full harness would re-decide them and
        trip `AlreadyAdjudicated` — the single-pass guard working, not a bug.
        Reading order is what makes the carry reachable at all, so it is
        asserted here rather than assumed: `Subject` is an ordered dataclass.
        """
        import os
        log.freeze()
        adjudicate._ensure_decisions()
        spec = adjudicate.REGISTRY[Q.METER]
        systems = sorted(log.subjects(R.Kind.SYSTEM))
        self.assertEqual(systems, sorted(systems))
        prev = os.environ.get(rhythm_mod.METER_CARRY_ENV)
        if on:
            os.environ[rhythm_mod.METER_CARRY_ENV] = "1"
        else:
            os.environ.pop(rhythm_mod.METER_CARRY_ENV, None)
        try:
            for sysj in systems:
                adjudicate.adjudicate_one(log, spec, sysj)
        finally:
            if prev is None:
                os.environ.pop(rhythm_mod.METER_CARRY_ENV, None)
            else:
                os.environ[rhythm_mod.METER_CARRY_ENV] = prev

    def test_off_by_default_the_system_still_abstains(self):
        """⚠️ The control for every claim below. Measured on the real page
        too: flag-OFF reproduced all 4,498 verdicts of the pre-change run
        identically, reasons and values included."""
        log, _src, dst = self._log()
        self._run(log, on=False)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_evidence")

    def test_on_it_takes_the_last_meter_that_was_READ(self):
        log, src, dst = self._log()
        self._run(log, on=True)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "carried")
        self.assertEqual((v.value["numerator"], v.value["denominator"]), (2, 4))
        self.assertEqual(v.detail["carried_from"], src.to_key())
        self.assertEqual(v.detail["pages_since_read"], 1)
        self.assertEqual(v.detail["instead_of"], "no_evidence")

    def test_it_never_overturns_a_system_that_read_its_own(self):
        """The carry is reached only from an abstention branch, so a system
        with its own evidence cannot be overwritten by an older page."""
        log, src, _dst = self._log()
        self._run(log, on=True)
        v = log.verdict(Q.METER, src)
        self.assertEqual(v.reason, "voted")

    def test_a_carry_NEVER_chains_onto_a_carry(self):
        """⚠️ THE NUMBER IN THE RECORD IS THE POINT. Only a `voted` verdict is
        a source, so `pages_since_read` is the true distance back to INK. A
        chain of one-page hops would each look local while the third page's
        meter was in fact sixteen pages and one movement away.
        """
        log = Log()
        src = R.system(0, 0)
        mid = R.system(1, 0)
        far = R.system(2, 0)
        for sysj, n in ((src, 12), (mid, 11), (far, 11)):
            log.record(adjudicate.Verdict(
                id=log._next_id("vrd"), subject=sysj,
                quantity=Q.SYSTEM_STAFF_COUNT, outcome=Outcome.DECIDED,
                value=n, decider="t", reason="counted"))
        for i in range(12):
            log.observe(R.staff(0, 0, i), Q.METER_TEMPLATE, (2, 4),
                        reader=READERS.TEMPLATE, frame="header_window",
                        score=0.7, raw="2/4")
        self._bars(log, 1, beats=2.0)
        self._bars(log, 2, beats=2.0)
        self._run(log, on=True)
        mid_v = log.verdict(Q.METER, mid)
        far_v = log.verdict(Q.METER, far)
        self.assertEqual(mid_v.reason, "carried")
        self.assertEqual(far_v.reason, "carried")
        # both name the READING, not each other, and the distance is honest
        self.assertEqual(mid_v.detail["carried_from"], src.to_key())
        self.assertEqual(far_v.detail["carried_from"], src.to_key())
        self.assertEqual(far_v.detail["pages_since_read"], 2)

    def test_a_NEW_MOVEMENT_REFUSES_the_carry_with_no_movement_detector(self):
        """⚠️⚠️ THIS TEST USED TO PIN A WRONG ANSWER ON PURPOSE, and its own
        comment said to change it only when a MOVEMENT-START signal existed.
        What arrived instead is a SECOND WITNESS, which is better: the bars a
        carried meter claims to govern confirm or refuse it, so a movement
        boundary needs no detecting at all — the new movement's bars simply
        contradict the old movement's meter.

        ⚠️⚠️ THIS TEST SHOWS THE MECHANISM, NOT A SOLVED PROBLEM, and the
        distinction was nearly lost. Here the destination's bars measure 1.5
        cleanly, so they genuinely contradict a carried 2/4. On the REAL
        Andante they do not speak at all: scored against `3/8`, the meter that
        page actually prints, it refuses THAT too (-1.0, against -3.0 for the
        wrong 2/4). Its durations are noise and a noisy page refuses
        everything, so the real page is protected by "when it cannot speak,
        abstain" rather than by this. A boundary on a page that READS WELL is
        unmeasured. See FINDINGS.md §10.

        What IS measured, on three well-read systems: the true meter scores
        +14, +7 and +16, and the wrong one -12, -9 and -14.
        """
        log, _src, dst = self._log(carried_pages=(1, 17), dst_beats=1.5)
        self._run(log, on=True)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "carry_outweighed_by_the_bars")
        self.assertLess(v.detail["support"], rhythm_mod.METER_CARRY_FLOOR)
        self.assertGreater(v.detail["bars_disagree"], v.detail["bars_agree"])
        self.assertEqual(v.detail["pages_since_read"], 16)

    def test_the_bars_of_the_SAME_movement_confirm_the_carry(self):
        """The other half, and the one that keeps the carry useful. Without
        this the corroboration would be indistinguishable from switching the
        carry off."""
        log, src, dst = self._log(dst_beats=2.0)
        self._run(log, on=True)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "carried")
        self.assertGreaterEqual(v.detail["support"], rhythm_mod.METER_CARRY_FLOOR)
        self.assertGreater(v.detail["bars_agree"], 0)

    def test_a_LONE_WHOLE_REST_MAY_NOT_CORROBORATE_ANYTHING(self):
        """⚠️⚠️ THE CIRCULARITY, AND LEAVING IT IN INVERTS THE ANSWER.

        An engraver fills an otherwise silent bar with ONE centred whole rest
        whatever the meter, so the glyph stands for THE BAR and says nothing
        about its length — and the 4.0 we give it is *our own default for want
        of a meter*. Counting it would read that default straight back as
        evidence, and a page of rests would confirm 4/4 for ever.

        Measured on Beethoven 5 / Litolff p.17: left in, 13 of 17 agreeing
        bars vote 4.0 and the true 1.5 gets none.

        ⚠️ This test exists because a mutation SURVIVED. Disabling the
        exclusion broke nothing in the suite, which meant the single rule that
        makes the corroboration usable was untested.
        """
        log = Log()
        src, dst = R.system(0, 0), R.system(1, 0)
        for sysj, n in ((src, 12), (dst, 11)):
            log.record(adjudicate.Verdict(
                id=log._next_id("vrd"), subject=sysj,
                quantity=Q.SYSTEM_STAFF_COUNT, outcome=Outcome.DECIDED,
                value=n, decider="t", reason="counted"))
        # the source reads 4/4 — the very value a whole rest would "confirm"
        for i in range(12):
            log.observe(R.staff(0, 0, i), Q.METER_TEMPLATE, (4, 4),
                        reader=READERS.TEMPLATE, frame="header_window",
                        score=0.7, raw="4/4")
        # every bar of the destination is a LONE WHOLE REST at 4.0
        for st in range(4):
            for c in range(3):
                cell, g = R.cell(1, 0, st, c), R.glyph(1, 0, st, c, 0)
                log.observe(g, Q.REST, "restWhole", reader=READERS.DETECTOR,
                            frame="cell:%d" % c, score=0.9)
                log.observe(g, Q.GLYPH_BOX, ("restWhole", 100, 0, 20, 16),
                            reader=READERS.DETECTOR, frame="cell:%d" % c,
                            score=0.9)
                log.record(adjudicate.Verdict(
                    id=log._next_id("vrd"), subject=g, quantity=Q.DURATION,
                    outcome=Outcome.DECIDED,
                    value={"beats": 4.0, "written": 4.0,
                           "duration_type": "whole", "dots": 0},
                    decider="t", reason="rest_class",
                    detail={"rest": "restWhole"}))
                log.record(adjudicate.Verdict(
                    id=log._next_id("vrd"), subject=cell, quantity=Q.EVENT,
                    outcome=Outcome.DECIDED,
                    value={"events": [{"glyphs": [0], "x": 100.0,
                                       "kind": "rest"}]},
                    decider="t", reason="x_clustered"))
        self._run(log, on=True)
        v = log.verdict(Q.METER, dst)
        # the rests match 4/4 EXACTLY, and must still corroborate nothing
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.detail["state"], "too_few_assessable_bars")

    def test_the_BARS_outweigh_the_carry_and_the_carry_never_outweighs_them(self):
        """⚠️ SEAN'S ORDERING, MADE STRUCTURAL RATHER THAN TUNED.

        *"the math that can be determined by its own equation could be weighed
        more heavily than information that can only be derived"* — so a fact
        checkable by its own arithmetic must not be outvotable by one merely
        inherited. At these weights two net contradicting bars outweigh ANY
        carry, and no amount of carrying outweighs the bars.

        This is a property of the CONSTANTS, so it is asserted on them
        directly: a sweep that broke the ordering would pass every other test
        in this file.
        """
        carry = rhythm_mod.W_METER_CARRIED
        against = abs(rhythm_mod.W_METER_BAR_CONTRADICTS)
        self.assertLess(carry + 2 * rhythm_mod.W_METER_BAR_CONTRADICTS,
                        rhythm_mod.METER_CARRY_FLOOR,
                        "two contradicting bars must sink any carry")
        self.assertLess(carry, rhythm_mod.METER_CARRY_FLOOR,
                        "a carry with NOTHING to check against must not stand")
        self.assertGreaterEqual(against, rhythm_mod.W_METER_BAR_FITS * 0.5,
                                "a contradicting bar may not be a rounding "
                                "error next to an agreeing one")

    def test_the_support_and_the_counts_are_BOTH_on_the_record(self):
        """⚠️ A single number hides which of three pages you are looking at.
        Sean: "keep reporting the counts"."""
        log, _src, dst = self._log(dst_beats=2.0)
        self._run(log, on=True)
        d = log.verdict(Q.METER, dst).detail
        for key in ("support", "floor", "bars_agree", "bars_disagree",
                    "bar_lengths_seen", "pages_since_read", "carried_from"):
            self.assertIn(key, d)

    def test_the_bars_own_reading_is_recorded_even_when_it_names_nothing(self):
        """On the *Andante* the bars name NOTHING — 1.0, 3.0, 5.0 with no
        mode. That is a different fact from "they disagree with the carry",
        and the record keeps it rather than collapsing both to a refusal."""
        log, _src, dst = self._log(carried_pages=(1, 17), dst_beats=1.5)
        self._run(log, on=True)
        d = log.verdict(Q.METER, dst).detail
        self.assertTrue(d["bar_lengths_seen"])
        self.assertIn(1.5, [float(k) for k in d["bar_lengths_seen"]])

    def test_a_page_that_cannot_corroborate_does_not_carry(self):
        """⚠️ NOT "carry anyway". A carry is only as good as its
        corroboration, and a page with no assessable bar is exactly the page
        where a movement may have started unseen. Abstaining is the status
        quo; carrying unverified is the hazard."""
        log, _src, dst = self._log(bars=False)
        self._run(log, on=True)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.detail["state"], "too_few_assessable_bars")

    def test_a_carried_meter_is_never_labelled_voted(self):
        """The whole record depends on a consumer being able to tell a meter
        that was READ from one that was inherited."""
        log, _src, dst = self._log()
        self._run(log, on=True)
        self.assertNotEqual(log.verdict(Q.METER, dst).reason, "voted")


class TestEvidenceSubjectsIsStructural(unittest.TestCase):
    """`Evidence.subjects` answers "what pages and systems are there", which
    is layout, not evidence — so it takes no quantity and checks no
    declaration. Reading a VALUE off one of them is still checked."""

    def test_it_needs_no_declaration_but_a_read_still_does(self):
        log = Log()
        log.observe(R.staff(0, 0, 0), Q.METER_TEMPLATE, (2, 4),
                    reader=READERS.TEMPLATE, frame="header_window",
                    score=0.7, raw="2/4")
        log.freeze()
        adjudicate._ensure_decisions()
        spec = adjudicate.REGISTRY[Q.METER]
        ev = adjudicate.Evidence(log, R.system(0, 0), spec)
        self.assertIn(R.system(0, 0), ev.subjects(R.Kind.SYSTEM))
        with self.assertRaises(adjudicate.UndeclaredEvidence):
            ev.rows(Q.MARGIN_LABEL)


class TestTheBarsMayNameTheMeter(unittest.TestCase):
    """⚠️ A system with NO glyph and NO carry may still be told what it is in,
    by its own arithmetic.

    Sean, 2026-09-09: *"If there is no meter glyph then we have to deal with
    bar sums... We have 12 systems and 10 of them say 4/4 for 6 measures."*
    And A-DUR-6: *"If there is no established meter then it must derive the
    most likely meter based off of the order of determination above."*

    ⚠️ THE SPLIT THIS CLASS EXISTS TO PIN: the bars name a LENGTH, and only a
    system that actually READ a meter can name the ENGRAVING. 2.0 quarters is
    `2/4` and also `4/8`; no arithmetic separates them.
    """

    def _bars(self, log, page, per_cell, *, n_staves=4, system=0):
        """One cell per entry of `per_cell`, every staff reading that length."""
        for st in range(n_staves):
            for c, beats in enumerate(per_cell):
                cell = R.cell(page, system, st, c)
                g = R.glyph(page, system, st, c, 0)
                log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                            reader=READERS.DETECTOR, frame="cell:%d" % c,
                            score=0.9)
                log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 100, 0, 20, 16),
                            reader=READERS.DETECTOR, frame="cell:%d" % c,
                            score=0.9)
                log.record(adjudicate.Verdict(
                    id=log._next_id("vrd"), subject=g, quantity=Q.DURATION,
                    outcome=Outcome.DECIDED,
                    value={"beats": beats, "written": beats,
                           "duration_type": "quarter", "dots": 0},
                    decider="t", reason="head_and_marks"))
                log.record(adjudicate.Verdict(
                    id=log._next_id("vrd"), subject=cell, quantity=Q.EVENT,
                    outcome=Outcome.DECIDED,
                    value={"events": [{"glyphs": [0], "x": 100.0,
                                       "kind": "chord"}]},
                    decider="t", reason="x_clustered"))

    def _log(self, per_cell, *, source=(2, 4), source_raw="2/4",
             source_page=0, dst_page=1):
        log = Log()
        src, dst = R.system(source_page, 0), R.system(dst_page, 0)
        for sysj, n in ((src, 12), (dst, 11)):
            log.record(adjudicate.Verdict(
                id=log._next_id("vrd"), subject=sysj,
                quantity=Q.SYSTEM_STAFF_COUNT, outcome=Outcome.DECIDED,
                value=n, decider="t", reason="counted"))
        if source is not None:
            for i in range(12):
                log.observe(R.staff(source_page, 0, i), Q.METER_TEMPLATE,
                            source, reader=READERS.TEMPLATE,
                            frame="header_window", score=0.7, raw=source_raw)
        self._bars(log, dst_page, per_cell)
        return log, src, dst

    def _run(self, log, *, from_bars, carry=False):
        import os
        log.freeze()
        adjudicate._ensure_decisions()
        spec = adjudicate.REGISTRY[Q.METER]
        env = {rhythm_mod.METER_FROM_BARS_ENV: "1" if from_bars else None,
               rhythm_mod.METER_CARRY_ENV: "1" if carry else None}
        prev = {k: os.environ.get(k) for k in env}
        try:
            for k, v in env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            for sysj in sorted(log.subjects(R.Kind.SYSTEM)):
                adjudicate.adjudicate_one(log, spec, sysj)
        finally:
            for k, v in prev.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    # ── the control ─────────────────────────────────────────────────────────

    def test_off_by_default_the_system_still_abstains(self):
        """The control for every claim below."""
        log, _src, dst = self._log([2.0] * 6)
        self._run(log, from_bars=False)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_evidence")

    # ── what it does ────────────────────────────────────────────────────────

    def test_six_bars_agreeing_name_the_meter(self):
        """Six bars at 2.0 with a `2/4` read elsewhere: the length is the
        bars', the spelling is borrowed, and both are on the record."""
        log, src, dst = self._log([2.0] * 6)
        self._run(log, from_bars=True)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "derived_from_bars")
        self.assertEqual((v.value["numerator"], v.value["denominator"]), (2, 4))
        self.assertEqual(v.detail["length"], 2.0)
        self.assertEqual(v.detail["bars_agree"], 6)
        self.assertEqual(v.detail["bars_disagree"], 0)
        self.assertEqual(v.detail["support"], 6.0)
        self.assertEqual(v.detail["form_borrowed_from"], src.to_key())
        self.assertEqual(v.detail["instead_of"], "no_evidence")

    def test_a_segment_is_written_so_meter_at_answers(self):
        """`Q.METER` is a fact about a RANGE OF BARS however it was decided,
        so a derived meter must serialise like a read one."""
        log, _src, dst = self._log([2.0] * 6)
        self._run(log, from_bars=True)
        v = log.verdict(Q.METER, dst)
        self.assertEqual(R.meter_at(v.value, 0)["raw"], "2/4")
        self.assertEqual(R.meter_at(v.value, 5)["raw"], "2/4")

    # ── what it refuses ─────────────────────────────────────────────────────

    def test_it_CANNOT_cross_a_movement_boundary(self):
        """⚠️⚠️ THE STRUCTURAL SAFETY CLAIM, AND IT IS WHY THIS IS NOT A
        SECOND COPY OF THE CARRY.

        Every term comes from bars inside this ONE system, so a page opening a
        new movement cannot be handed the old movement's meter by this route
        however many pages of it precede. The shape is the real *Andante*'s:
        four assessable bars reading four different lengths (measured on
        Beethoven 5 / Litolff p.17 system 0 — 3.0, 3.5, 1.0, 1.5).
        """
        log, _src, dst = self._log([3.0, 3.5, 1.0, 1.5])
        self._run(log, from_bars=True)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_evidence")

    def test_three_bars_are_not_enough_however_well_they_agree(self):
        """⚠️ AND THE FLOOR IS THE ONLY THING REFUSING THEM.

        This test was written to pin a separate minimum-assessable-bars
        constant and it PASSED WITH THAT CONSTANT DELETED — a bar is worth
        1.0, so three of them score +3 and the floor refuses them anyway.
        The constant is gone; this now pins the floor's lower reach, which is
        what actually holds.
        """
        log, _src, dst = self._log([2.0] * 3)
        self._run(log, from_bars=True)
        self.assertIs(log.verdict(Q.METER, dst).outcome, Outcome.ABSTAINED)

    def test_a_length_NO_METER_PRINTS_is_not_a_candidate(self):
        """⚠️ Six bars unanimously one quarter-note long propose NOTHING.
        `rhythm._drop_implausible_meters` names `1/4` in its own docstring as
        garbage that survives upstream filtering; a bar-sum reader must not
        reintroduce it by the back door."""
        log, _src, dst = self._log([1.0] * 6)
        self._run(log, from_bars=True)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertNotIn(1.0, rhythm_mod._METER_LENGTHS)

    def test_a_split_page_scores_below_the_floor(self):
        """Eight bars, five agreeing and three not: +2, under the floor. The
        floor is what "the longer the more likely" cashes out as."""
        log, _src, dst = self._log([2.0] * 5 + [3.0, 4.0, 6.0])
        self._run(log, from_bars=True)
        self.assertIs(log.verdict(Q.METER, dst).outcome, Outcome.ABSTAINED)

    # ── the length / form split ─────────────────────────────────────────────

    def test_a_length_with_no_form_NAMES_THE_LENGTH_and_refuses(self):
        """⚠️ A REAL ANSWER, NOT A GAP: *these bars are three quarter-notes
        long, and nothing on this document has said whether that is printed
        3/4, 6/8 or 12/16*. Refusing to spell it is the point."""
        log, _src, dst = self._log([3.0] * 6, source=(2, 4), source_raw="2/4")
        self._run(log, from_bars=True)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "bars_name_a_length_without_a_form")
        self.assertEqual(v.detail["length"], 3.0)
        self.assertEqual(v.detail["support"], 6.0)
        self.assertEqual(sorted(v.detail["candidate_forms"]),
                         ["12/16", "3/4", "6/8"])

    def test_the_LETTER_form_is_never_borrowed(self):
        """⚠️⚠️ `raw` reaches `staged.export` as `symbol="common"`, which is a
        positive claim that a `C` is PRINTED on this system — and this system
        printed nothing we could read. The numbers are borrowed; the
        engraving is not, and the source's own `raw` is recorded beside the
        answer rather than copied into it."""
        log, _src, dst = self._log([4.0] * 6, source=(4, 4), source_raw="C")
        self._run(log, from_bars=True)
        v = log.verdict(Q.METER, dst)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual((v.value["numerator"], v.value["denominator"]), (4, 4))
        self.assertEqual(v.value["raw"], "4/4")
        self.assertEqual(v.detail["form_source_raw"], "C")
        from tools.omr.time_signature_locator import LETTER_METERS
        self.assertIn("C", LETTER_METERS)
        self.assertNotIn(v.value["raw"], LETTER_METERS)

    def test_a_borrowed_form_never_chains_onto_a_borrowed_form(self):
        """Only INK is a source. A `derived_from_bars` verdict is not a
        `voted` one, so it can never lend its spelling onward — the same
        discipline `_carry_meter` states for the carry."""
        log = Log()
        src, mid, far = R.system(0, 0), R.system(1, 0), R.system(2, 0)
        for sysj, n in ((src, 12), (mid, 11), (far, 11)):
            log.record(adjudicate.Verdict(
                id=log._next_id("vrd"), subject=sysj,
                quantity=Q.SYSTEM_STAFF_COUNT, outcome=Outcome.DECIDED,
                value=n, decider="t", reason="counted"))
        for i in range(12):
            log.observe(R.staff(0, 0, i), Q.METER_TEMPLATE, (2, 4),
                        reader=READERS.TEMPLATE, frame="header_window",
                        score=0.7, raw="2/4")
        self._bars(log, 1, [2.0] * 6)
        self._bars(log, 2, [2.0] * 6)
        self._run(log, from_bars=True)
        for sysj in (mid, far):
            v = log.verdict(Q.METER, sysj)
            self.assertEqual(v.reason, "derived_from_bars")
            # both name the READING, never each other
            self.assertEqual(v.detail["form_borrowed_from"], src.to_key())

    # ── the ordering ────────────────────────────────────────────────────────

    def test_it_never_overturns_a_system_that_read_its_own_meter(self):
        log, src, _dst = self._log([3.0] * 6)
        self._run(log, from_bars=True)
        self.assertEqual(log.verdict(Q.METER, src).reason, "voted")

    def test_the_CARRY_is_asked_first_where_both_could_speak(self):
        """⚠️ Reach, not merit: the carry names an ENGRAVING it actually saw,
        so where it stands there is nothing for a borrow to add."""
        log, _src, dst = self._log([2.0] * 6)
        self._run(log, from_bars=True, carry=True)
        self.assertEqual(log.verdict(Q.METER, dst).reason, "carried")

    def test_the_constants_keep_the_floor_reachable_by_a_real_page(self):
        """⚠️ A PROPERTY OF THE CONSTANTS, asserted on them directly so a
        sweep that broke it fails even when every behavioural test passes.

        The floor must sit at or below what the *Andante*'s own four
        assessable bars could score, so that page REACHES it and is refused
        by it — a floor no real negative can reach is justified by nothing.
        """
        self.assertGreater(rhythm_mod.METER_FROM_BARS_FLOOR,
                           rhythm_mod.W_METER_BAR_FITS
                           + 3 * rhythm_mod.W_METER_BAR_CONTRADICTS,
                           "the Andante's 1-agree/3-disagree must not stand")
        self.assertLessEqual(rhythm_mod.METER_FROM_BARS_FLOOR,
                             4 * rhythm_mod.W_METER_BAR_FITS,
                             "the Andante's four bars must still REACH the "
                             "floor, so a real page refuses them")
        self.assertFalse(hasattr(rhythm_mod, "METER_FROM_BARS_MIN_ASSESSABLE"),
                         "a gate that cannot fire reads as a protection that "
                         "is not there — see the constant's own note")
