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


class TestAGlyphStandingOnANeighbouringStaff(unittest.TestCase):
    """⚠️ A measure cell is the staff plus four staff spaces of air, so on a
    conductor's page a NEIGHBOURING staff's clef lands in this staff's cell —
    two clef glyphs, at nearly the same x and 250–350 canonical px apart in y,
    each scoring `W_DETECTOR_HIGH`. Five of the six staves whose clef could not
    decide across two scanned pages were an exact **3.0 against 3.0** tie for
    that reason, and 67 notes on Beethoven p3 had no pitch because of it.

    ⚠️ THE FILED FIX DOES NOT REACH THIS. `adjudicate_clef`'s first
    `checked_by` is the written-range test, which needs the INSTRUMENT — and
    instrument abstains on 22 of 22 and 27 of 27 staves of those pages. The
    glyph's own position needs no identity, which is what makes it usable on a
    scan.
    """

    def _staff(self, *glyphs):
        """`glyphs` = (class, score, position_steps or None)."""
        log = Log()
        st = R.staff(0, 0, 0)
        for i, (name, score, pos) in enumerate(glyphs):
            log.observe(st, Q.CLEF_GLYPH, name, reader=READERS.DETECTOR,
                        frame="cell:0", score=score, y_center=100 * i)
            if pos is not None:
                log.observe(st, Q.CLEF_POSITION, pos, reader=READERS.GEOMETRY,
                            frame="cell:0", glyph=name, y_center=100 * i)
        log.freeze()
        adjudicate._ensure_decisions()
        return adjudicate.adjudicate_one(
            log, adjudicate.REGISTRY[Q.CLEF], st)

    def test_the_tie_that_abstained_now_decides(self):
        """The measured shape: one glyph at +3.2 steps, one at −4.8."""
        v = self._staff(("clefF", 0.88, 3.2), ("clefG", 0.95, -4.8))
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, "bass")

    def test_without_the_position_it_still_abstains(self):
        """The control: the SAME two readings with no grid measured tie at
        3.0 and 3.0, which is what they did before this evidence existed."""
        v = self._staff(("clefF", 0.88, None), ("clefG", 0.95, None))
        self.assertIsNot(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "margin_below_floor")

    def test_a_lone_glyph_standing_OFF_the_staff_is_still_the_best_evidence(self):
        """⚠️ ADDITIVE, NEVER A FILTER. Removing an off-staff glyph's term
        would make an arbitration invisibly, and it would be the wrong call
        where a staff's only candidate stands off it."""
        v = self._staff(("clefG", 0.90, 13.6))
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, "treble")

    def test_an_UNMEASURED_position_is_not_read_as_off_the_staff(self):
        """`None` means the cell had no grid. Treating that as "off the staff"
        would silently withdraw the detector's evidence on exactly the pages
        whose geometry is worst."""
        on = self._staff(("clefG", 0.90, None), ("clefF", 0.40, -9.0))
        self.assertEqual(on.value, "treble")   # decided on confidence alone

    def test_the_term_is_worth_more_than_the_margin_floor(self):
        """The population it is for is an EXACT tie, so a term that only
        matches the floor leaves it abstaining."""
        from tools.omr.staged.adjudicators import clef as C
        self.assertGreater(C.W_ON_THIS_STAFF, C.MARGIN_FLOOR)

    def test_the_band_is_wider_than_the_staff_on_purpose(self):
        """A clef's BOX centre is not its notated line, and the measured
        separation is 8 steps clear on the near side — so nothing needs a
        tight band, and a tight one would start deciding cases the evidence
        does not separate."""
        from tools.omr.staged.adjudicators import clef as C
        self.assertLess(C.ON_STAFF_MIN_STEPS, 0.0)
        self.assertGreater(C.ON_STAFF_MAX_STEPS, 8.0)
        for measured in (3.1, 3.2, 3.3, 3.4, 3.5):
            self.assertTrue(C.ON_STAFF_MIN_STEPS <= measured
                            <= C.ON_STAFF_MAX_STEPS)
        for measured in (-6.9, -5.8, -4.8, 13.3, 13.6, 14.8):
            self.assertFalse(C.ON_STAFF_MIN_STEPS <= measured
                             <= C.ON_STAFF_MAX_STEPS)



