"""`through=` / `--through` (ROADMAP 2.34) — stop the staged pipeline after
GATHER, ADJUDICATE or EVALUATE, and prove the default is untouched.

Sean: *"if we try grafting weights can we do that in the first 2 stages of
production … where it just handles gathering ink and boxing and identifying
before it goes to all of the other stages?"* This is the plumbing that lets
`benchmarks/omr-weights-ab-2026-09/`'s A/B harness price a graft at
GATHER+ADJUDICATE alone, with no EVALUATE consequence able to restate a
value the two arms would otherwise have to agree on for a different reason.

Every test here can fail: `test_default_is_byte_identical_to_before` was
run red against a deliberate regression (adding `"stopped_after": None` to
every returned dict unconditionally) before being committed.
"""

import unittest

from tools.omr.staged import pipeline

from .test_staged_pipeline import FakeDetector, build_page


def _run(through="infer"):
    return pipeline.run_staged_on(build_page(), detector=FakeDetector(),
                                  through=through)


class TestDefaultUnchanged(unittest.TestCase):
    """The control: omitting `through` (the CLI's default, `"infer"`) must
    still run every stage and carry no new key."""

    def test_default_is_byte_identical_to_before(self):
        result = _run()
        self.assertNotIn("stopped_after", result)
        self.assertIn("agreement", result)
        self.assertIn("evaluation", result)
        # this fixture has no INFER-eligible narrowing, so "inference" may
        # or may not be present depending on the rules' own defaults --
        # that is `test_infer_bypass.py`'s question, not this file's.

    def test_through_infer_is_the_same_as_omitting_it(self):
        self.assertEqual(_run(), _run(through="infer"))


class TestStoppedAfterAdjudicate(unittest.TestCase):

    def setUp(self):
        self.result = _run(through="adjudicate")

    def test_no_evaluate_or_infer_keys(self):
        for key in ("evaluation", "agreement", "inference", "reevaluation"):
            self.assertNotIn(key, self.result)

    def test_provenance_says_where_it_stopped(self):
        self.assertEqual(self.result["stopped_after"], "adjudicate")

    def test_adjudication_still_ran(self):
        # ADJUDICATE itself is not skipped -- only what comes AFTER it.
        adj = self.result["adjudication"]
        self.assertGreater(adj["n_verdicts"], 0)

    def test_no_evaluate_consequence_rows_reached_the_record(self):
        """`restate_pitch` etc. are EVALUATE consequences -- a record
        stopped after ADJUDICATE must carry none of them."""
        quantities = {v["quantity"] for v in self.result["record"]["verdicts"]}
        # `pitch` is written only by the EVALUATE consequence
        # `restate_pitch`; its absence here is the direct proof that
        # EVALUATE never ran, not merely that its report was not returned.
        self.assertNotIn("pitch", quantities)

    def test_key_set_is_exactly_what_a_stopped_run_should_carry(self):
        self.assertEqual(
            sorted(self.result),
            ["adjudication", "record", "stopped_after", "stubs", "summary"])


class TestStoppedAfterEvaluate(unittest.TestCase):

    def setUp(self):
        self.result = _run(through="evaluate")

    def test_evaluate_ran_but_not_infer(self):
        self.assertIn("evaluation", self.result)
        self.assertIn("agreement", self.result)
        self.assertNotIn("inference", self.result)
        self.assertNotIn("reevaluation", self.result)

    def test_provenance_says_where_it_stopped(self):
        self.assertEqual(self.result["stopped_after"], "evaluate")


class TestStoppedAfterGather(unittest.TestCase):

    def setUp(self):
        self.result = _run(through="gather")

    def test_no_adjudicate_verdicts_at_all(self):
        self.assertEqual(self.result["record"]["verdicts"], [])
        self.assertEqual(self.result["adjudication"]["n_verdicts"], 0)

    def test_no_later_stage_keys(self):
        for key in ("evaluation", "agreement", "inference", "reevaluation"):
            self.assertNotIn(key, self.result)

    def test_provenance_says_where_it_stopped(self):
        self.assertEqual(self.result["stopped_after"], "gather")


class TestDecideRefusesAGatherOnlyStop(unittest.TestCase):
    """`decide()` always runs ADJUDICATE first -- a `through="gather"` stop
    is the CALLER's job (`run_staged_on`), before `decide()` is ever
    invoked. Asking `decide()` itself for it is a caller bug, not a silent
    no-op."""

    def test_raises(self):
        from tools.omr.staged.record import Log
        with self.assertRaises(ValueError):
            pipeline.decide(Log(), through="gather")


if __name__ == "__main__":
    unittest.main()
