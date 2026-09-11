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
        # ⚠️⚠️ BOTH SIDES ARE EMPTY SINCE 2026-09-11, so the equality above is
        # `set() == set()` and would pass just as well if the derivation were
        # broken to return nothing. It used to be guarded by
        # `assertTrue(declared)` -- an assertion that a stub EXISTS, which is
        # a property of the build's progress and goes red on success. What is
        # guarded now is the DERIVATION itself: a stub declared here must
        # appear in the inventory's own `stub` column.
        import dataclasses
        from unittest import mock
        from tools.omr.staged.record import Q

        real = A.REGISTRY[Q.ARC_KIND]
        with mock.patch.dict(
                A.REGISTRY,
                {Q.ARC_KIND: dataclasses.replace(real, stub=True)}):
            inv2 = inventory.build()
        self.assertIn(Q.ARC_KIND,
                      {r["quantity"] for r in inv2["decisions"] if r["stub"]},
                      "`stub` is not derived from the decorator")


class TestTheChecksHaveTeeth(unittest.TestCase):
    """⚠️ A check that cannot fail is worse than no check. Each of these
    proves the corresponding invariant is actually evaluated."""

    def test_an_unsatisfiable_want_is_reported(self):
        """⚠️ THIS TEST'S OWN INSTRUCTION, FOLLOWED. It used to assert that
        five stubs want a quantity NOTHING gathers, and said: *"if this ever
        reads zero, either the gather sites landed (good — delete the
        expectation) or the check stopped looking (bad)."* On 2026-09-09
        `gather_glyph_families` landed and it reads zero for the good reason —
        so the expectation is gone and what remains is the DISTINCTION: the
        check must still fire on a fabricated starved decision."""
        self.assertEqual(
            [p for p in inventory.build()["problems"]
             if "never gathered" in p], [],
            "the gather sites landed; a hit here is a NEW starved stub")

        fake = {"quantity": "x", "registered": True, "stub": True,
                "domain": [], "declared_and_never_read": [],
                "consumes": [{"quantity": "nothing_observes_this",
                              "kind": "UNSATISFIABLE", "gathered_by": [],
                              "gathered_indirectly_by": []}]}
        problems = inventory._problems([fake], ["x"], {"x": 0}, {}, {})
        self.assertTrue(any("never gathered" in p for p in problems), problems)
        self.assertTrue(any("no gather site" in p for p in problems), problems)

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
        self.assertEqual(row["domain"], ["tuplet_marker"])
        # ⚠️ per-quantity now, because a domain can name more than one:
        # `duration` answers for noteheads AND rests.
        self.assertEqual(row["run_domain_rows"], {"tuplet_marker": None})

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


class TestTheGapListIsAnInventoryNotASuppressionList(unittest.TestCase):
    """⚠️ Same contract as `export_coverage.KNOWN_GAPS`, and for the same
    reason: a `--check` that is permanently red is a check nobody can put in
    CI, and one that hides its failures is worse."""

    def setUp(self):
        self.problems = inventory.build()["problems"]

    def test_every_problem_today_is_on_the_list_with_a_reason(self):
        new = inventory.unaccounted(self.problems)
        self.assertEqual(new, [], f"{len(new)} problem(s) on no entry")
        for reason in inventory.KNOWN_GAPS.values():
            self.assertTrue(reason.strip(), "an entry with no reason")

    def test_a_CLOSED_gap_must_LEAVE_the_list(self):
        """Otherwise the list stops describing the pipeline and starts
        describing its history."""
        stale = inventory.stale_gaps(self.problems)
        self.assertEqual(stale, [], f"{len(stale)} entr(ies) nothing reports")

    def test_a_NEW_problem_is_not_swallowed(self):
        """The teeth: an unlisted problem must be reported, not absorbed."""
        self.assertEqual(
            inventory.unaccounted(["some brand new invariant broke"]),
            ["some brand new invariant broke"])

    def test_the_list_is_not_a_prefix_of_everything(self):
        """A too-loose key would match unrelated problems and suppress them."""
        self.assertIsNone(inventory._gap_key("clef wants 'clef_glyph', which "
                                             "no gather site observes"))
