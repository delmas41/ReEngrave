"""The health report is derived, and these prove it can still fail.

⚠️ It reported **"EMPTY CELLS: none"** once by accident, and that is why this
file exists. Crediting a test that iterates `adjudicate.REGISTRY` / `ORDER`
with covering every decision emptied the report in one line — the discipline
tests iterate the whole registry to assert declaration properties, so every
decision looked covered in every shape. A check that cannot fail is worse than
no check, so the over-broad resolution was removed and this pins its absence.
"""

import unittest

from tools.omr.staged import adjudicate as A
from tools.omr.staged import health


class TestTheReportCoversEveryDecision(unittest.TestCase):
    def test_one_row_per_decision_in_ORDER(self):
        h = health.build()
        self.assertEqual(list(h["per_decision"]), list(A.ORDER))

    def test_it_scans_real_test_functions(self):
        rows = health.scan()
        self.assertGreater(len(rows), 200, "the scanner found almost nothing")
        self.assertTrue(any(r["file"] == "test_staged_adjudicate.py"
                            for r in rows))


class TestTheChecksHaveTeeth(unittest.TestCase):
    def test_a_decision_with_no_tests_is_reported(self):
        problems = health._problems({
            "fabricated": {"stub": False, "decides": 0, "abstains": 0,
                           "records": 0, "files": [], "tests": []}})
        self.assertTrue(any("NO staged test names it" in p for p in problems))

    def test_each_missing_shape_is_reported_separately(self):
        problems = health._problems({
            "fabricated": {"stub": False, "decides": 1, "abstains": 0,
                           "records": 0, "files": ["test_x.py"], "tests": []}})
        self.assertTrue(any("ABSTAINS" in p for p in problems))
        self.assertTrue(any("RECORDS" in p for p in problems))

    def test_coverage_from_a_DOWNSTREAM_stage_only_is_reported(self):
        """⚠️ `part_partition` was in exactly this state: every test naming it
        lived in `test_staged_export.py`, which hands the join in as a
        fixture. A decision exercised solely by its consumer is untested."""
        problems = health._problems({
            "fabricated": {"stub": False, "decides": 1, "abstains": 1,
                           "records": 1, "files": ["test_staged_export.py"],
                           "tests": []}})
        self.assertTrue(any("ONLY by downstream tests" in p for p in problems))

    def test_a_stub_is_exempt_from_DECIDES_and_from_nothing_else(self):
        problems = health._problems({
            "fabricated": {"stub": True, "decides": 0, "abstains": 1,
                           "records": 1, "files": ["test_x.py"], "tests": []}})
        self.assertEqual(problems, [])
        problems = health._problems({
            "fabricated": {"stub": True, "decides": 0, "abstains": 0,
                           "records": 1, "files": ["test_x.py"], "tests": []}})
        self.assertTrue(any("not_implemented" in p for p in problems))


class TestDynamicNamingIsResolvedButBounded(unittest.TestCase):
    def test_a_test_iterating_stubs_counts_as_naming_every_stub(self):
        """`test_each_stub_abstains_with_not_implemented_and_records_it`
        iterates `adjudicate.stubs()` and writes no `Q.ARC_OWNER`."""
        rows = health.scan()
        hit = [r for r in rows
               if r["test"] == "test_each_stub_abstains_with_not_implemented_and_records_it"]
        self.assertTrue(hit, "the test this asserts about has been renamed")
        # ⚠️ ARC_OWNER left this list on 2026-09-09 when it was filled.
        self.assertIn("WEDGE_ANCHOR", hit[0]["quantities"])

    def test_iterating_the_REGISTRY_does_NOT_credit_every_decision(self):
        """⚠️ THE ONE THAT KEEPS THE REPORT HONEST. Resolving `REGISTRY` /
        `ORDER` the way `stubs()` is resolved took EMPTY CELLS to none."""
        rows = health.scan()
        registry_tests = [r for r in rows
                          if r["file"] == "test_staged_discipline.py"]
        self.assertTrue(registry_tests)
        credited = {q for r in registry_tests for q in r["quantities"]}
        self.assertNotIn("MEASURE_PARTITION", credited)


if __name__ == "__main__":
    unittest.main()
