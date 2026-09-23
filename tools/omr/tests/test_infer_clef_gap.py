"""Roadmap 2.10 — the unread clef on a part the record has already placed.

Sean, 2026-09-23: *"yes — viola staff with unreadable clef reads as alto and
it should check other systems if the alto clef can be found"*
(`docs/DECISIONS.md`).

⚠️ THIS FILE IS RED ON THE TREE IT WAS WRITTEN AGAINST, and that is checkable
with one command rather than asserted here:

    git grep -n -e CLEF_GAP_SWITCH -e clef_gap_enabled -e inferred_in_basis \
        -e 'def run_over' -e reads_beyond_cause -e clef_gap_census \
        -e 'def fill_clef_gap' -e _move_glyph_also_reads 1c9cf26c -- tools/

returns NOTHING. Every symbol this module imports or reaches for was absent at
`1c9cf26c`, so the file could not import there, let alone pass — which is the
RED this suite claims, and not a battery that passes by refusing everything.
(`instrument_named` alone existed, as a second linear scan in
`score_language.py`; that one now delegates.)

⚠️ NO TEST HERE ASSERTS ON MODULE SOURCE TEXT. The fixtures are real `Log`s
and every assertion is about a verdict the machine wrote.
"""

import os
import unittest
from unittest import mock

from tools.omr.instruments import instrument_named
from tools.omr.staged import consequences  # noqa: F401 -- registers EVALUATE
from tools.omr.staged import evaluate, infer, inferences
from tools.omr.staged.record import (Candidate, Kind, Log, Outcome, Q, Subject,
                                     Verdict)

DOC = Subject(Kind.DOCUMENT)


def _rules():
    """The registered INFER rules, loaded.

    ⚠️ `infer.RULES` IS LAZY AND THE SUITE MUTATES IT. `_ensure_rules` imports
    `inferences` only while the list is empty, so a helper elsewhere that
    cleared it leaves the stage permanently ruleless for the process; and
    `test_infer_bypass` RELOADS `tools.omr.staged.infer`, which rebuilds the
    `Inference` enum -- so a registered rule's `inference` is then a member of
    the OLD class and `is infer.Inference.X` silently matches nothing. Both
    faults surface here as a bare `StopIteration` in a passing-alone file, so
    this loads the rules and every lookup below goes by NAME.
    """
    infer._ensure_rules()
    return list(infer.RULES)


def _registered(name: str):
    return next(r for r in _rules() if r.inference.value == name)


def _staff(page: int, system: int, staff: int) -> Subject:
    return Subject(Kind.STAFF, page=page, system=system, staff=staff)


def _glyph(page: int, system: int, staff: int, cell: int = 0,
           glyph: int = 0) -> Subject:
    return Subject(Kind.GLYPH, page=page, system=system, staff=staff,
                   cell=cell, glyph=glyph)


def _verdict(log: Log, subject: Subject, quantity: str, value, *,
             outcome=Outcome.DECIDED, decider="test", reason="read",
             candidates=(), detail=None, basis=()) -> Verdict:
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=subject, quantity=quantity,
        outcome=outcome, value=value, decider=decider, reason=reason,
        candidates=tuple(candidates), basis=tuple(basis),
        detail=dict(detail or {})))