class TestASuppliedClefSpeaksOnlyWhereThePageDidNot(unittest.TestCase):
    """⚠️⚠️ GAPS ONLY, and the weight is why it had to be structural.

    A clef supplied by a confirmed session fact sheet is the one term in this
    decision that did not come off the page at all, and `W_DOSSIER` (4.0)
    stands ABOVE `W_DETECTOR_HIGH` (3.0). So before this rule a supplied clef
    did not corroborate a read one, it REPLACED it -- silently, and including
    where the reading was right and the sheet held a typo.

    Sean, 2026-09-21: *"redo our work tonight to be an option to turn on when
    we can't get the info we need."* The information we could not get is the
    only place it may speak, which is the `adjudicate_key_signature`
    precedent inherited rather than re-litigated.

    ⚠️ RED PROOF, STATED EXACTLY. Against the previous `_carry_terms` (the
    seed admitted everywhere) **three of these seven go red**: the two
    overturn tests and the recorded-refusal one. The first draft of this
    docstring claimed all seven did, which was false and is the precise shape
    this file warns about elsewhere -- *a test named for a hazard it does not
    reach*, written into the summary rather than the body. The other four are
    deliberately NOT red, and each is load-bearing for a different reason:
    `test_it_decides_a_staff_the_page_said_NOTHING_about` is the POSITIVE
    CONTROL (without it the three red ones would pass for a rule that threw
    every seed away); the absent-key test and the carry test guard what must
    NOT change; and the weight-ordering test pins the premise that makes the
    whole rule necessary.
    """

    def _seed(self, log, name="alto"):
        log.observe(SUB, Q.CLEF_SEED, name, reader=READERS.DOSSIER,
                    frame="page", tier="dossier")

    def test_it_decides_a_staff_the_page_said_NOTHING_about(self):
        """The whole point of supplying it. Without this the change would be
        a refusal with no upside, and the other tests would pass for a rule
        that simply threw every seed away."""
        log = _log()
        self._seed(log, "tenor")
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, "tenor")

    def test_it_does_NOT_overturn_a_clef_the_detector_read(self):
        log = _log()
        log.observe(SUB, Q.CLEF_GLYPH, "clefG", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.95)
        self._seed(log, "alto")
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertEqual(v.value, "treble",
                         "the supplied clef outvoted a read one")

    def test_it_does_NOT_overturn_a_clef_the_LOCATOR_read(self):
        """⚠️ The locator weighs 2.0, BELOW the seed's 4.0 -- so a weight
        tweak alone would not have covered this staff. The gap test is on
        whether the page spoke, not on how loudly."""
        log = _log()
        log.observe(SUB, Q.CLEF_LOCATED, "tenor", reader=READERS.CV_LOCATOR,
                    frame="header_window", score=0.88, family="C", line=4)
        self._seed(log, "alto")
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.CLEF, SUB).value, "tenor")

    def test_the_refusal_is_RECORDED_rather_than_silent(self):
        """A supplied clef that disagreed with a page that spoke is the one
        signal a gaps-only rule would otherwise throw away."""
        log = _log()
        log.observe(SUB, Q.CLEF_GLYPH, "clefG", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.95)
        self._seed(log, "alto")
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertEqual(
            v.detail.get("supplied_clefs_withheld_because_the_page_spoke"), 1)

    def test_nothing_is_recorded_when_nothing_was_withheld(self):
        """The key is absent rather than zero -- *a null key is still a key*,
        and a reader scanning for withheld seeds must not find one on every
        staff in the document."""
        log = _log()
        self._seed(log, "tenor")
        adjudicate.run(log)
        self.assertNotIn(
            "supplied_clefs_withheld_because_the_page_spoke",
            log.verdict(Q.CLEF, SUB).detail)

    def test_the_CARRY_tier_is_untouched_by_the_gap_rule(self):
        """⚠️ `clef_continuity`'s mechanism is the ONE carry in this pipeline
        that survives, it was measured, and it is not what Sean asked to
        change. A rule that quietly took it with the seed would be a second,
        unpriced change riding on the first."""
        log = _log()
        log.observe(SUB, Q.CLEF_GLYPH, "clefF", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.30)
        log.observe(SUB, Q.CLEF_SEED, "treble", reader=READERS.DOSSIER,
                    frame="page", tier="carry")
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        # The carry still contributes: with a weak detector reading, its 1.5
        # reaches the contest at all, which a withheld term could not.
        self.assertIn("treble", v.detail.get("scores", {}))
        self.assertNotIn(
            "supplied_clefs_withheld_because_the_page_spoke", v.detail,
            "the gap rule swallowed the CARRY tier as well as the seed")

    def test_the_weight_ordering_that_MAKES_this_necessary_still_holds(self):
        """⚠️ If `W_DOSSIER` ever falls below `W_DETECTOR_HIGH`, this rule
        stops being load-bearing and somebody will delete it as redundant.
        It would not be: a supplied clef could still out-vote a PAIR of weak
        read terms. Pinning the ordering keeps the reason legible."""
        self.assertGreater(clef_mod.W_DOSSIER, clef_mod.W_DETECTOR_HIGH)
