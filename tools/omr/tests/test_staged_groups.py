"""Coherence tests for redundant groups.

⚠️ NOT ACCURACY TESTS. Nothing here asserts that any reading is RIGHT. They
assert the properties the group abstraction exists for, and each of the four
load-bearing ones was run RED before it was believed:

  1. a disagreement implicates EVERY member, never the cheapest;
  2. witnesses that are one signal are one witness, so correlated unanimity
     reports SINGLE and never UNANIMOUS;
  3. NONE / SINGLE / UNANIMOUS / MAJORITY / SPLIT are five distinguishable
     answers, not two;
  4. a declared redundancy that finds nothing is REPORTED by name.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate, groups
from tools.omr.staged import record as R
from tools.omr.staged.groups import (Agreement, Group, Redundancy, Source,
                                     Witness)
from tools.omr.staged.record import (ABSTAIN, Kind, Log, Observation, Outcome,
                                     Q, READERS, Subject, Verdict)

FRAME = "header_window"


def meter_row(log: Log, staff: Subject, raw: str, *,
              reader: str = READERS.TEMPLATE, frame: str = FRAME,
              derived_from=()):
    """One staff's template meter reading."""
    num, den = (int(x) for x in raw.split("/")) if "/" in raw else (4, 4)
    return log.observe(staff, Q.METER_TEMPLATE, (num, den), reader=reader,
                       frame=frame, score=0.7, raw=raw,
                       derived_from=derived_from)


def a_system_of(log: Log, n: int, meters, page=0, system=0):
    """`meters` is one raw string per staff, or None for a silent staff."""
    for i, raw in enumerate(meters):
        st = R.staff(page, system, i)
        if raw is None:
            log.abstain(st, Q.METER_TEMPLATE, reader=READERS.TEMPLATE,
                        frame=FRAME, reason=ABSTAIN.BELOW_THRESHOLD)
            continue
        meter_row(log, st, raw)


def only(red_name: str):
    """Assess exactly one declared redundancy."""
    groups._ensure_declarations()
    for r in groups.REDUNDANCIES:
        if r.name == red_name:
            return r
    raise AssertionError(f"no redundancy named {red_name!r}")


class TestTheFiveAnswers(unittest.TestCase):
    """⚠️ NONE and SINGLE are not agreement, and SPLIT is not MAJORITY.

    A naive `len(set(values)) == 1` collapses four of these five into "agree",
    and the two it hides are the ones that carry no information.
    """

    def _assess(self, meters):
        log = Log()
        a_system_of(log, len(meters), meters)
        log.freeze()
        found = groups.assess(log, only("meter_across_staves"))
        real = [g for g in found if g.fact != "<unplaced>"]
        self.assertEqual(len(real), 1, [g.fact for g in found])
        return real[0]

    def test_no_witness_at_all_is_NONE(self):
        g = self._assess([None, None, None])
        self.assertIs(g.agreement, Agreement.NONE)
        self.assertEqual(g.witnesses, ())

    def test_one_witness_is_SINGLE_and_not_agreement(self):
        g = self._assess(["2/4", None, None])
        self.assertIs(g.agreement, Agreement.SINGLE)
        self.assertTrue(g.uninformative)

    def test_all_agreeing_is_UNANIMOUS(self):
        g = self._assess(["2/4"] * 4)
        self.assertIs(g.agreement, Agreement.UNANIMOUS)
        self.assertFalse(g.uninformative)
        self.assertEqual(g.dissenting, ())

    def test_a_strict_plurality_is_MAJORITY(self):
        g = self._assess(["2/4", "2/4", "2/4", "4/4"])
        self.assertIs(g.agreement, Agreement.MAJORITY)
        self.assertEqual(len(g.dissenting), 1)

    def test_an_even_division_is_SPLIT_and_names_NO_dissenter(self):
        """⚠️ With the group evenly divided nobody is the odd one out.
        Naming a side would be the convict-the-cheapest move this refuses."""
        g = self._assess(["2/4", "2/4", "4/4", "4/4"])
        self.assertIs(g.agreement, Agreement.SPLIT)
        self.assertEqual(g.dissenting, ())
        self.assertEqual(len(g.suspects), 4)

    def test_a_silent_staff_is_recorded_not_counted_as_agreeing(self):
        g = self._assess(["2/4", "2/4", None])
        self.assertEqual(len(g.witnesses), 2)
        self.assertEqual([s for s, _why in g.silent],
                         ["staff/0/0/2"])
        self.assertEqual([why for _s, why in g.silent], ["declined"])