class _Doc:
    """A document of N systems carrying one part on one slot.

    ⚠️ A REAL `Log`, not a stub. The rule reads `log.subjects(Kind.STAFF)`,
    `log.verdict(...)` and `Log.closure` through `independent_groups`, and a
    fake standing in for any of those would test the fixture.
    """

    def __init__(self, clefs, *, slot=9, instrument="Viola",
                 slot_outcome=Outcome.DECIDED, positions=()):
        """`clefs[i]` is system i's clef, or None for an ABSTAINED one."""
        self.log = Log()
        self.staves = []
        for i, clef in enumerate(clefs):
            s = _staff(0, i, 3)
            self.staves.append(s)
            decided = slot_outcome is Outcome.DECIDED
            _verdict(self.log, s, Q.SLOT_INDEX,
                     slot if decided else None, outcome=slot_outcome,
                     reason="paired_by_name" if decided
                     else "family_block_not_forced",
                     candidates=() if decided
                     else (Candidate(slot, 1.0), Candidate(slot + 1, 1.0)),
                     detail={"instrument": instrument})
            if clef is None:
                _verdict(self.log, s, Q.CLEF, None,
                         outcome=Outcome.ABSTAINED, decider="adjudicate_clef",
                         reason="no_candidates")
            elif isinstance(clef, tuple):      # ("narrowed", a, b)
                _verdict(self.log, s, Q.CLEF, None, outcome=Outcome.NARROWED,
                         decider="adjudicate_clef",
                         reason="margin_below_floor",
                         candidates=[Candidate(c, 1.0) for c in clef[1:]])
            else:
                _verdict(self.log, s, Q.CLEF, clef, decider="adjudicate_clef",
                         reason="scored")
        for (i, cell, glyph, pos) in positions:
            self.log.observe(_glyph(0, i, 3, cell, glyph),
                             Q.NOTEHEAD_STAFF_POSITION, float(pos),
                             reader="cv_lines", frame=f"cell:{cell}")
        self.log.freeze()

    def census(self):
        return {g.staff.to_key(): g for g in inferences.clef_gap_census(self.log)}

    def infer(self):
        return infer.run(self.log, evaluate.Report([], [], []))

    def clef(self, i):
        return self.log.verdict(Q.CLEF, self.staves[i])


class TestTheFlag(unittest.TestCase):
    """⚠️ DEFAULT ON, so the test is a DENY-list (`docs/flags-2026-09.md`,
    CLAUDE.md §7). A default-ON flag written as an allow-list is switched off
    by a typo, which is the one thing a shipped rule's gate must not do."""

    def test_on_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertTrue(infer.clef_gap_enabled())

    def test_a_typo_does_not_switch_it_off(self):
        for bad in ("1", "yess", "ON!", "TRUE", "maybe"):
            with mock.patch.dict(os.environ, {infer.CLEF_GAP_ENV: bad}):
                self.assertTrue(infer.clef_gap_enabled(), bad)

    def test_the_off_words_work(self):
        """⚠️ THE POSITIVE CONTROL. Without it the predicate could be
        `lambda: True` and every test above would still pass."""
        for good in ("0", "", "false", "NO", "off"):
            with mock.patch.dict(os.environ, {infer.CLEF_GAP_ENV: good}):
                self.assertFalse(infer.clef_gap_enabled(), good)

    def test_the_rule_has_its_own_switch_and_it_is_not_the_others(self):
        r = _registered("fill_clef_gap")
        self.assertEqual(r.switch.env, infer.CLEF_GAP_ENV)
        self.assertNotEqual(r.switch.env, infer.INFER_ENV)
        self.assertNotEqual(r.switch.env, infer.FAMILY_BLOCK_ENV)

    def test_off_means_the_rule_does_not_run_and_the_report_names_the_flag(self):
        d = _Doc(["alto", "alto", None])
        with mock.patch.dict(os.environ, {infer.CLEF_GAP_ENV: "0"}):
            rep = d.infer()
        self.assertEqual(
            [i for i in rep.inferred if i[0] == "fill_clef_gap"], [])
        self.assertIn((("fill_clef_gap"), infer.CLEF_GAP_ENV), rep.disabled)
        self.assertIs(d.clef(2).outcome, Outcome.ABSTAINED)


