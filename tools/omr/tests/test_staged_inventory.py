"""The inventory is DERIVED, and these assert that it stays derived.

⚠️ Every one of these tests would pass against a hand-written table too. What
they actually pin is that the derivation SEES things -- so each is written to
go red if the corresponding source of truth is bypassed.
"""

import unittest

from tools.omr.staged import adjudicate as A
from tools.omr.staged import inventory


class TestDerivedFromTheRegistry(unittest.TestCase):
    def setUp(self):
        self.inv = inventory.build()

    def test_one_row_per_decision_in_ORDER(self):
        self.assertEqual([r["quantity"] for r in self.inv["decisions"]],
                         list(A.ORDER))

    def test_the_registry_and_ORDER_agree(self):
        """A decision registered but absent from ORDER never runs, and one
        named in ORDER with no adjudicator is a hole. Either is a `problem`."""
        A._ensure_decisions()
        self.assertEqual(set(A.REGISTRY), set(A.ORDER))

    def test_stub_flags_come_from_the_decorator_not_from_a_list(self):
        declared = set(A.stubs())
        derived = {r["quantity"] for r in self.inv["decisions"] if r["stub"]}
        self.assertEqual(declared, derived)
        self.assertTrue(declared, "a zero here would be a broken derivation")


class TestTheChecksHaveTeeth(unittest.TestCase):
    """⚠️ A check that cannot fail is worse than no check. Each of these
    proves the corresponding invariant is actually evaluated."""

    def test_an_unsatisfiable_want_is_reported(self):
        """Five of the six stubs want a quantity NOTHING gathers. If this ever
        reads zero, either the gather sites landed (good -- delete the
        expectation) or the check stopped looking (bad)."""
        starved = [p for p in inventory.build()["problems"]
                   if "never gathered" in p]
        self.assertTrue(starved)

    def test_a_late_verdict_dependency_would_be_caught(self):
        """Reverse two entries of ORDER and the ordering check must fire.

        ⚠️ `clef` consumes the `instrument` VERDICT. Running the clef first
        makes that read `None` forever -- silently, because `Evidence.verdict`
        returns None rather than raising. That silence is exactly what this
        check exists to break."""
        order = list(A.ORDER)
        i, c = order.index("instrument"), order.index("clef")
        order[i], order[c] = order[c], order[i]
        rank = {q: n for n, q in enumerate(order)}
        rows = inventory.build()["decisions"]
        sites, indirect = inventory._gather_sites()
        problems = inventory._problems(rows, order, rank, sites)
        self.assertTrue(any("runs AFTER it" in p for p in problems), problems)

    def test_indirectly_observed_quantities_are_not_false_alarms(self):
        """⚠️ THE FIRST VERSION OF THIS SCRIPT FAILED HERE. `gather_cv_lines`
        observes `stem` through a loop variable, so a literal-argument matcher
        called it ungathered and reported `duration` unsatisfiable."""
        sites, indirect = inventory._gather_sites()
        self.assertNotIn("stem", sites)
        self.assertIn("stem", indirect)
        # ⚠️ Specifically the UNSATISFIABLE alarm. `stem` legitimately appears
        # in a different problem — `duration` declares it and never reads it —
        # and matching the bare quantity name made this test fail the moment
        # that second check landed.
        self.assertFalse([p for p in inventory.build()["problems"]
                          if "'stem'" in p and "no gather site" in p])

    def test_a_quantity_that_is_both_observed_and_decided_is_not_a_cycle(self):
        """`system_staff_count` is gathered by `gather_measures` AND decided.
        `system_membership` runs first and reads the OBSERVATION."""
        row = next(r for r in inventory.build()["decisions"]
                   if r["quantity"] == "system_membership")
        kinds = {c["quantity"]: c["kind"] for c in row["consumes"]}
        self.assertEqual(kinds["system_staff_count"], "both")


class TestTheRunColumn(unittest.TestCase):
    def test_a_decision_with_an_empty_domain_writes_no_row(self):
        """⚠️ THE HOLE THE HANDOFF FOUND, reproduced mechanically.

        A stub ABSTAINS and says `not_implemented`; a decision whose
        `subjects_from` domain is empty runs on zero subjects and writes
        NOTHING. The two look identical from the record alone -- only the
        registry says the second was supposed to appear."""
        # a synthetic run whose summary holds no tuplet rows at all
        import json
        import tempfile
        import pathlib
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "run.json"
            p.write_text(json.dumps({"summary": {"clef": {"decided": 3}}}))
            out = inventory.with_run(inventory.build(), str(p))
        self.assertIn("tuplet_ratio", out["run"]["no_row_at_all"])
        row = next(r for r in out["decisions"]
                   if r["quantity"] == "tuplet_ratio")
        self.assertEqual(row["domain"], "tuplet_marker")
        self.assertIsNone(row["run_domain_rows"])

    def test_a_decision_that_fired_is_not_reported_silent(self):
        """The positive control the zero needs beside it."""
        import json
        import tempfile
        import pathlib
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "run.json"
            p.write_text(json.dumps({"summary": {
                q: {"decided": 1} for q in A.ORDER}}))
            out = inventory.with_run(inventory.build(), str(p))
        self.assertEqual(out["run"]["no_row_at_all"], [])


if __name__ == "__main__":
    unittest.main()