class TestAFailedCheckImplicatesTheGroup(unittest.TestCase):
    """⚠️⚠️ THE MOST IMPORTANT PROPERTY IN THIS MODULE.

    Nine eighths in a 4/4 bar proves an error and does not say which symbol.
    Get this wrong and a failed check confidently rewrites whatever is
    cheapest to alter.
    """

    def setUp(self):
        log = Log()
        a_system_of(log, 4, ["2/4", "2/4", "2/4", "4/4"])
        log.freeze()
        self.group = [g for g in groups.assess(log, only("meter_across_staves"))
                      if g.fact != "<unplaced>"][0]

    def test_the_majority_is_a_suspect_TOO(self):
        """The dissenter is not convicted. Every witness is implicated,
        including the three that agree with each other."""
        self.assertEqual(len(self.group.suspects), 4)
        for w in self.group.witnesses:
            self.assertIn(w.row_id, self.group.suspects)

    def test_dissenters_are_a_SUBSET_of_suspects_never_the_whole_of_them(self):
        self.assertTrue(set(self.group.dissenting) < set(self.group.suspects))

    def test_the_group_names_the_QUANTITIES_it_implicates_including_its_own(self):
        self.assertIn(Q.METER, self.group.implicates)
        self.assertIn(Q.METER_TEMPLATE, self.group.implicates)

    def test_there_is_no_field_naming_a_culprit(self):
        """⚠️ Asserted structurally, because prose in a docstring does not
        stop the next hand adding `culprit`. A field named for the guilty
        member would make the wrong reading the easy one."""
        banned = {"culprit", "correct_value", "winner", "wrong", "repair",
                  "fix", "offender", "blame"}
        fields = set(Group.__dataclass_fields__)
        self.assertEqual(fields & banned, set())

    def test_every_declared_redundancy_implicates_ITSELF(self):
        """A check that implicates only OTHER facts has quietly decided the
        fact under test is innocent. Mirrors the same assertion on decisions."""
        groups._ensure_declarations()
        for red in groups.REDUNDANCIES:
            with self.subTest(red=red.name):
                self.assertIn(red.quantity, red.implicates)


class TestIndependence(unittest.TestCase):
    """⚠️ Two signals sharing an ancestor are ONE signal, not corroboration.

    The measured case this guards: the header clef pre-pass and the
    measure-pass argmax are the same call on the same list object — divergent
    on 0 of 396 staves — and counting them as agreement would have produced a
    77% agreement rate carrying no information.
    """

    def test_one_reading_recorded_twice_is_one_witness(self):
        log = Log()
        st = R.staff(0, 0, 0)
        meter_row(log, st, "2/4")
        meter_row(log, st, "2/4")          # the same reader, subject and frame
        log.freeze()
        g = [x for x in groups.assess(log, only("meter_across_staves"))
             if x.fact != "<unplaced>"][0]
        self.assertEqual(len(g.witnesses), 2)
        self.assertEqual(g.n_signals, 1)
        self.assertIs(g.agreement, Agreement.SINGLE)
        self.assertTrue(g.uninformative)

    def test_correlated_UNANIMITY_never_reports_unanimous(self):
        """The exact failure shape: four rows, one signal, all agreeing."""
        log = Log()
        st = R.staff(0, 0, 0)
        for _ in range(4):
            meter_row(log, st, "2/4")
        log.freeze()
        g = [x for x in groups.assess(log, only("meter_across_staves"))
             if x.fact != "<unplaced>"][0]
        self.assertIsNot(g.agreement, Agreement.UNANIMOUS)
        self.assertIs(g.agreement, Agreement.SINGLE)

    def test_two_descendants_of_ONE_EXTERNAL_DOCUMENT_are_one_witness(self):
        """⚠️ The dossier double-count, in a group. Two staves' readings that
        both descend from one external row are not two witnesses — and with an
        empty basis they would look exactly like two."""
        log = Log()
        seed = log.observe(R.DOCUMENT, Q.DOSSIER_FACT, {"meter": "2/4"},
                           reader=READERS.DOSSIER, frame="dossier")
        meter_row(log, R.staff(0, 0, 0), "2/4", derived_from=(seed.id,))
        meter_row(log, R.staff(0, 0, 1), "2/4", derived_from=(seed.id,))
        log.freeze()
        g = [x for x in groups.assess(log, only("meter_across_staves"))
             if x.fact != "<unplaced>"][0]
        self.assertEqual(len(g.witnesses), 2)
        self.assertEqual(g.n_signals, 1, "two descendants of one document")
        self.assertIs(g.agreement, Agreement.SINGLE)

    def test_CONTROL_two_staves_read_off_the_page_are_two_witnesses(self):
        """⚠️ The control that makes the test above mean something. The rule
        must collapse a SHARED ANCESTOR, not everything that agrees."""
        log = Log()
        meter_row(log, R.staff(0, 0, 0), "2/4")
        meter_row(log, R.staff(0, 0, 1), "2/4")
        log.freeze()
        g = [x for x in groups.assess(log, only("meter_across_staves"))
             if x.fact != "<unplaced>"][0]
        self.assertEqual(g.n_signals, 2)
        self.assertIs(g.agreement, Agreement.UNANIMOUS)

    def test_a_signal_that_contradicts_ITSELF_votes_for_nothing(self):
        """One reader, one crop, two answers. That is evidence of
        disagreement and evidence for neither value."""
        log = Log()
        st = R.staff(0, 0, 0)
        meter_row(log, st, "2/4")
        meter_row(log, st, "4/4")
        log.freeze()
        g = [x for x in groups.assess(log, only("meter_across_staves"))
             if x.fact != "<unplaced>"][0]
        self.assertIs(g.agreement, Agreement.SPLIT)
        self.assertEqual(len(g.internally_split), 1)
        self.assertEqual(g.readings, ())


