"""The per-subject trace and the per-family stage funnel.

⚠️ **THE FIXTURES ARE BUILT BY THE REAL `Log`**, never typed as JSON. *A
fixture that does not match GATHER tests the test* -- this repo's recorded
lesson, which cost `Q.METER_GLYPH` a rule that read no boxes on any real page
while five unit tests stayed green.

⚠️ **EVERY ASSERTION ABOUT A DERIVATION CARRIES ITS OWN FALSIFIER.** The stage
map being total is only worth asserting beside an assertion that a decider
nobody registered comes back `UNATTRIBUTED`; otherwise a `stage_of_decider`
that returned `"ADJUDICATE"` unconditionally would pass.
"""
from __future__ import annotations

import ast
import json
import os
import tempfile
import unittest
from pathlib import Path

from tools.omr.staged import adjudicate as A
from tools.omr.staged import evaluate as E
from tools.omr.staged import export as X
from tools.omr.staged import infer as INF
from tools.omr.staged import record as R
from tools.omr.staged import trace as T
from tools.omr.staged.record import ABSTAIN, Log, Outcome, Q, READERS, Verdict


def _note_log() -> Log:
    """One notehead, walked through GATHER, ADJUDICATE and EVALUATE.

    Built with the real `Log`, so every row carries whatever the harness fills
    and the trace sees exactly the shape a pipeline run writes.
    """
    log = Log()
    g = R.glyph(1, 0, 2, 4, 1)
    st = R.staff(1, 0, 2)
    log.observe(g, Q.GLYPH_BOX, ["noteheadHalfInSpace", 136, 694, 147, 150],
                reader=READERS.DETECTOR, frame="cell:4", score=0.2987)
    log.observe(g, Q.NOTEHEAD_CLASS, "noteheadHalfInSpace",
                reader=READERS.DETECTOR, frame="cell:4", score=0.2987)
    # ⚠️ NO SCORE. A ruler reading is not a guess, and the trace must show the
    # absence rather than a zero.
    log.observe(g, Q.NOTEHEAD_STAFF_POSITION, 7.38, reader=READERS.GEOMETRY,
                frame="cell:4")
    log.abstain(R.cell(1, 0, 2, 4), Q.STEM, reader=READERS.CV_LINES,
                frame="cell:4", reason=ABSTAIN.NO_INK)
    log.observe(R.cell(1, 0, 2, 4), Q.INK, [1, 2, 3, 4],
                reader=READERS.CV_INK, frame="cell:4")
    log.observe(st, Q.CLEF_GLYPH, "clefG", reader=READERS.DETECTOR,
                frame="page")
    # ⚠️ THE ID COMES FROM THE LOG, exactly as `adjudicate_one` takes it
    # (`adjudicate.py:713`). `Log.record` keys `_vrd` on `verdict.id`, so a
    # fixture passing `id=""` to every verdict silently keeps only the LAST
    # one -- which is how the first draft of this file recorded four verdicts
    # and stored one. A fixture that does not match the harness tests the
    # test.
    first = log.record(Verdict(
        id=log._next_id("vrd"), subject=g, quantity=Q.DURATION,
        outcome=Outcome.DECIDED, value={"beats": 1.0},
        decider="adjudicate_duration", reason="head_and_marks"))
    log.record(Verdict(
        id=log._next_id("vrd"), subject=g, quantity=Q.DURATION,
        outcome=Outcome.DECIDED, value={"beats": 2.0},
        decider="reconcile_duration", reason="meter_reconciliation",
        supersedes=first.id))
    log.record(Verdict(
        id=log._next_id("vrd"), subject=g, quantity=Q.PITCH,
        outcome=Outcome.DECIDED, value="F4", decider="restate_pitch",
        reason="position_and_clef"))
    log.record(Verdict(
        id=log._next_id("vrd"), subject=st, quantity=Q.CLEF,
        outcome=Outcome.DECIDED, value="treble", decider="adjudicate_clef",
        reason="scored"))
    return log


def _rec(log: Log) -> X.Record:
    """Through JSON, the way the CLI reads it -- so a field the producer fills
    and `to_json` drops is invisible here too, exactly as it is in production."""
    return X.Record(json.loads(json.dumps({"record": log.to_json()},
                                          default=str)))