class TestTierTwoTheSamePartOnOtherSystems(unittest.TestCase):

    def test_two_systems_decided_alto_so_the_third_takes_alto(self):
        d = _Doc(["alto", "alto", None])
        rep = d.infer()
        v = d.clef(2)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, "alto")
        self.assertEqual(v.reason, "clef_from_other_systems")
        self.assertTrue(v.detail["inferred"])
        self.assertIn(("fill_clef_gap", d.staves[2].to_key(), v.id),
                      rep.inferred)

    def test_the_basis_names_the_two_systems_that_said_so(self):
        """⚠️ THE WITNESSES BY ID, not a count. A rule that reports 'two
        agreed' without naming which two cannot be checked against the page,
        and this repository has already shipped one figure that was a
        computation of another figure rather than a measurement."""
        d = _Doc(["alto", "alto", None])
        d.infer()
        v = d.clef(2)
        want = {d.clef(0).id, d.clef(1).id}
        self.assertTrue(want <= set(v.basis), (want, v.basis))
        self.assertEqual(set(v.used), want)
        self.assertEqual(v.detail["tally"], {"alto": 2})
        self.assertEqual(v.detail["n_agreeing"], 2)

    def test_the_prior_abstention_survives_underneath(self):
        d = _Doc(["alto", "alto", None])
        before = d.clef(2).id
        d.infer()
        self.assertEqual(d.clef(2).supersedes, before)
        prior = d.log.row(before)
        self.assertIs(prior.outcome, Outcome.ABSTAINED)
        self.assertEqual(prior.reason, "no_candidates")

    def test_a_split_abstains(self):
        """Sean: *a split abstains*. Not the alphabetical winner, and NOT a
        fall-through to the instrument's convention either."""
        d = _Doc(["treble", "alto", None])
        d.infer()
        self.assertIs(d.clef(2).outcome, Outcome.ABSTAINED)
        g = d.census()[d.staves[2].to_key()]
        self.assertEqual(g.outcome, "split")
        self.assertEqual(g.detail["tally"], {"alto": 1, "treble": 1})

    def test_a_majority_is_enough_and_the_dissent_is_recorded(self):
        d = _Doc(["alto", "alto", "treble", None])
        d.infer()
        self.assertEqual(d.clef(3).value, "alto")
        self.assertEqual(d.clef(3).detail["tally"], {"alto": 2, "treble": 1})

    def test_it_is_preferred_over_the_convention_even_when_they_disagree(self):
        """⚠️ THE ORDER IS THE RULE. A Viola whose other systems all read
        TREBLE takes treble, not the alto its instrument would predict: tier
        (2) is a reading of real ink on this document and tier (3) is a claim
        about engraving practice, and a rule that let the weaker evidence win
        would be unable to follow a printed clef change."""
        d = _Doc(["treble", "treble", None], instrument="Viola")
        d.infer()
        self.assertEqual(instrument_named("Viola").default_clef, "alto")
        self.assertEqual(d.clef(2).value, "treble")
        self.assertEqual(d.clef(2).reason, "clef_from_other_systems")


class TestTierThreeTheInstrumentsConvention(unittest.TestCase):

    def test_no_other_system_decided_so_the_viola_takes_alto(self):
        d = _Doc([None], instrument="Viola")
        d.infer()
        v = d.clef(0)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, "alto")
        self.assertEqual(v.reason, "clef_from_instrument_convention")
        self.assertEqual(v.detail["convention"], "instrument_header_clef")

    def test_the_value_comes_from_the_instruments_table_not_from_the_rule(self):
        """⚠️ DERIVED, NEVER TYPED. If a rule held its own {Viola: alto} map
        it would drift from `instruments.py`, which is the one place the tree
        answers *what clef to expect*. Asserted over three families at once so
        an `alto` hardcoded into the rule fails here."""
        for name, want in (("Viola", "alto"), ("Cello", "bass"),
                           ("Flute", "treble")):
            with self.subTest(name):
                d = _Doc([None], instrument=name)
                d.infer()
                self.assertEqual(d.clef(0).value,
                                 instrument_named(name).default_clef)
                self.assertEqual(d.clef(0).value, want)

    def test_it_has_no_witnesses_and_says_so(self):
        """⚠️ Hazard (b). A convention is not a witness, and a rule that let
        one look like one would be counting its own assumption as evidence."""
        d = _Doc([None], instrument="Viola")
        d.infer()
        v = d.clef(0)
        self.assertEqual(v.used, ())
        self.assertEqual(v.detail["n_witnesses"], 0)
        self.assertEqual(v.detail["n_independent_witnesses"], 0)
        self.assertEqual(v.detail["n_systems_read"], 0)

    def test_a_name_the_table_does_not_hold_declines(self):
        d = _Doc([None], instrument="Ondes Martenot")
        d.infer()
        self.assertIs(d.clef(0).outcome, Outcome.ABSTAINED)
        self.assertEqual(d.census()[d.staves[0].to_key()].outcome,
                         "declined_no_instrument_name")