class TestTheGroupRuleIsSubjectAware(unittest.TestCase):
    """⚠️ AND `adjudicate._one_signal` IS NOT — deliberately, and the
    divergence is pinned so that unifying them is a decision, not an accident.

    A decision's evidence is almost always about ONE subject, so matching on
    `(reader, frame, quantity)` reads there as "the same reader on the same
    crop". A redundant group is the opposite case by construction: twelve
    staves, one reader, one kind of crop — and the adjudicate rule would
    collapse a whole system's meter vote into one witness.
    """

    def test_adjudicate_would_collapse_two_staves_and_groups_does_not(self):
        log = Log()
        a = meter_row(log, R.staff(0, 0, 0), "2/4")
        b = meter_row(log, R.staff(0, 0, 1), "2/4")
        self.assertTrue(adjudicate._one_signal(log, a, b),
                        "the adjudicate rule is subject-blind")
        self.assertFalse(groups.one_signal(log, a, b),
                         "the group rule must not be")

    def test_both_rules_agree_where_the_subject_is_the_same(self):
        log = Log()
        st = R.staff(0, 0, 0)
        a = meter_row(log, st, "2/4")
        b = meter_row(log, st, "2/4")
        self.assertTrue(adjudicate._one_signal(log, a, b))
        self.assertTrue(groups.one_signal(log, a, b))


class TestVerdictWitnesses(unittest.TestCase):
    """Groups over adjudicated facts, not only over readers."""

    def _log_with_counts(self, counts):
        log = Log()
        for i, n in enumerate(counts):
            st = R.staff(0, 0, i)
            log.observe(st, Q.BARLINE_COLUMN, n, reader=READERS.GEOMETRY,
                        frame="page")
        log.freeze()
        for i, n in enumerate(counts):
            st = R.staff(0, 0, i)
            rows = log.rows(Q.BARLINE_COLUMN, st)
            log.record(Verdict(
                id=log._next_id("vrd"), subject=st,
                quantity=Q.MEASURE_PARTITION, outcome=Outcome.DECIDED,
                value=n, decider="test", reason="counted",
                considered=(rows[0].id,), basis=(rows[0].id,)))
        return log

    def test_staves_agreeing_on_a_bar_count_are_unanimous(self):
        log = self._log_with_counts([6, 6, 6])
        g = [x for x in groups.assess(log, only("measure_count_across_staves"))
             if x.fact != "<unplaced>"][0]
        self.assertIs(g.agreement, Agreement.UNANIMOUS)
        self.assertEqual(g.n_signals, 3)

    def test_one_staff_reading_a_different_count_is_a_MAJORITY_disagreement(self):
        log = self._log_with_counts([6, 6, 6, 4])
        g = [x for x in groups.assess(log, only("measure_count_across_staves"))
             if x.fact != "<unplaced>"][0]
        self.assertIs(g.agreement, Agreement.MAJORITY)
        self.assertEqual(len(g.suspects), 4, "all four staves are implicated")

    def test_an_ABSTAINED_verdict_is_silent_and_not_a_witness(self):
        log = self._log_with_counts([6, 6])
        st = R.staff(0, 0, 2)
        log.observe  # noqa: B018  -- the log is frozen; subject comes from below
        log.record(Verdict(
            id=log._next_id("vrd"), subject=st, quantity=Q.MEASURE_PARTITION,
            outcome=Outcome.ABSTAINED, value=None, decider="test",
            reason="no_barline"))
        g = [x for x in groups.assess(log, only("measure_count_across_staves"))
             if x.fact != "<unplaced>"][0]
        self.assertEqual(len(g.witnesses), 2)
        self.assertIn(("staff/0/0/2", "abstained:no_barline"), g.silent)


