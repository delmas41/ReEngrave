"""ROADMAP 0.5 / 3.4b-check: a producer OUTSIDE the pipeline (a human reader)
must be WIRED into the derived checks, never explained away by a hand-typed
`KNOWN_GAPS` entry -- and it must never be mistaken for a GATHER site.

⚠️ Every test here is written to go RED against the tree this lane found:
before `producers.py` existed, `inventory.build()` reported nine decisions
wanting `Q.HUMAN_BOX_VERDICT` as UNSATISFIABLE (a producer that plainly
exists, `review/human_evidence.py`, reclassified as a hole) and
`gather_coverage.report()` silently counted `HUMAN_BOX_VERDICT` and
`HUMAN_VERDICT_STANCE` as "declared, never gathered" with no explanation at
all. `test_the_nine_...` and `test_gather_coverage_...` below are the record
of that RED state, reproduced by disabling the repair rather than by
reverting it.

⚠️ THE COUNT IS 12 TODAY, NOT 9 — ROADMAP 3.4g-4 added three more human-only
family decisions (`flag_is_not_a_flag`, `keysig_marker_is_not_a_marker`,
`tuplet_marker_is_not_a_marker`) on the same pattern after this lane landed,
and `producers.py`'s classification covers them for free because it reads
`review/human_evidence.py`'s own AST rather than a hand-typed list. The tests
below say which count is a frozen historical snapshot (the original nine, by
name) and which is a live property of the current registry (12).
"""
from __future__ import annotations

import unittest
from unittest import mock

from tools.omr.staged import adjudicate as A
from tools.omr.staged import gather_coverage as GC
from tools.omr.staged import inventory
from tools.omr.staged import producers as OOP
from tools.omr.staged import reach as R
from tools.omr.staged.record import Q


class TestTheRegistryIsDerivedNotHandTyped(unittest.TestCase):
    """`filed()`/`all_filed()` must read `human_evidence.py`'s OWN AST, never
    a list somebody typed once and forgot."""

    def test_human_evidence_files_human_box_verdict_and_stance(self):
        filed = OOP.filed("review/human_evidence.py")
        self.assertIn(Q.HUMAN_BOX_VERDICT, filed)
        self.assertIn(Q.HUMAN_VERDICT_STANCE, filed)
        # ⚠️ Also the three box quantities a human's box can carry — proof
        # the scan is not special-cased to just the two label quantities.
        self.assertIn(Q.GLYPH_BOX, filed)
        self.assertIn(Q.NOTEHEAD_CLASS, filed)
        self.assertIn(Q.NOTEHEAD_STAFF_POSITION, filed)

    def test_all_filed_keys_by_the_Q_VALUE_not_the_attribute_name(self):
        """A lookup against `spec.wants` uses the STRING VALUE
        (`"human_box_verdict"`), never the bare attribute spelling
        (`"HUMAN_BOX_VERDICT"`) -- the first version of this module got this
        backwards and every consumer's lookup silently missed."""
        all_filed = OOP.all_filed()
        self.assertIn("human_box_verdict", all_filed)
        self.assertNotIn("HUMAN_BOX_VERDICT", all_filed)

    def test_producer_is_registered_as_NOT_A_STAGE(self):
        """`producers.py` itself must never be scanned by `reach.survey()` as
        a stage -- it NAMES quantities to audit them and produces none at
        run time, same discipline as `capture.py`/`meaning.py`/`brakes.py`."""
        self.assertIn("producers.py", R.NOT_A_STAGE)
        self.assertEqual(R.unaccounted_modules(), [])