class TestTheStageMapIsDerivedAndTotal(unittest.TestCase):

    def test_every_registered_decider_resolves_to_its_own_stage(self):
        A._ensure_decisions()
        E._ensure_rules()
        for spec in A.REGISTRY.values():
            self.assertEqual(T.stage_of_decider(spec.name), "ADJUDICATE",
                             spec.name)
        for rule in E.RULES:
            self.assertEqual(T.stage_of_decider(rule.fn.__name__), "EVALUATE",
                             rule.fn.__name__)

    def test_an_infer_decider_resolves_by_PREFIX(self):
        self.assertEqual(
            T.stage_of_decider(f"{INF.DECIDER_PREFIX}collapse_anything"),
            "INFER")

    def test_a_decider_NOBODY_registered_is_UNATTRIBUTED(self):
        """⚠️ THE FALSIFIER. Without this the assertion above is satisfied by
        a function that returns "ADJUDICATE" for every input."""
        self.assertEqual(T.stage_of_decider("adjudicate_nothing_at_all"),
                         "UNATTRIBUTED")
        self.assertEqual(T.stage_of_decider(""), "UNATTRIBUTED")

    def test_no_decider_is_claimed_by_two_stages(self):
        by = T.deciders_by_stage()
        self.assertEqual(by["ADJUDICATE"] & by["EVALUATE"], frozenset())

    def test_the_stages_come_from_reach_and_exclude_the_non_writers(self):
        stages = T.row_writing_stages()
        self.assertIn("GATHER", stages)
        self.assertIn("ADJUDICATE", stages)
        self.assertNotIn("EXPORT", stages)      # writes no row
        self.assertNotIn("HARNESS", stages)


class TestItDoesNotClaimAnAblation(unittest.TestCase):
    """⚠️ Sean asked to *add each step progressively*; that cannot be run, and
    the module must not imply it can."""

    def test_INFER_is_ablatable_and_the_other_stages_are_not(self):
        ab = T.ablatable()
        self.assertIn("INFER", ab)
        for stage in ("GATHER", "ADJUDICATE", "EVALUATE"):
            self.assertNotIn(stage, ab, f"{stage} has no off switch")

    def test_it_says_what_it_cannot_see(self):
        self.assertTrue(T.WHAT_THIS_CANNOT_SEE)
        joined = " ".join(T.WHAT_THIS_CANNOT_SEE)
        self.assertIn("ACCURACY", joined)


class TestTheTrace(unittest.TestCase):

    def test_it_shows_GATHER_then_ADJUDICATE_then_EVALUATE_in_order(self):
        t = T.trace(_rec(_note_log()), "glyph/1/0/2/4/1")
        seen = [s["stage"] for s in t["steps"]]
        self.assertEqual([s for i, s in enumerate(seen)
                          if i == 0 or seen[i - 1] != s],
                         ["GATHER", "ADJUDICATE", "EVALUATE"])

    def test_a_scoreless_ruler_reading_shows_its_absence_not_a_zero(self):
        t = T.trace(_rec(_note_log()), "glyph/1/0/2/4/1")
        pos = [s for s in t["steps"]
               if s.get("quantity") == Q.NOTEHEAD_STAFF_POSITION][0]
        self.assertIsNone(pos["score"])
        cls = [s for s in t["steps"]
               if s.get("quantity") == Q.NOTEHEAD_CLASS][0]
        self.assertIsNotNone(cls["score"])

    def test_a_GATHER_abstention_on_an_ANCESTOR_is_not_lost(self):
        """The stem abstention is on the CELL; a trace of the glyph must still
        surface it, or the *no ink* finding is invisible from a note."""
        t = T.trace(_rec(_note_log()), "glyph/1/0/2/4/1")
        cells = [c for c in t["context"] if c["subject"] == "cell/1/0/2/4"]
        self.assertEqual(len(cells), 1)
        self.assertGreaterEqual(cells[0]["abstentions"], 1)

    def test_the_ANCESTOR_context_carries_the_staff_clef(self):
        t = T.trace(_rec(_note_log()), "glyph/1/0/2/4/1")
        lines = " ".join(v for c in t["context"] for v in c["verdicts"])
        self.assertIn("clef=treble", lines)

    def test_a_supersession_names_the_prior_value_and_the_DIRECTION(self):
        t = T.trace(_rec(_note_log()), "glyph/1/0/2/4/1")
        ev = [s for s in t["steps"]
              if s["stage"] == "EVALUATE" and s["quantity"] == Q.DURATION][0]
        self.assertEqual(ev["supersedes"]["direction"], "changed_the_value")
        self.assertEqual(ev["supersedes"]["prior_decider"],
                         "adjudicate_duration")
        self.assertEqual(ev["supersedes"]["prior_value"], {"beats": 1.0})

    def test_the_EXPORT_step_ABSTAINS_with_no_report(self):
        """⚠️ *not written* and *nobody asked the exporter* are different
        facts; a fallback returning the first is the conversion this project
        refuses."""
        t = T.trace(_rec(_note_log()), "glyph/1/0/2/4/1")
        self.assertEqual(t["export"]["state"], "declined")

    def test_it_renders(self):
        out = T.render_trace(T.trace(_rec(_note_log()), "glyph/1/0/2/4/1"))
        self.assertIn("GATHER", out)
        self.assertIn("SUPERSEDES", out)


