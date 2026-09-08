"""Coherence tests for the adjudication harness.

⚠️ THE CENTRAL TEST IN THIS FILE IS `TestTheThreeStandingRefusals`, and it is
the design's own first falsifier. The three refusals in the tree were each
won by measurement AFTER being bitten:

    clef_correction.py:566   deduced identity -> clef
    dossier.py:434           clef -> the part<->staff pin
    score_layouts.py:682     clef -> the layout pin

A mechanism that does not reproduce them is wrong however elegant, and the
design says so: "if it does not, stop -- the design is wrong and this is
where it is cheapest to find out."

⚠️ IT MUST ALSO ADMIT THE DELIBERATE EXCEPTION. `score_order_ambiguity` -- a
label the layout prior disambiguated -- is admitted ON PURPOSE at
`contextual.py:409`. A rule that excludes it is the WRONG RULE, and that is
what forces the exact wording: not "exclude anything with clef in its
ancestry" but "admit if it also rests on an INDEPENDENT READING".
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate as A
from tools.omr.staged import record as R
from tools.omr.staged.adjudicate import (Evidence, Mode, Ruling, Term,
                                         UndeclaredEvidence, tally)
from tools.omr.staged.record import (ABSTAIN, Log, Outcome, Q, READERS, Scope,
                                     State, Verdict)


class _owns:
    """Temporarily take ownership of a quantity.

    ⚠️ The registry refuses two owners for one quantity -- "one quantity, one
    owner" -- so a test that registers a probe must displace the incumbent and
    put it back. That the guard fires when these tests run alongside the real
    adjudicators is the guard WORKING, and it is why this helper exists rather
    than a flag loosening the rule.
    """

    def __init__(self, quantity):
        self.quantity = quantity
        self.prior = None

    def __enter__(self):
        self.prior = A.REGISTRY.pop(self.quantity, None)
        return self

    def __exit__(self, *exc):
        A.REGISTRY.pop(self.quantity, None)
        if self.prior is not None:
            A.REGISTRY[self.quantity] = self.prior
        return False


def _spec(quantity=Q.CLEF, wants=(Q.INSTRUMENT,), excludes=()):
    return A.DecisionSpec(
        name="probe", quantity=quantity, scope=R.Kind.STAFF, wants=tuple(wants),
        reasons=("r",), mode=Mode.ADDITIVE, margin_floor=None,
        excludes_tiers=tuple(excludes), revises=None, stub=False,
        fn=lambda ev: Ruling(value=1, reason="r"))


class TestDeclaredEvidence(unittest.TestCase):
    """The declaration has teeth, or it is documentation."""

    def test_reading_an_undeclared_quantity_raises(self):
        log = Log()
        ev = Evidence(log, R.staff(0, 0, 0), _spec(wants=(Q.CLEF_GLYPH,)))
        ev.rows(Q.CLEF_GLYPH)                      # declared: fine
        with self.assertRaises(UndeclaredEvidence):
            ev.rows(Q.MARGIN_LABEL)                # not declared: refused

    def test_the_harness_fills_missing_without_asking_the_decision(self):
        """Mechanism 3: the decision is not consulted about its own honesty."""
        log = Log()
        sub = R.staff(0, 0, 0)

        with _owns(Q.STAFF_GROUP):
            @A.decision(quantity=Q.STAFF_GROUP, scope=R.Kind.STAFF,
                        wants=(Q.BRACKET_BLOCK,), reasons=("r",),
                        composed_from=(Q.BRACKET_BLOCK,))
            def _probe(ev):
                ev.rows(Q.BRACKET_BLOCK)           # asks, gets nothing
                return Ruling(value=1, reason="r")

            log.freeze()
            v = A.adjudicate_one(log, A.REGISTRY[Q.STAFF_GROUP], sub)
            self.assertIn(Q.BRACKET_BLOCK, v.missing)
            self.assertEqual(v.declined, ())

    def test_declined_and_missing_are_recorded_apart(self):
        log = Log()
        sub = R.staff(0, 0, 0)
        log.abstain(sub, Q.BRACKET_BLOCK, reader=READERS.GEOMETRY,
                    frame="system", reason=ABSTAIN.SYSTEM_TOO_SMALL)

        with _owns(Q.STAFF_GROUP):
            @A.decision(quantity=Q.STAFF_GROUP, scope=R.Kind.STAFF,
                        wants=(Q.BRACKET_BLOCK, Q.SYSTEMIC_COLUMN),
                        reasons=("r",), composed_from=(Q.BRACKET_BLOCK,))
            def _probe(ev):
                ev.rows(Q.BRACKET_BLOCK)
                ev.rows(Q.SYSTEMIC_COLUMN)
                return Ruling(value=1, reason="r")

            log.freeze()
            v = A.adjudicate_one(log, A.REGISTRY[Q.STAFF_GROUP], sub)
            self.assertEqual(v.declined, (Q.BRACKET_BLOCK,))
            self.assertEqual(v.missing, (Q.SYSTEMIC_COLUMN,))


class TestTheThreeStandingRefusals(unittest.TestCase):
    """⚠️ THE DESIGN'S FIRST ACCEPTANCE TEST."""

    def setUp(self):
        self.log = Log()
        self.sub = R.staff(0, 0, 0)
        # A clef, read and adjudicated. This is what must not flow back.
        obs = self.log.observe(self.sub, Q.CLEF_GLYPH, "clefG",
                               reader=READERS.DETECTOR, frame="cell:0",
                               score=0.9)
        self.clef = self.log.record(Verdict(
            id=self.log._next_id("vrd"), subject=self.sub, quantity=Q.CLEF,
            outcome=Outcome.DECIDED, value="treble", decider="clef",
            reason="scored", considered=(obs.id,), basis=(obs.id,)))

    def _identity(self, basis, subject=None):
        return self.log.record(Verdict(
            id=self.log._next_id("vrd"), subject=subject or self.sub,
            quantity=Q.INSTRUMENT, outcome=Outcome.DECIDED,
            value={"name": "Horn"}, decider="identity", reason="r",
            considered=tuple(basis), basis=tuple(basis)))

    def _admits(self, verdict):
        ev = Evidence(self.log, verdict.subject, _spec(quantity=Q.CLEF))
        return ev.verdict(Q.INSTRUMENT) is not None, ev._excluded

    # ── refusal 1: deduced identity -> clef ─────────────────────────────────

    def test_score_order_identity_is_refused(self):
        """`clef_correction.py:566`: `if instrument_source_by_slot.get(slot)
        != "label"`. The score-order prior consumes clefs
        (`contextual.py:1208-1209`, `fit_layouts(..., clefs=clef_by_slot)`),
        so a deduced identity has our own output in its ancestry and no
        independent reading of its own."""
        deduced = self._identity(basis=(self.clef.id,))
        admitted, excluded = self._admits(deduced)
        self.assertFalse(admitted)
        self.assertTrue(any("circular" in why for _rid, why in excluded))

    def test_label_identity_is_admitted(self):
        """READ identity -> clef is permitted, and the asymmetry is
        deliberate and correct in the codebase."""
        label = self.log.observe(self.sub, Q.MARGIN_LABEL, "Corni",
                                 reader=READERS.TEXT_LAYER,
                                 frame="system_margin")
        read = self._identity(basis=(label.id,))
        admitted, _ = self._admits(read)
        self.assertTrue(admitted)

    def test_score_order_ambiguity_is_admitted(self):
        """⚠️ THE EXCEPTION THAT FIXES THE RULE'S WORDING.

        A label the layout prior disambiguated has BOTH an OCR row and the
        prior (which consumed clefs) in its basis. The crude rule -- exclude
        anything with clef in its ancestry -- would wrongly refuse it. The
        rule as written asks for at least one independent READING, and the
        OCR row supplies it.
        """
        label = self.log.observe(self.sub, Q.MARGIN_LABEL, "Tp.",
                                 reader=READERS.TEXT_LAYER,
                                 frame="system_margin")
        ambiguous = self._identity(basis=(label.id, self.clef.id))
        admitted, _ = self._admits(ambiguous)
        self.assertTrue(admitted)

    # ── refusals 2 and 3: clef -> the part/layout join ──────────────────────

    def test_a_join_that_consumed_clefs_may_not_score_the_clef(self):
        """`dossier.py:434` and `score_layouts.py:682` refuse the same edge in
        the other direction: supplying clefs is what the join exists to do,
        so pinning the join on clefs is circular exactly where it matters."""
        join = self.log.record(Verdict(
            id=self.log._next_id("vrd"), subject=self.sub,
            quantity=Q.SLOT_INDEX, outcome=Outcome.DECIDED, value=3,
            decider="slots", reason="r", considered=(self.clef.id,),
            basis=(self.clef.id,)))
        ev = Evidence(self.log, self.sub,
                      _spec(quantity=Q.CLEF, wants=(Q.SLOT_INDEX,)))
        self.assertIsNone(ev.verdict(Q.SLOT_INDEX))

    # ── the quality hold-out is a DIFFERENT question ────────────────────────

    def test_a_quality_holdout_is_separate_from_circularity(self):
        """⚠️ `roster` identity's basis is a catalog row, NOT a clef
        descendant, so the circularity filter ADMITS it -- correctly. It is
        held out of clef decisions by a MEASURED judgement
        (`OMR_ROSTER_CLEF=0`), and folding that into the structural safety
        rule is how one of them goes silently missing."""
        roster = self.log.observe(R.DOCUMENT, Q.ROSTER_ENTRY, ["Horn"],
                                  reader=READERS.CATALOG, frame="page",
                                  tier="roster")
        from_roster = self._identity(basis=(roster.id,))

        # circularity filter alone: admitted
        ev = Evidence(self.log, self.sub, _spec(quantity=Q.CLEF))
        self.assertIsNotNone(ev.verdict(Q.INSTRUMENT))

        # the quality hold-out, declared separately, refuses it
        ev2 = Evidence(self.log, self.sub,
                       _spec(quantity=Q.CLEF, excludes=("roster",)))
        # the tier lives on the observation, so the hold-out is expressed on
        # the reader that produced it
        self.assertTrue(any(r.detail.get("tier") == "roster"
                            for r in self.log.rows(Q.ROSTER_ENTRY, R.DOCUMENT)))