class TestWhatItDeclines(unittest.TestCase):

    def test_a_decided_clef_is_never_overruled(self):
        """⚠️ THE POSITIVE CONTROL OF THE WHOLE FILE, and it is the property
        rule 3 of the stage exists for: replacing a READING with a guess makes
        a cleanup count unable to tell a reading fault from an inference
        fault. The fixture is adversarial -- every other system says alto and
        this one READ treble."""
        d = _Doc(["alto", "alto", "alto", "treble"])
        before = d.clef(3)
        d.infer()
        after = d.clef(3)
        self.assertEqual(after.id, before.id)
        self.assertEqual(after.value, "treble")
        self.assertEqual(after.decider, "adjudicate_clef")
        self.assertFalse(infer.is_inferred(after))
        self.assertEqual(d.census()[d.staves[3].to_key()].outcome,
                         "declined_prior_is_decided")

    def test_a_narrowed_clef_is_the_clef_readers_problem_not_this_rules(self):
        """⚠️ `infer.INFERABLE` ADMITS A NARROWING AND THIS RULE STILL
        DECLINES IT. A narrowed clef means `adjudicate_clef` read the staff
        and could not separate two candidates under its own margin floor;
        Sean's rule is about a clef that could not be read AT ALL, and
        collapsing a contest from another system would be this rule quietly
        overruling a margin decision it has no evidence about."""
        d = _Doc(["alto", "alto", ("narrowed", "alto", "tenor")])
        d.infer()
        self.assertIs(d.clef(2).outcome, Outcome.NARROWED)
        self.assertEqual(d.census()[d.staves[2].to_key()].outcome,
                         "declined_prior_is_narrowed")

    def test_an_undecided_part_declines(self):
        d = _Doc(["alto", "alto", None], slot_outcome=Outcome.NARROWED)
        d.infer()
        self.assertIs(d.clef(2).outcome, Outcome.ABSTAINED)
        self.assertEqual(d.census()[d.staves[2].to_key()].outcome,
                         "declined_part_not_decided")

    def test_a_staff_is_never_its_own_witness(self):
        """One system, clef abstained, no other staff on the slot: tier (2)
        has nothing and the rule falls through to (3) rather than reading its
        own abstention as a read."""
        d = _Doc([None], instrument="Viola")
        d.infer()
        self.assertEqual(d.clef(0).reason, "clef_from_instrument_convention")

    def test_another_part_on_another_slot_is_not_a_witness(self):
        log = Log()
        viola, cello = _staff(0, 0, 3), _staff(0, 1, 4)
        _verdict(log, viola, Q.SLOT_INDEX, 9, detail={"instrument": "Viola"})
        _verdict(log, viola, Q.CLEF, None, outcome=Outcome.ABSTAINED,
                 decider="adjudicate_clef", reason="no_candidates")
        _verdict(log, cello, Q.SLOT_INDEX, 10, detail={"instrument": "Cello"})
        _verdict(log, cello, Q.CLEF, "bass", decider="adjudicate_clef",
                 reason="scored")
        log.freeze()
        infer.run(log, evaluate.Report([], [], []))
        v = log.verdict(Q.CLEF, viola)
        self.assertEqual(v.value, "alto")       # the CONVENTION, not the bass
        self.assertEqual(v.reason, "clef_from_instrument_convention")


class TestItRunsAfterTheSlotRule(unittest.TestCase):

    def test_registration_order_puts_the_slot_rule_first(self):
        """⚠️ NOT COSMETIC. `infer.run` walks `RULES` in REGISTRATION order,
        and on the Litolff record all 9 staves this rule repairs have their
        `Q.SLOT_INDEX` DECIDED by `collapse_slot_index_to_family_block` --
        itself an inference. Registered first, this rule would find no decided
        slot, propose nothing, and report a clean, FALSE zero."""
        names = [r.inference.value for r in _rules()]
        self.assertLess(names.index("collapse_slot_index_to_family_block"),
                        names.index("fill_clef_gap"))

    def test_a_part_placed_by_an_inference_is_used_and_labelled_as_such(self):
        log = Log()
        a, b = _staff(0, 0, 3), _staff(0, 1, 3)
        _verdict(log, a, Q.SLOT_INDEX, 9, detail={"instrument": "Viola"})
        _verdict(log, a, Q.CLEF, "alto", decider="adjudicate_clef",
                 reason="scored")
        _verdict(log, b, Q.SLOT_INDEX, 9, decider="infer:whatever",
                 reason="the_short_block_is_condensed_at_its_foot",
                 detail={"instrument": "Viola", "inferred": True})
        _verdict(log, b, Q.CLEF, None, outcome=Outcome.ABSTAINED,
                 decider="adjudicate_clef", reason="no_candidates")
        log.freeze()
        infer.run(log, evaluate.Report([], [], []))
        v = log.verdict(Q.CLEF, b)
        self.assertEqual(v.value, "alto")
        self.assertTrue(v.detail["part_from_an_inference"])