class TestDirectionIsNeverNetted(unittest.TestCase):
    """⚠️ CLAUDE.md's worked example is ADJUDICATE being WRONG and EVALUATE
    fixing it. A funnel reporting only net change shows EVALUATE contributing
    nothing there, so each class is asserted separately."""

    def test_the_five_classes(self):
        d = lambda po, pv, no, nv: T._direction(                # noqa: E731
            {"outcome": po, "value": pv}, {"outcome": no, "value": nv})
        self.assertEqual(d("decided", 1, "decided", 2), "changed_the_value")
        self.assertEqual(d("decided", 1, "decided", 1), "restated_same_value")
        self.assertEqual(d("abstained", None, "decided", 1),
                         "filled_an_abstention")
        self.assertEqual(d("narrowed", None, "decided", 1),
                         "collapsed_a_narrowing")
        self.assertEqual(d("decided", 1, "abstained", None),
                         "withdrew_an_answer")

    def test_a_missing_prior_row_is_NAMED_not_guessed(self):
        self.assertEqual(T._direction(None, {"outcome": "decided"}),
                         "prior_row_absent")


class TestTheFunnel(unittest.TestCase):

    def test_EVERY_family_has_a_population_ROUTE(self):
        """⚠️ THE `note` FAMILY IS WHY THIS EXISTS. Its deciding quantity is
        `Q.PITCH`, which NO adjudicator owns, so a `subjects_from`-only
        derivation reported the best-read family in the pipeline as DEAD."""
        for fam in X.FAMILIES:
            meta = T.family_quantities(fam)
            self.assertTrue(
                meta["population_quantities"] or meta["detector_prefixes"],
                f"{fam} is unreachable by either route")

    def test_the_note_familys_quantity_has_no_adjudicator_and_it_says_so(self):
        meta = T.family_quantities("note")
        self.assertEqual(meta["deciding_quantity"], Q.PITCH)
        self.assertIsNone(A.REGISTRY.get(Q.PITCH))
        self.assertIn("no adjudicator", meta["decided_by"])
        self.assertTrue(meta["detector_prefixes"])

    def test_the_population_comes_from_the_DETECTOR_route_for_notes(self):
        subjects, via = T.population_of(_rec(_note_log()), "note")
        self.assertEqual(subjects, {"glyph/1/0/2/4/1"})
        self.assertEqual(via, {"detector_class": 1})

    def test_an_unknown_family_RAISES_rather_than_returning_empty(self):
        with self.assertRaises(KeyError):
            T.family_quantities("trombone")

    def test_a_family_with_no_ink_on_the_record_is_DEAD_and_says_which(self):
        f = T.funnel(_rec(_note_log()), "wedge")
        self.assertTrue(f["dead"])
        self.assertIn("both routes ran", f["why"])

    def test_n_in_counts_ROWS_and_n_standing_counts_FINAL_answers(self):
        """⚠️ THE DISTINCTION THAT MADE THE COLUMNS CLOSE. The exporter reads
        only the standing verdict, so a funnel counting rows has a different
        denominator -- and a stage whose every row is superseded must not read
        as having decided everything."""
        f = T.funnel(_rec(_note_log()), "note")
        rows = {(s["stage"], s["quantity"]): s for s in f["stages"]}
        adj = rows[("ADJUDICATE", Q.DURATION)]
        ev = rows[("EVALUATE", Q.DURATION)]
        self.assertEqual(adj["n_in"], 1)
        self.assertEqual(adj["n_standing"], 0)     # superseded by EVALUATE
        self.assertEqual(ev["n_standing"], 1)

    def test_every_stage_row_BALANCES_as_an_equality(self):
        f = T.funnel(_rec(_note_log()), "note")
        for s in f["stages"]:
            self.assertTrue(s["balanced"], s)
            self.assertEqual(s["unaccounted"], [], s)

    def test_an_UNKNOWN_outcome_lands_in_unaccounted_and_UNBALANCES(self):
        """⚠️ THE ESCAPE HATCH MUST HAVE TEETH. Without this the balance
        assertion above is satisfied by a row that can never be unbalanced."""
        row = T._stage_row("ADJUDICATE", Q.DURATION,
                           [{"id": "v1", "subject": "glyph/0/0/0/0/0",
                             "outcome": "invented", "reason": "x"}],
                           {}, 1, set())
        self.assertEqual(row["unaccounted"], ["v1"])
        self.assertFalse(row["balanced"])

    def test_the_EXPORT_step_ABSTAINS_rather_than_re_deriving(self):
        f = T.funnel(_rec(_note_log()), "note")
        self.assertEqual(f["export"]["state"], "declined")
        self.assertIn("NEVER re-derived", f["export"]["reason"])

    def test_it_renders(self):
        self.assertIn("POPULATION",
                      T.render_funnel(T.funnel(_rec(_note_log()), "note")))