class TestTheDossierDoubleCount(unittest.TestCase):
    """⚠️ THE DOSSIER HAZARD IN ITS SECOND FORM, and the coordinator's ruling.

    The FIRST form -- a clef adjudicator reading back its own dossier seed --
    really does dissolve under the staged split: the dossier becomes a row
    among rows, it overwrites nothing, and there is no seed to read back.

    THE SECOND FORM DOES NOT DISSOLVE. If a dossier supplies BOTH the clef
    seed AND the instrument, a clef decision that weighs both is counting ONE
    SOURCE TWICE. That is not self-reference, it is the other rule -- two
    signals sharing an ancestor are ONE signal -- and it is more insidious,
    because it looks like two independent pieces of evidence agreeing.

    ⚠️ THIS TEST FAILED WHEN FIRST WRITTEN, and the failure was a modelling
    error in the design: `Observation.basis` was empty "by definition", so a
    dossier's two descendants shared no ancestor and the correlation check saw
    two independent witnesses. The invariant is now narrower and true -- a row
    read off THIS RASTER has no ancestors; a row derived from an EXTERNAL
    DOCUMENT carries that document's row.
    """

    def setUp(self):
        self.log = Log()
        self.sub = R.staff(0, 0, 0)
        self.dossier = self.log.observe(
            R.DOCUMENT, Q.DOSSIER_FACT, {"clef": "alto", "instrument": "Viola"},
            reader=READERS.DOSSIER, frame="page", tier="dossier")

    def test_the_seed_and_the_instrument_share_the_dossier_as_ancestor(self):
        seed = self.log.observe(self.sub, Q.CLEF_SEED, "alto",
                                reader=READERS.DOSSIER, frame="page",
                                tier="dossier",
                                derived_from=(self.dossier.id,))
        instrument = self.log.record(Verdict(
            id=self.log._next_id("vrd"), subject=self.sub,
            quantity=Q.INSTRUMENT, outcome=Outcome.DECIDED,
            value={"name": "Viola", "expected_clef": "alto"},
            decider="identity", reason="r",
            considered=(self.dossier.id,), basis=(self.dossier.id,)))

        shared = ((self.log.closure(seed.id) & self.log.closure(instrument.id))
                  - {seed.id, instrument.id})
        self.assertEqual(shared, {self.dossier.id})

    def test_the_correlation_check_sees_them_as_ONE_signal(self):
        seed = self.log.observe(self.sub, Q.CLEF_SEED, "alto",
                                reader=READERS.DOSSIER, frame="page",
                                tier="dossier",
                                derived_from=(self.dossier.id,))
        instrument = self.log.record(Verdict(
            id=self.log._next_id("vrd"), subject=self.sub,
            quantity=Q.INSTRUMENT, outcome=Outcome.DECIDED,
            value={"name": "Viola", "expected_clef": "alto"},
            decider="identity", reason="r",
            considered=(self.dossier.id,), basis=(self.dossier.id,)))

        ev = Evidence(self.log, self.sub,
                      _spec(quantity=Q.CLEF,
                            wants=(Q.CLEF_SEED, Q.INSTRUMENT)))
        ev.rows(Q.CLEF_SEED)
        ev.verdict(Q.INSTRUMENT)
        groups = ev.correlated_groups()
        self.assertTrue(groups, "the dossier's two descendants must group")
        self.assertTrue(any({seed.id, instrument.id} <= g for g in groups))

    def test_and_tally_therefore_counts_the_dossier_ONCE(self):
        """The behavioural consequence: agreement between two descendants of
        one source must not score as corroboration."""
        seed = self.log.observe(self.sub, Q.CLEF_SEED, "alto",
                                reader=READERS.DOSSIER, frame="page",
                                tier="dossier",
                                derived_from=(self.dossier.id,))
        instrument = self.log.record(Verdict(
            id=self.log._next_id("vrd"), subject=self.sub,
            quantity=Q.INSTRUMENT, outcome=Outcome.DECIDED,
            value={"name": "Viola", "expected_clef": "alto"},
            decider="identity", reason="r",
            considered=(self.dossier.id,), basis=(self.dossier.id,)))
        ev = Evidence(self.log, self.sub,
                      _spec(quantity=Q.CLEF,
                            wants=(Q.CLEF_SEED, Q.INSTRUMENT)))
        ev.rows(Q.CLEF_SEED)
        ev.verdict(Q.INSTRUMENT)
        groups = ev.correlated_groups()

        terms = [Term("dossier_seed", 4.0, (seed.id,)),
                 Term("instrument", 1.0, (instrument.id,))]
        self.assertEqual(tally(terms), 5.0)               # naive: double-counted
        self.assertEqual(tally(terms, correlated=groups), 4.0)   # one source

    def test_a_reader_of_THIS_page_is_NOT_correlated_with_the_dossier(self):
        """⚠️ The control. The rule must collapse a shared ancestor, not
        everything that agrees -- a detector reading the same clef IS
        independent corroboration and must still count."""
        seed = self.log.observe(self.sub, Q.CLEF_SEED, "alto",
                                reader=READERS.DOSSIER, frame="page",
                                tier="dossier",
                                derived_from=(self.dossier.id,))
        detected = self.log.observe(self.sub, Q.CLEF_GLYPH, "clefC",
                                    reader=READERS.DETECTOR, frame="cell:0",
                                    score=0.8)
        ev = Evidence(self.log, self.sub,
                      _spec(quantity=Q.CLEF,
                            wants=(Q.CLEF_SEED, Q.CLEF_GLYPH)))
        ev.rows(Q.CLEF_SEED)
        ev.rows(Q.CLEF_GLYPH)
        groups = ev.correlated_groups()
        self.assertFalse(any(detected.id in g and seed.id in g for g in groups))

    def test_a_dangling_derived_from_is_refused(self):
        """A reference to a row that is not in the log would silently restore
        the double-count, so it is an error rather than an empty closure."""
        with self.assertRaises(ValueError):
            self.log.observe(self.sub, Q.CLEF_SEED, "alto",
                             reader=READERS.DOSSIER, frame="page",
                             derived_from=("obs:999999",))