class TestTheSecondEvaluatePassReachesThePitches(unittest.TestCase):
    """⚠️⚠️ THE ORDERING PROBLEM, ASSERTED. INFER runs AFTER EVALUATE and a
    notehead's PITCH is an EVALUATE consequence of the clef, so an inferred
    clef that nothing re-evaluates repairs NOTHING -- the staff keeps its
    heads and keeps its `no_pitch` refusals, and the rule is inert in exactly
    the way that reads as a clean zero."""

    def _doc(self):
        # one head at position 4 (the middle line): B4 in treble, C4 in alto.
        return _Doc(["alto", "alto", None],
                    positions=[(0, 0, 0, 4), (2, 0, 0, 4)])

    def test_without_the_second_pass_the_inferred_staff_has_no_pitch(self):
        """⚠️ RUN THE CONTROL IN THE STATE WHERE IT FAILS (rule 7). If this
        passed as well after `run_over`, the test below would be measuring
        nothing."""
        d = self._doc()
        evaluate.run(d.log)
        d.infer()
        self.assertIsNone(d.log.verdict(Q.PITCH, _glyph(0, 2, 3, 0, 0)))

    def test_the_bounded_pass_gives_it_a_pitch_from_the_inferred_clef(self):
        d = self._doc()
        evaluate.run(d.log)
        d.infer()
        rep = evaluate.run_over(d.log, infer.inferred_verdicts(d.log))
        p = d.log.verdict(Q.PITCH, _glyph(0, 2, 3, 0, 0))
        self.assertIsNotNone(p)
        self.assertEqual(p.value, "C4")         # alto, middle line
        self.assertIn(("restate_pitch", d.staves[2].to_key(), Q.PITCH),
                      rep.fired)

    def test_the_derived_pitch_carries_the_label_through_its_basis(self):
        """The label PROPAGATES rather than being re-stamped: the pitch names
        the clef in its `basis`, and `infer.inferred_in_basis` answers *was a
        guess in this chain* from the record alone."""
        d = self._doc()
        evaluate.run(d.log)
        d.infer()
        evaluate.run_over(d.log, infer.inferred_verdicts(d.log))
        p = d.log.verdict(Q.PITCH, _glyph(0, 2, 3, 0, 0))
        self.assertIn(d.clef(2).id, p.basis)
        self.assertEqual(infer.inferred_in_basis(d.log, p), (d.clef(2).id,))

    def test_a_pitch_from_a_READ_clef_carries_no_such_label(self):
        """⚠️ THE POSITIVE CONTROL FOR THE LABEL. A query that returned
        something for every pitch would answer nothing."""
        d = self._doc()
        evaluate.run(d.log)
        d.infer()
        evaluate.run_over(d.log, infer.inferred_verdicts(d.log))
        p = d.log.verdict(Q.PITCH, _glyph(0, 0, 3, 0, 0))
        self.assertEqual(p.value, "C4")
        self.assertEqual(infer.inferred_in_basis(d.log, p), ())

    def test_the_second_pass_restates_nothing_the_first_pass_settled(self):
        """⚠️⚠️ THE BOUND, AND THE REASON `run_over` IS NOT A SECOND `run`. A
        full re-run appends a second copy of every consequence in the
        document. Here the READ staves must come out with exactly the pitch
        rows they already had."""
        d = self._doc()
        evaluate.run(d.log)
        read_before = [v.id for v in d.log.verdicts(
            Q.PITCH, _glyph(0, 0, 3, 0, 0))]
        d.infer()
        evaluate.run_over(d.log, infer.inferred_verdicts(d.log))
        read_after = [v.id for v in d.log.verdicts(
            Q.PITCH, _glyph(0, 0, 3, 0, 0))]
        self.assertEqual(read_before, read_after)

    def test_with_no_inference_the_bounded_pass_fires_nothing(self):
        """⚠️ Reach before accuracy. An empty cause set must produce an empty
        pass and SAY so, not silently skip the loop."""
        d = _Doc(["alto", "alto", "alto"], positions=[(0, 0, 0, 4)])
        evaluate.run(d.log)
        rep = evaluate.run_over(d.log, [])
        self.assertEqual(rep.fired, [])
        self.assertIn("not_downstream_of_an_inference",
                      {s[2] for s in rep.skipped})

    def test_the_rule_order_is_preserved_in_the_second_pass(self):
        """`move_glyph` runs after `respell_accidental` (CLAUDE.md §4c), and
        one loop body serves both passes so the two orders cannot diverge."""
        order = [r.consequence.value for r in sorted(
            evaluate.RULES, key=lambda r: evaluate.DOWNHILL.index(r.cause))]
        self.assertLess(order.index("respell_accidental"),
                        order.index("move_glyph"))