class TestClaimsEmptyWhileInkIsPresent(unittest.TestCase):

    def test_the_ink_claiming_reason_set_is_DERIVED_and_non_empty(self):
        reasons = T.ink_claiming_reasons()
        self.assertIn(ABSTAIN.NO_INK, reasons)
        # ⚠️ `no_mask` names the missing ERASED IMAGE -- an honest claim about
        # the reader's input, not about the page -- and must stay out.
        self.assertNotIn(ABSTAIN.NO_MASK, reasons)
        self.assertNotIn(ABSTAIN.NO_DETECTIONS, reasons)

    def test_it_finds_a_no_ink_claim_a_Q_INK_row_contradicts(self):
        e = T.empty_claims(_rec(_note_log()))
        self.assertEqual(e["contradicted_total"], 1)
        self.assertIn(f"{Q.STEM}/{ABSTAIN.NO_INK}", e["contradicted"])
        self.assertIn("Q.INK", "".join(e["witness_mix"]))

    def test_the_INK_READERS_OWN_no_ink_is_EXCLUDED(self):
        """⚠️ THE ONE HONEST USE OF THE WORD. It measured the components and
        found none; counting it would be the instrument contradicting itself."""
        log = _note_log()
        log.abstain(R.cell(1, 0, 3, 0), Q.INK, reader=READERS.CV_INK,
                    frame="cell:0", reason=ABSTAIN.NO_INK)
        e = T.empty_claims(_rec(log))
        self.assertEqual(e["claims_by_the_ink_reader_itself"], 1)
        self.assertNotIn(f"{Q.INK}/{ABSTAIN.NO_INK}", e["contradicted"])

    def test_a_no_ink_claim_with_NO_witness_is_not_counted(self):
        """One-sided on purpose: with no ink row and no detection under the
        cell, nothing here contradicts the reader."""
        log = Log()
        log.abstain(R.cell(9, 0, 0, 0), Q.STEM, reader=READERS.CV_LINES,
                    frame="cell:0", reason=ABSTAIN.NO_INK)
        self.assertEqual(T.empty_claims(_rec(log))["contradicted_total"], 0)

    def test_an_HONEST_empty_claim_is_reported_apart_not_as_a_fault(self):
        log = _note_log()
        log.abstain(R.cell(1, 0, 2, 4), Q.METER_GLYPH, reader=READERS.DETECTOR,
                    frame="cell:4", reason=ABSTAIN.NO_DETECTIONS)
        e = T.empty_claims(_rec(log))
        self.assertIn(f"{Q.METER_GLYPH}/{ABSTAIN.NO_DETECTIONS}",
                      e["honest_empty_context"])
        self.assertNotIn(f"{Q.METER_GLYPH}/{ABSTAIN.NO_DETECTIONS}",
                         e["contradicted"])

    def test_it_renders(self):
        self.assertIn("CONTRADICTED",
                      T.render_empty(T.empty_claims(_rec(_note_log()))))


