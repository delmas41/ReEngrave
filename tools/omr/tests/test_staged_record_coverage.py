"""Standing check: does anything a reader would SEE come out the far end?

⚠️ A TEST RATHER THAN AN AUDIT, and for the reason `export_coverage.py` is a
test: this family RECURS. The project has paid for detected-then-dropped nine
times in the exporter, each found late by forensics after a metric bucket
grew — and then twice more inside this package, three days old, in
`Ruling.detail` and `Ruling.used`.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged import record_coverage as RC
from tools.omr.tests.test_staged_pipeline import FakeDetector, build_page


class TestNothingIsSilentlyDropped(unittest.TestCase):
    def test_no_ruling_field_dies_in_the_harness(self):
        """⚠️ THE CHECK THAT FOUND BOTH BUGS. It puts a distinctive sentinel in
        every `Ruling` field, runs the REAL harness, and looks for the sentinel
        in the serialised `Verdict`. Nothing is matched by NAME — a field
        carried under a different name still passes, because the question is
        whether the information comes out, not whether the label does."""
        self.assertEqual(RC.ruling_gaps(), [])

    def test_no_populated_field_is_missing_from_the_json(self):
        from tools.omr.staged import adjudicate, gather
        log = gather.gather(build_page(), detector=FakeDetector())
        adjudicate.run(log)
        self.assertEqual(RC.serialisation_gaps(log), [])

    def test_the_report_is_clean(self):
        from tools.omr.staged import adjudicate, gather
        log = gather.gather(build_page(), detector=FakeDetector())
        adjudicate.run(log)
        report = RC.report(log)
        self.assertTrue(report["clean"], report["gaps"])


class TestTheInventoryDescribesTheCodeNotItsHistory(unittest.TestCase):
    """⚠️ An entry that is CLOSED must LEAVE `KNOWN_DROPS`, or the list stops
    describing the exporter and starts describing its past. Same rule as
    `export_coverage.test_the_inventory_has_no_stale_entries`."""

    def test_every_entry_names_a_field_that_exists(self):
        import dataclasses
        from tools.omr.staged.record import Abstention, Observation, Verdict
        types = {c.__name__: c for c in (Observation, Abstention, Verdict)}
        for (carrier, field_name), reason in RC.KNOWN_DROPS.items():
            with self.subTest(entry=f"{carrier}.{field_name}"):
                self.assertIn(carrier, types)
                names = {f.name for f in dataclasses.fields(types[carrier])}
                self.assertIn(field_name, names)
                self.assertGreater(len(reason), 40, "an inventory entry must "
                                   "carry its reason, not just its name")


class TestTheCheckActuallyBites(unittest.TestCase):
    """⚠️ Run RED before green. A coverage check that cannot fail is the same
    silent-null it exists to catch — and this project has shipped a regression
    test that passed vacuously either way."""

    def test_dropping_a_ruling_field_is_detected(self):
        from tools.omr.staged import adjudicate as A

        original = A.adjudicate_one
        src = A.adjudicate_one.__code__
        self.assertIn("used", A.adjudicate_one.__code__.co_names + tuple(
            A.adjudicate_one.__code__.co_varnames))

        # simulate the bug: a Verdict built without the ruling's detail
        import dataclasses
        from tools.omr.staged.record import Verdict
        real = Verdict.to_json

        def blind(self):
            out = real(self)
            out.pop("detail", None)
            out.pop("used", None)
            return out

        Verdict.to_json = blind
        try:
            gaps = {g[1] for g in RC.ruling_gaps()}
            self.assertIn("detail", gaps)
            self.assertIn("used", gaps)
        finally:
            Verdict.to_json = real


if __name__ == "__main__":
    unittest.main()