class TestTheControlsCanFail(unittest.TestCase):
    """CLAUDE.md rule 7: a control must be able to fail. Each of these proves
    the corresponding repair is actually doing something, by disabling it and
    watching the old, wrong answer come back."""

    def test_a_declared_writer_that_does_not_exist_RAISES(self):
        with mock.patch.dict(
                OOP.OUT_OF_PIPELINE,
                {"review/human_evidence.py": ("_obs_json", "_no_such_fn")}):
            problems = OOP.check()
            self.assertTrue(
                any("_no_such_fn" in p for p in problems), problems)
            with self.assertRaises(ValueError):
                OOP.validate()

    def test_a_producer_entry_that_files_nothing_RAISES(self):
        """A declared producer whose AST search comes back empty -- every
        writer function exists, but none is ever called with a literal
        `Q.X` -- is a dead entry, and `validate()` must not pass it
        quietly. `filed()` itself is exercised elsewhere
        (`TestTheRegistryIsDerivedNotHandTyped`); this isolates `check()`'s
        OWN reaction to an empty result."""
        with mock.patch.object(OOP, "filed", return_value={}):
            problems = OOP.check()
            self.assertTrue(
                any("files NOTHING" in p for p in problems), problems)
            with self.assertRaises(ValueError):
                OOP.validate()

    def test_a_want_no_producer_anywhere_files_is_STILL_reported(self):
        """⚠️ THE CONTROL THIS REPAIR MUST NOT BREAK. With the out-of-pipeline
        registry disabled (as if `producers.py` did not exist), a decision
        wanting `Q.HUMAN_BOX_VERDICT` must go back to being reported
        UNSATISFIABLE -- proving the new `out_of_pipeline` classification is
        what suppresses the finding today, not some unrelated change.

        ⚠️ 12, NOT 9: ROADMAP 3.4g-4 added three more human-only family
        decisions (`flag_is_not_a_flag`, `keysig_marker_is_not_a_marker`,
        `tuplet_marker_is_not_a_marker`) to the nine this lane found, and the
        count is a property of the CURRENT registry, not a frozen historical
        one -- `test_reproduces_the_RED_state_this_lane_found` below is the
        one test that pins the original nine BY NAME."""
        with mock.patch.object(OOP, "all_filed", return_value={}):
            inv = inventory.build()
        unsatisfiable_human = [
            p for p in inv["problems"]
            if "human_box_verdict" in p and "no gather site" in p]
        self.assertEqual(len(unsatisfiable_human), 12, inv["problems"])

    def test_reproduces_the_RED_state_this_lane_found(self):
        """The exact shape reported before this repair: nine decisions,
        UNSATISFIABLE, with the out-of-pipeline registry disabled.

        ⚠️ ROADMAP 3.4g-4 ADDED THREE MORE, ON THE SAME PATTERN, AFTER THIS
        LANE LANDED: `flag_is_not_a_flag`, `keysig_marker_is_not_a_marker`,
        `tuplet_marker_is_not_a_marker` are asserted SEPARATELY below rather
        than folded into the historical nine, so this list stays the exact
        RED state this lane's own commit found and fixed."""
        with mock.patch.object(OOP, "all_filed", return_value={}):
            inv = inventory.build()
        decisions = sorted(
            p.split(" wants ")[0] for p in inv["problems"]
            if "human_box_verdict" in p and "no gather site" in p)
        original_nine = [
            "ledger_is_not_a_ledger", "notehead_is_not_a_notehead",
            "accidental_is_not_an_accidental", "rest_is_not_a_rest",
            "arpeggiato_is_not_an_arpeggiato", "arc_is_not_an_arc",
            "dynamic_is_not_a_dynamic", "articulation_is_not_an_articulation",
            "glyph_owner"]
        added_by_3_4g_4 = [
            "flag_is_not_a_flag", "keysig_marker_is_not_a_marker",
            "tuplet_marker_is_not_a_marker"]
        self.assertEqual(decisions, sorted(original_nine + added_by_3_4g_4))


class TestInventoryClassifiesOutOfPipelineCorrectly(unittest.TestCase):
    """The GREEN state: with the real registry, none of the nine decisions
    reports UNSATISFIABLE for `human_box_verdict`, and the classification
    that suppresses it is visibly `out_of_pipeline`, never folded into a
    GATHER site."""

    def setUp(self):
        self.inv = inventory.build()

    def test_no_human_box_verdict_problem_remains(self):
        hits = [p for p in self.inv["problems"] if "human_box_verdict" in p]
        self.assertEqual(hits, [], hits)

    def test_glyph_owner_wants_human_box_verdict_out_of_pipeline(self):
        row = next(r for r in self.inv["decisions"]
                   if r["quantity"] == "glyph_owner")
        c = next(c for c in row["consumes"]
                if c["quantity"] == "human_box_verdict")
        self.assertEqual(c["kind"], "out_of_pipeline")
        self.assertEqual(c["out_of_pipeline_producer"],
                         "review/human_evidence.py")
        # ⚠️ NEVER COUNTED AS A GATHER SITE.
        self.assertEqual(c["gathered_by"], [])
        self.assertEqual(c["gathered_indirectly_by"], [])

    def test_KNOWN_GAPS_no_longer_carries_the_nine_closed_entries(self):
        for key in inventory.KNOWN_GAPS:
            self.assertNotIn("human_box_verdict", key, key)

    def test_the_gap_list_is_still_consistent(self):
        """Every remaining problem is on `KNOWN_GAPS` and no entry is stale
        -- the same contract `test_staged_inventory.py` already enforces,
        reasserted here because this lane rewrote the list."""
        problems = self.inv["problems"]
        self.assertEqual(inventory.unaccounted(problems), [])
        self.assertEqual(inventory.stale_gaps(problems), [])