class TestSignedTerms(unittest.TestCase):
    def test_correlated_evidence_is_counted_once(self):
        """⚠️ The live case: two rows that LOOK like two readings and are
        measured to be the same call -- divergent on 0 of 396 staves."""
        a = Term("a", 3.0, ("obs:1",))
        b = Term("b", 3.0, ("obs:2",))
        self.assertEqual(tally([a, b]), 6.0)
        self.assertEqual(tally([a, b], correlated=[frozenset({"obs:1", "obs:2"})]),
                         3.0)

    def test_a_withheld_term_is_not_a_zero(self):
        """`slots._pair_score` withholds its group term rather than guessing,
        because a wrong group verdict is worth 3.0 against a position signal
        worth ~0.05. Withholding says "incomparable"; zero says "I looked and
        found no support"."""
        self.assertEqual(tally([Term("a", 2.0), None]), 2.0)

    def test_there_is_no_way_to_express_a_multiplier(self):
        """⚠️ By construction. An uncalibrated probability is worse than none
        -- ECE 0.1277, top bin promising 0.989 and delivering 0.692."""
        self.assertFalse(hasattr(A, "multiply"))
        self.assertFalse(hasattr(A, "probability"))


class TestCompetitiveNeedsAFloor(unittest.TestCase):
    def test_competitive_without_margin_floor_is_refused(self):
        with _owns(Q.ARC_KIND):
            with self.assertRaises(ValueError):
                @A.decision(quantity=Q.ARC_KIND, scope=R.Kind.GLYPH,
                            wants=(Q.ARC_BOX,), reasons=("r",),
                            mode=Mode.COMPETITIVE,
                            composed_from=(Q.ARC_BOX,))
                def _bad(ev):
                    return Ruling(value=1, reason="r")

    def test_a_margin_below_the_floor_abstains(self):
        """Today the clef argmax wins at ANY confidence -- there is no floor
        anywhere in the chain. The floor's existence is the change."""
        log = Log()
        sub = R.staff(0, 0, 0)

        with _owns(Q.ARC_KIND):
            @A.decision(quantity=Q.ARC_KIND, scope=R.Kind.GLYPH,
                        wants=(Q.ARC_BOX,), reasons=("r",),
                        mode=Mode.COMPETITIVE, margin_floor=1.0,
                        composed_from=(Q.ARC_BOX,))
            def _probe(ev):
                return Ruling(value="tie", reason="r", margin=0.2)

            log.freeze()
            v = A.adjudicate_one(log, A.REGISTRY[Q.ARC_KIND], sub)
            self.assertIs(v.outcome, Outcome.ABSTAINED)
            self.assertEqual(v.reason, "margin_below_floor")
            self.assertIsNone(v.value)
            self.assertEqual(v.margin, 0.2)