class TestMoveGlyphSeesTheInferredClefToo(unittest.TestCase):
    """⚠️ `move_glyph`'s CAUSE is the ownership and its clef comes from the
    WINNING staff, so a pass keyed on the cause alone would silently skip a
    glyph whose winner's clef was just inferred -- a half-repair that reads as
    a whole one. `consequences._move_glyph_also_reads` declares it."""

    def test_it_is_declared(self):
        evaluate._ensure_rules()
        r = next(r for r in evaluate.RULES
                 if r.consequence.value == "move_glyph")
        self.assertIsNotNone(r.reads_beyond_cause)

    def test_a_glyph_won_by_the_repaired_staff_gets_a_pitch(self):
        log = Log()
        viola, other = _staff(0, 0, 3), _staff(0, 0, 4)
        _verdict(log, viola, Q.SLOT_INDEX, 9, detail={"instrument": "Viola"})
        _verdict(log, viola, Q.CLEF, None, outcome=Outcome.ABSTAINED,
                 decider="adjudicate_clef", reason="no_candidates")
        _verdict(log, other, Q.SLOT_INDEX, 10, detail={"instrument": "Cello"})
        _verdict(log, other, Q.CLEF, "bass", decider="adjudicate_clef",
                 reason="scored")
        g = _glyph(0, 0, 4, 0, 0)          # cut on the CELLO, won by the VIOLA
        log.observe(g, Q.GLYPH_BAND_DISTANCE, 1.0, reader="cv_lines",
                    frame="cell:0", candidate=viola.to_key(),
                    position_in_candidate=4.0)
        _verdict(log, g, Q.GLYPH_OWNER, viola.to_key(), decider="test",
                 reason="ladder")
        log.freeze()

        evaluate.run(log)
        # RED CONTROL: no clef on the winner, so no pitch -- and that is the
        # state the repair has to change.
        self.assertIsNone(log.verdict(Q.PITCH, g))

        infer.run(log, evaluate.Report([], [], []))
        evaluate.run_over(log, infer.inferred_verdicts(log))
        p = log.verdict(Q.PITCH, g)
        self.assertIsNotNone(p)
        self.assertEqual(p.value, "C4")     # alto, middle line
        self.assertEqual(infer.inferred_in_basis(log, p),
                         (log.verdict(Q.CLEF, viola).id,))


class TestTheHarnessAdmitsAnAbstainedPrior(unittest.TestCase):
    """⚠️ A NEW SHAPE FOR THIS STAGE. Every rule before 2.10 spoke into a
    NARROWING, where rule 4 bounds the value to the reader's own candidates.
    `adjudicate_clef` abstaining `no_candidates` kept NO candidates, so on
    this path rule 4 has nothing to bound with -- which makes it worth
    asserting that the harness admits the abstention AND still refuses a
    decision."""

    def test_abstained_is_inferable(self):
        self.assertIn(Outcome.ABSTAINED, infer.INFERABLE)
        self.assertNotIn(Outcome.DECIDED, infer.INFERABLE)

    def test_the_inferred_verdict_is_labelled_by_the_harness(self):
        d = _Doc(["alto", "alto", None])
        d.infer()
        v = d.clef(2)
        self.assertTrue(infer.is_inferred(v))
        self.assertEqual(v.decider, "infer:fill_clef_gap")
        self.assertTrue(v.detail["inferred"])
        self.assertTrue(v.detail["sideways"])
        self.assertEqual(v.detail["prior_outcome"], "abstained")

    def test_every_new_verdict_the_stage_wrote_is_labelled(self):
        d = _Doc(["alto", "alto", None, None])
        before = {v.id for v in d.log.all_verdicts()}
        d.infer()
        new = [v for v in d.log.all_verdicts() if v.id not in before]
        self.assertTrue(new)
        self.assertTrue(all(infer.is_inferred(v) for v in new))