class TestTheSlotJoinRefusesAcrossLINEUPS(unittest.TestCase):
    """⚠️ Two systems witness one part only when they print the same number of
    staves.

    `slot_index` is today the staff's ORDINAL within its own system, and a
    printed score suppresses tacet staves — so joining slot 4 of an 11-staff
    system to slot 4 of an 8-staff system grafts a horn's continuation onto a
    trumpet's part. That is exactly the population `export._stitch_slots`
    refuses, and where the partition gate measured 3 of 27 staves misgrouped.
    """

    def _log(self, systems):
        """`systems` maps system index -> list of clef names, one per staff."""
        log = Log()
        for sys_idx, clefs in systems.items():
            for st_idx, _c in enumerate(clefs):
                log.observe(R.staff(0, sys_idx, st_idx), Q.STAFF_LINES,
                            [1, 2, 3, 4, 5], reader=READERS.GEOMETRY,
                            frame="page")
        log.freeze()
        for sys_idx, clefs in systems.items():
            sysub = R.system(0, sys_idx)
            log.record(Verdict(id=log._next_id("vrd"), subject=sysub,
                               quantity=Q.SYSTEM_STAFF_COUNT,
                               outcome=Outcome.DECIDED, value=len(clefs),
                               decider="test", reason="counted"))
            for st_idx, clef in enumerate(clefs):
                st = R.staff(0, sys_idx, st_idx)
                log.record(Verdict(id=log._next_id("vrd"), subject=st,
                                   quantity=Q.SLOT_INDEX,
                                   outcome=Outcome.DECIDED, value=st_idx,
                                   decider="test", reason="full_lineup"))
                log.record(Verdict(id=log._next_id("vrd"), subject=st,
                                   quantity=Q.CLEF, outcome=Outcome.DECIDED,
                                   value=clef, decider="test", reason="scored"))
        return log

    def test_two_full_systems_of_one_part_are_two_witnesses(self):
        log = self._log({0: ["treble", "bass"], 1: ["treble", "bass"]})
        found = [g for g in groups.assess(log, only("clef_across_systems"))
                 if g.fact != "<unplaced>"]
        self.assertEqual(len(found), 2, "one group per part")
        for g in found:
            self.assertIs(g.agreement, Agreement.UNANIMOUS)
            self.assertEqual(g.n_signals, 2)

    def test_systems_of_DIFFERENT_staff_counts_never_witness_each_other(self):
        log = self._log({0: ["treble", "alto", "bass"], 1: ["treble", "bass"]})
        found = [g for g in groups.assess(log, only("clef_across_systems"))
                 if g.fact != "<unplaced>"]
        # 3 parts in the full lineup + 2 in the reduced one = 5 separate facts,
        # every one of them SINGLE. None of the reduced system's staves is
        # allowed to corroborate a full system's part.
        self.assertEqual(len(found), 5)
        for g in found:
            self.assertIs(g.agreement, Agreement.SINGLE)
            self.assertEqual(len(g.witnesses), 1)

    def test_a_staff_with_no_slot_verdict_is_UNPLACED_not_guessed(self):
        log = self._log({0: ["treble", "bass"]})
        st = R.staff(0, 0, 2)
        log.record(Verdict(id=log._next_id("vrd"), subject=st,
                           quantity=Q.CLEF, outcome=Outcome.DECIDED,
                           value="tenor", decider="test", reason="scored"))
        unplaced = [g for g in groups.assess(log, only("clef_across_systems"))
                    if g.fact == "<unplaced>"]
        self.assertEqual(len(unplaced), 1)
        self.assertEqual(len(unplaced[0].witnesses), 1)