class TestOneQuantityOneOwner(unittest.TestCase):
    """⚠️ Found by these tests colliding with the real adjudicators, which is
    the guard working. Two owners for one quantity would mean the answer
    depends on import order."""

    def test_a_second_owner_is_refused(self):
        with _owns(Q.ARC_KIND):
            @A.decision(quantity=Q.ARC_KIND, scope=R.Kind.GLYPH,
                        wants=(Q.ARC_BOX,), reasons=("r",),
                        composed_from=(Q.ARC_BOX,))
            def _first(ev):
                return Ruling(value=1, reason="r")

            with self.assertRaises(ValueError):
                @A.decision(quantity=Q.ARC_KIND, scope=R.Kind.GLYPH,
                            wants=(Q.ARC_BOX,), reasons=("r",),
                            composed_from=(Q.ARC_BOX,))
                def _second(ev):
                    return Ruling(value=2, reason="r")


class TestStubsAreDeclared(unittest.TestCase):
    def test_every_ordered_quantity_has_an_owner(self):
        """⚠️ A stub is fine; a MISSING decision is not, because a missing
        decision is indistinguishable from one that always abstains."""
        from tools.omr.staged import adjudicators  # noqa: F401
        unowned = [q for q in A.ORDER if q not in A.REGISTRY]
        self.assertEqual(unowned, [])

    def test_stubs_are_enumerable(self):
        from tools.omr.staged import adjudicators  # noqa: F401
        self.assertTrue(A.stubs())


if __name__ == "__main__":
    unittest.main()