class TestTheCheckCanFail(unittest.TestCase):

    def test_the_controls_are_all_non_zero_on_this_tree(self):
        for name, n in T.controls().items():
            self.assertGreater(n, 0, f"control {name} is at zero")

    def test_check_exits_2_when_a_CONTROL_is_at_zero(self):
        """⚠️ A CHECK THAT CANNOT FAIL IS WORSE THAN NO CHECK. This repo
        emptied one of its own in one line, so the mechanism is exercised
        rather than trusted."""
        real = T.controls
        T.controls = lambda: {"row_writing_stages": 0}
        try:
            self.assertEqual(T.main([]), 0)          # no --check: prints only
            self.assertEqual(T.main(["--check"]), 2)
        finally:
            T.controls = real

    def test_check_exits_1_on_an_unaccounted_problem(self):
        real = T.problems
        T.problems = lambda: ["SOMETHING-NEW nobody inventoried this"]
        try:
            self.assertEqual(T.main(["--check"]), 1)
        finally:
            T.problems = real

    def test_check_passes_on_this_tree(self):
        self.assertEqual(T.main(["--check"]), 0)

    def test_the_gap_inventory_has_no_STALE_entries(self):
        self.assertEqual(T.stale_gaps(T.problems()), [])

    def test_every_problem_is_either_inventoried_or_reported(self):
        probs = T.problems()
        self.assertEqual(T.unaccounted(probs), [])


class TestTheRecordEnvelope(unittest.TestCase):

    def test_a_record_with_no_record_key_RAISES(self):
        """⚠️ A filter that silently empties a file looks exactly like a file
        with nothing in it."""
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False) as f:
            json.dump({"observations": []}, f)
            path = f.name
        try:
            with self.assertRaises(KeyError):
                T._load(path)
        finally:
            os.unlink(path)

    def test_it_reads_the_shape_the_CLI_writes(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False) as f:
            json.dump({"record": _note_log().to_json()}, f, default=str)
            path = f.name
        try:
            self.assertEqual(len(T._load(path).verdicts), 4)
        finally:
            os.unlink(path)


class TestItDeclaresItselfADerivedCheck(unittest.TestCase):
    """⚠️ Without the marker, this module NAMING reason words and quantities
    without CONSUMING them turns live `wiring` gap entries STALE -- the fault
    `capture.py` paid for when it landed."""

    def test_the_marker_is_in_the_exact_AST_SHAPE_wiring_requires(self):
        self.assertTrue(T.DERIVED_CHECK)
        tree = ast.parse(Path(T.__file__).read_text())
        found = [
            node for node in tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "DERIVED_CHECK"
                    for t in node.targets)
            and isinstance(node.value, ast.Constant)
            and node.value.value is True]
        self.assertEqual(len(found), 1,
                         "wiring._declares_derived_check matches a bare "
                         "module-level `DERIVED_CHECK = True` only; an "
                         "annotated assignment would be invisible to it")

    def test_wiring_agrees_that_this_module_is_a_derived_check(self):
        from tools.omr.staged import wiring
        self.assertTrue(wiring._declares_derived_check(Path(T.__file__)))


class TestItDoesNotDuplicateTheExportersLadder(unittest.TestCase):
    """⚠️ `build_sheet.py` held its own copy of *the three refusals in order*,
    the exporter grew to five, and it reported 542 where the real rule refuses
    738. This asserts the copy does not exist here."""

    def test_the_module_names_no_refusal_reason_of_its_own(self):
        src = Path(T.__file__).read_text()
        for invented in ("no_pitch", "owned_by_another_staff",
                         "staff_not_identified", "duration_narrowed"):
            # named in prose is fine; a STRING LITERAL compared against would
            # be a second copy of the rule.
            self.assertNotIn(f'"{invented}"', src, invented)
            self.assertNotIn(f"'{invented}'", src, invented)

    def test_it_calls_the_real_exporter(self):
        src = Path(T.__file__).read_text()
        self.assertIn("X.to_musicxml", src)


if __name__ == "__main__":                                  # pragma: no cover
    unittest.main()