class TestALegitimateDifferenceIsDeclared(unittest.TestCase):
    """⚠️ A clef change is real music. Without this field a cello moving from
    bass to tenor reads as an error, and the report would be training a reader
    to distrust correct engraving."""

    def test_the_clef_group_declares_one_and_the_meter_group_does_not(self):
        self.assertIsNotNone(only("clef_across_systems").legitimate_difference)
        self.assertIsNotNone(
            only("key_signature_across_systems").legitimate_difference)
        self.assertIsNone(only("meter_across_staves").legitimate_difference)

    def test_it_reaches_the_group_and_its_json(self):
        log = Log()
        log.freeze()
        red = only("clef_across_systems")
        g = groups._one_group(log, red, "slot|0|of|2", [], ())
        self.assertIsNotNone(g.legitimate_difference)
        self.assertIsNotNone(g.to_json()["legitimate_difference"])


class TestDeclarationDiscipline(unittest.TestCase):
    """The declaration must say why and about what, on the model of
    `evaluate.rule`'s required `bound`."""

    def _kwargs(self, **over):
        base = dict(name="probe", quantity=Q.METER_TEMPLATE,
                    source=Source.OBSERVATION, witness_scope=Kind.STAFF,
                    fact_key=lambda log, r: r.subject.at(Kind.SYSTEM),
                    reading=lambda log, r: r.value,
                    why="x" * 50, aspect="y" * 50,
                    implicates=(Q.METER_TEMPLATE,))
        base.update(over)
        return base

    def tearDown(self):
        groups.REDUNDANCIES[:] = [r for r in groups.REDUNDANCIES
                                  if r.name != "probe"]

    def test_a_redundancy_with_no_stated_reason_is_refused(self):
        with self.assertRaises(ValueError):
            groups.redundancy(**self._kwargs(why="because"))

    def test_a_redundancy_with_no_stated_ASPECT_is_refused(self):
        """The key-signature trap: printed on every staff, redundant across
        none of them."""
        with self.assertRaises(ValueError):
            groups.redundancy(**self._kwargs(aspect="the value"))

    def test_a_redundancy_that_does_not_implicate_itself_is_refused(self):
        with self.assertRaises(ValueError):
            groups.redundancy(**self._kwargs(implicates=(Q.METER,)))

    def test_a_redundancy_naming_an_unknown_quantity_is_refused(self):
        with self.assertRaises(ValueError):
            groups.redundancy(**self._kwargs(implicates=(Q.METER_TEMPLATE,
                                                         "not_a_quantity")))

    def test_every_declared_redundancy_names_prior_art_or_a_reason(self):
        groups._ensure_declarations()
        self.assertGreaterEqual(len(groups.REDUNDANCIES), 5)
        for red in groups.REDUNDANCIES:
            with self.subTest(red=red.name):
                self.assertGreater(len(red.why), 40)
                self.assertGreater(len(red.aspect), 40)