class TestRestatePitchDoesNotOverturnAMovedGlyph(unittest.TestCase):
    """⚠️ FOUND BY THE ARM, NOT BY A HUNCH. The Litolff whole-movement replay
    died on `glyph/2/1/9/6/2` with `AlreadyAdjudicated`: a glyph cut in the
    abstained-clef Viola's cells but awarded to a NEIGHBOUR, which
    `move_glyph` had already re-pitched on the WINNER's clef in the first
    pass. `restate_pitch` walks the staff's position rows, and a contest
    DROPS the loser rather than removing its row, so the second pass offered
    it again — on the clef of the staff it had left.
    """

    def _log(self):
        log = Log()
        viola, other = _staff(0, 0, 3), _staff(0, 0, 4)
        _verdict(log, viola, Q.SLOT_INDEX, 9, detail={"instrument": "Viola"})
        _verdict(log, viola, Q.CLEF, None, outcome=Outcome.ABSTAINED,
                 decider="adjudicate_clef", reason="no_candidates")
        _verdict(log, other, Q.SLOT_INDEX, 10, detail={"instrument": "Cello"})
        _verdict(log, other, Q.CLEF, "bass", decider="adjudicate_clef",
                 reason="scored")
        # cut in the VIOLA's cell, won by the CELLO
        g = _glyph(0, 0, 3, 0, 0)
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, 4.0, reader="cv_lines",
                    frame="cell:0")
        log.observe(g, Q.GLYPH_BAND_DISTANCE, 1.0, reader="cv_lines",
                    frame="cell:0", candidate=other.to_key(),
                    position_in_candidate=4.0)
        _verdict(log, g, Q.GLYPH_OWNER, other.to_key(), decider="test",
                 reason="ladder")
        log.freeze()
        return log, g, viola

    def test_the_second_pass_does_not_raise(self):
        log, g, _viola = self._log()
        evaluate.run(log)
        infer.run(log, evaluate.Report([], [], []))
        evaluate.run_over(log, infer.inferred_verdicts(log))   # used to raise

    def test_the_glyph_keeps_the_pitch_the_winner_gave_it(self):
        log, g, viola = self._log()
        evaluate.run(log)
        moved = log.verdict(Q.PITCH, g)
        self.assertEqual(moved.decider, "move_glyph")
        infer.run(log, evaluate.Report([], [], []))
        evaluate.run_over(log, infer.inferred_verdicts(log))
        after = log.verdict(Q.PITCH, g)
        self.assertEqual(after.id, moved.id)
        self.assertEqual(after.value, moved.value)
        # ⚠️ and it is the WINNER's reading, not what this staff's new clef
        # would have given the same position.
        self.assertNotEqual(after.value, "C4")       # alto, middle line

    def test_the_guard_is_a_no_op_on_the_first_pass(self):
        """⚠️ THE CONTROL THAT KEEPS THE GUARD HONEST. It must not suppress a
        pitch the first pass would have written — `restate_pitch` is the first
        writer of `Q.PITCH` in DOWNHILL order, so nothing stands when it runs
        and every position row still gets its pitch."""
        d = _Doc(["alto"], positions=[(0, 0, 0, 4), (0, 0, 1, 2)])
        rep = evaluate.run(d.log)
        self.assertEqual(d.log.verdict(Q.PITCH, _glyph(0, 0, 3, 0, 0)).value,
                         "C4")
        self.assertIsNotNone(d.log.verdict(Q.PITCH, _glyph(0, 0, 3, 0, 1)))
        self.assertEqual(
            sum(1 for f in rep.fired if f[0] == "restate_pitch"), 2)


if __name__ == "__main__":
    unittest.main()
