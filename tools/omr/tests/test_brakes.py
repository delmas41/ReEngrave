"""The brake audit must be able to FAIL.

⚠️ Every assertion here is about the INSTRUMENT, never about the pipeline's
numbers: a test that pins "25 instrument abstentions" would go red the day the
reader improves, which is the opposite of what this audit wants.
"""
import unittest

from tools.omr.staged import adjudicate, brakes, infer, reach


class TestTheQuestionsCanRun(unittest.TestCase):
    """⚠️ The recorded hazard: `adjudicate.REGISTRY` is EMPTY on a bare import
    and `infer.RULES` likewise. A sibling audit's first run iterated NOTHING
    and printed a clean zero; this module's own first draft did it twice."""

    def test_the_registry_is_populated(self):
        self.assertTrue(adjudicate.REGISTRY,
                        "REGISTRY empty — importing brakes must populate it")

    def test_the_infer_rules_are_populated(self):
        self.assertTrue(infer.RULES,
                        "infer.RULES empty — Q1 would read 100% reachable")

    def test_no_control_is_zero(self):
        for name, value in brakes.controls().items():
            self.assertGreater(value, 0, f"control {name} is zero")


class TestTheCheckIsNotVacuous(unittest.TestCase):

    def test_every_question_finds_something(self):
        """A question that reports nothing at all is indistinguishable from
        one that did not run."""
        self.assertTrue(brakes.readings_gap(), "Q4 found nothing")
        findings, unresolved = brakes.vocabulary_gap()
        self.assertTrue(findings or unresolved, "Q5 found nothing")

    def test_a_new_readings_gap_is_UNACCOUNTED(self):
        """The positive control on Q4: plant one, it must be caught."""
        victim = adjudicate.REGISTRY["duration"]
        original = adjudicate.READINGS.get("duration")
        try:
            adjudicate.READINGS["duration"] = tuple(original) + ("staff_skew",)
            self.assertNotIn("staff_skew", victim.wants)
            bad, lines = brakes.check()
            self.assertEqual(bad, 1)
            self.assertTrue(any("UNACCOUNTED (readings)" in l and "staff_skew" in l
                                for l in lines), lines)
        finally:
            adjudicate.READINGS["duration"] = original

    def test_a_closed_gap_goes_STALE(self):
        """An entry nothing reports any more must LEAVE the list — the
        `export_coverage.KNOWN_GAPS` contract."""
        brakes.ACCOUNTED_READINGS[("nonexistent", "nowhere")] = "planted"
        try:
            bad, lines = brakes.check()
            self.assertEqual(bad, 1)
            self.assertTrue(any("STALE (readings)" in l for l in lines), lines)
        finally:
            del brakes.ACCOUNTED_READINGS[("nonexistent", "nowhere")]

    def test_a_dynamic_reason_module_is_UNRESOLVED_not_a_finding(self):
        """Reporting it as a finding is how the first draft accused eight
        decisions of a fault two have."""
        findings, unresolved = brakes.vocabulary_gap()
        finding_modules = {r["module"] for r in findings}
        unresolved_modules = {r["module"] for r in unresolved}
        self.assertFalse(finding_modules & unresolved_modules,
                         "a module cannot be both resolved and not")
        self.assertTrue(unresolved, "no module computes a reason — suspicious")


class TestTheRecordQuestions(unittest.TestCase):
    """⚠️ `considered`/`used` hold ROW IDS; `missing`/`declined`/`excluded`
    hold QUANTITY NAMES. The first draft mixed them and reported 3,674
    unconsulted cells where there are 125."""

    def _record(self):
        return {"record": {
            "observations": [
                {"id": "obs:1", "subject": "staff/0/0/0",
                 "quantity": "margin_label"},
                {"id": "obs:2", "subject": "document",
                 "quantity": "roster_entry"},
            ],
            "verdicts": [
                {"id": "vrd:1", "subject": "staff/0/0/0",
                 "quantity": "instrument", "outcome": "abstained",
                 "reason": "no_evidence", "considered": ["obs:1"],
                 "used": [], "missing": [], "declined": [], "excluded": []},
            ],
            "abstentions": [],
        }}

    def test_a_consulted_want_is_not_reported_unconsulted(self):
        """`margin_label` is reached THROUGH its row id in `considered`."""
        m = brakes.measure(self._record())
        keys = list(m["unconsulted"])
        self.assertFalse(any(k.endswith("/margin_label") for k in keys), keys)

    def test_an_unconsulted_want_at_an_ANCESTOR_is_reported(self):
        """`roster_entry` is filed on the DOCUMENT and declared by
        `instrument`; the verdict never touched it."""
        m = brakes.measure(self._record())
        self.assertIn("instrument/no_evidence/roster_entry", m["unconsulted"])

    def test_an_empty_considered_is_BLIND(self):
        rec = self._record()
        rec["record"]["verdicts"][0]["considered"] = []
        m = brakes.measure(rec)
        self.assertEqual(m["blind"].get("instrument/no_evidence"), 1)

    def test_a_decided_verdict_is_not_examined(self):
        rec = self._record()
        rec["record"]["verdicts"][0]["outcome"] = "decided"
        m = brakes.measure(rec)
        self.assertEqual(m["unresolved_verdicts"], 0)

    def test_the_handoff_counts_only_registered_INFER_targets(self):
        m = brakes.measure(self._record())
        self.assertEqual(m["reaches_infer"], 0)
        self.assertEqual(m["stops_with_no_stage"], 1)


class TestItIsRegisteredWithItsSiblings(unittest.TestCase):

    def test_reach_accounts_for_this_module(self):
        """⚠️ `reach.unaccounted_modules()` fails on any staged `.py` in
        neither list — CLAUDE.md records committing `capture.py` breaking
        `wiring --check` for exactly this reason."""
        self.assertEqual(reach.unaccounted_modules(), [])
        self.assertIn("brakes.py", reach.NOT_A_STAGE)

    def test_it_declares_itself_a_derived_check(self):
        self.assertTrue(getattr(brakes, "DERIVED_CHECK", False))


if __name__ == "__main__":
    unittest.main()