class TestTheReport(unittest.TestCase):
    def test_an_empty_registry_is_an_ERROR_not_an_empty_report(self):
        """⚠️ A-BUILD-5, third instance. A stage that found nothing because
        nothing was loaded is indistinguishable from one with nothing to
        find."""
        saved = list(groups.REDUNDANCIES)
        groups.REDUNDANCIES.clear()
        try:
            original = groups._declare
            groups._declare = lambda: None
            try:
                with self.assertRaises(groups.NoRedundanciesDeclared):
                    groups.run(Log())
            finally:
                groups._declare = original
        finally:
            groups.REDUNDANCIES[:] = saved

    def test_a_declared_redundancy_that_found_NOTHING_is_named(self):
        """⚠️ A ZERO IS A SUSPECT. Seven-plus probes in this project have
        printed clean tables of zeros at exit 0."""
        log = Log()
        log.freeze()
        report = groups.run(log)
        named = report.to_json()["declared_but_empty"]
        self.assertIn("meter_across_staves", named)
        self.assertIn("clef_across_systems", named)

    def test_the_three_kinds_of_zero_are_reported_APART(self):
        """⚠️ They have different causes and different fixes: a declaration
        that placed no fact is a bug in the declaration; a fact nobody
        witnessed is silent readers; and a redundancy that never got two
        independent signals corroborated NOTHING however busy it looks."""
        log = Log()
        # one system, one staff, one reading -> a fact, a witness, and no
        # corroboration anywhere.
        a_system_of(log, 1, ["2/4"])
        log.freeze()
        js = groups.run(log).to_json()
        self.assertNotIn("meter_across_staves", js["declared_but_empty"])
        self.assertNotIn("meter_across_staves", js["witnessed_by_nobody"])
        self.assertIn("meter_across_staves", js["checked_nothing"])

    def test_a_fact_nobody_witnessed_is_named_apart_from_an_empty_one(self):
        log = Log()
        a_system_of(log, 2, [None, None])
        log.freeze()
        js = groups.run(log).to_json()
        self.assertNotIn("meter_across_staves", js["declared_but_empty"],
                         "the fact exists; its staves declined")
        self.assertIn("meter_across_staves", js["witnessed_by_nobody"])

    def test_a_corroborated_redundancy_is_in_NONE_of_the_three(self):
        """The control. All three lists must be able to be empty, or they are
        constants dressed as checks."""
        log = Log()
        a_system_of(log, 3, ["2/4", "2/4", "2/4"])
        log.freeze()
        js = groups.run(log).to_json()
        for key in ("declared_but_empty", "witnessed_by_nobody",
                    "checked_nothing"):
            self.assertNotIn("meter_across_staves", js[key], key)

    def test_a_redundancy_that_found_something_is_NOT_named_as_empty(self):
        """The control: `declared_but_empty` must be able to be non-trivial in
        both directions, or it is a constant."""
        log = Log()
        a_system_of(log, 3, ["2/4", "2/4", "2/4"])
        log.freeze()
        report = groups.run(log)
        self.assertNotIn("meter_across_staves",
                         report.to_json()["declared_but_empty"])

    def test_disagreements_are_reported_apart_from_the_rest(self):
        log = Log()
        a_system_of(log, 4, ["2/4", "2/4", "2/4", "4/4"])
        log.freeze()
        report = groups.run(log)
        js = report.to_json()
        self.assertEqual(js["n_disagreements"], 1)
        self.assertEqual(js["disagreements"][0]["agreement"], "majority")

    def test_uninformative_groups_are_counted_beside_the_agreement_tally(self):
        """A wall of UNANIMOUS that is entirely uninformative checked
        nothing, and a single number would hide which one you have."""
        log = Log()
        st = R.staff(0, 0, 0)
        meter_row(log, st, "2/4")
        meter_row(log, st, "2/4")
        log.freeze()
        per = groups.run(log).to_json()["per_redundancy"]
        self.assertEqual(per["meter_across_staves"]["uninformative"], 1)
        self.assertEqual(per["meter_across_staves"]["agreement"]["single"], 1)

    def test_the_report_is_json_serialisable(self):
        import json
        log = Log()
        a_system_of(log, 3, ["2/4", "4/4", None])
        log.freeze()
        json.dumps(groups.run(log).to_json(), default=str)


class TestTheGroupStageIsWiredIntoThePipeline(unittest.TestCase):
    """⚠️ Anti-drift. A report computed and never surfaced is the Class-C
    fault this project keeps paying for — 85 warnings on one real document,
    every one inert. This asserts the stage is CALLED, by AST, so removing
    the call fails here rather than quietly emptying the output."""

    def test_run_staged_on_calls_the_group_stage(self):
        import ast
        import inspect
        from tools.omr.staged import pipeline
        tree = ast.parse(inspect.getsource(pipeline.run_staged_on))
        calls = {ast.unparse(n.func) for n in ast.walk(tree)
                 if isinstance(n, ast.Call)}
        self.assertIn("groups.run", calls)

    def test_the_result_carries_the_agreement_report(self):
        from tools.omr.staged import pipeline
        result = pipeline.run_staged_on([])
        self.assertIn("agreement", result)
        self.assertIn("per_redundancy", result["agreement"])


if __name__ == "__main__":
    unittest.main()