class TestGatherCoverageLabelsTheProducerHuman(unittest.TestCase):
    """`gather_coverage.py` had NO explanation apparatus at all for this --
    the two human quantities just inflated `declared_ungathered` forever."""

    def setUp(self):
        self.rep = GC.report()

    def test_human_quantities_are_out_of_pipeline_not_declared_ungathered(self):
        ng = self.rep["not_gathered"]
        self.assertNotIn("HUMAN_BOX_VERDICT", ng["declared_ungathered"])
        self.assertNotIn("HUMAN_VERDICT_STANCE", ng["declared_ungathered"])
        self.assertIn("HUMAN_BOX_VERDICT", ng["out_of_pipeline"])
        self.assertIn("HUMAN_VERDICT_STANCE", ng["out_of_pipeline"])

    def test_wanted_but_out_of_pipeline_names_the_nine_decisions(self):
        """⚠️ 12, NOT 9 — see `test_reproduces_the_RED_state_this_lane_found`
        for why: ROADMAP 3.4g-4 added three more human-only family decisions
        on the same pattern after this lane landed."""
        who = self.rep["wanted_but_out_of_pipeline"]["HUMAN_BOX_VERDICT"]
        self.assertEqual(len(who), 12, who)
        self.assertNotIn("HUMAN_BOX_VERDICT",
                         self.rep["wanted_but_ungathered"])

    def test_disabling_the_registry_reproduces_the_RED_count(self):
        """The same disable-and-watch-it-fail control, one level up: with no
        out-of-pipeline producer declared, both human quantities fall back
        into `declared_ungathered`."""
        with mock.patch.object(OOP, "all_filed", return_value={}):
            rep = GC.report()
        self.assertIn("HUMAN_BOX_VERDICT",
                      rep["not_gathered"]["declared_ungathered"])
        self.assertIn("HUMAN_VERDICT_STANCE",
                      rep["not_gathered"]["declared_ungathered"])


class TestTheSecondBlindSpotRestPosition(unittest.TestCase):
    """ROADMAP 0.5's second half: `inventory._gather_sites` used to walk only
    `gather.py`'s AST, so every quantity `positions.py` observes -- including
    `Q.REST_POSITION`, routed through its own `_STEP_FAMILIES` table rather
    than named literally inside the recording function -- was invisible to
    it. `reach.py`'s own `Q.REST_POSITION` entry named this as the reason the
    quantity is not yet declared in any decision's `wants`."""

    def test_rest_position_and_its_five_siblings_are_now_seen(self):
        sites, indirect = inventory._gather_sites()
        for q in ("rest_position", "arc_position", "articulation_position",
                  "fermata_position", "ornament_position",
                  "tuplet_marker_position"):
            self.assertTrue(q in sites or q in indirect,
                           f"{q} still invisible to _gather_sites")

    def test_a_decision_wanting_rest_position_would_be_a_measurement(self):
        """The end-to-end proof: fabricate a decision wanting
        `Q.REST_POSITION` (nobody declares it today -- `rhythm.py` says why)
        and confirm `build()` no longer classifies it UNSATISFIABLE."""
        import dataclasses
        real = A.REGISTRY[Q.DURATION]
        widened = dataclasses.replace(
            real, wants=tuple(real.wants) + (Q.REST_POSITION,))
        with mock.patch.dict(A.REGISTRY, {Q.DURATION: widened}):
            inv = inventory.build()
        row = next(r for r in inv["decisions"] if r["quantity"] == "duration")
        c = next(c for c in row["consumes"] if c["quantity"] == "rest_position")
        self.assertIn(c["kind"], ("measurement", "both"))
        self.assertNotEqual(c["kind"], "UNSATISFIABLE")

if __name__ == "__main__":
    unittest.main()
