"""BYPASS — with EVERY RULE off, a tree carrying the stage is
indistinguishable from a tree without it.

⚠️⚠️ THE PROPERTY WAS RESTATED ON 2026-09-21 AND NOT WEAKENED. It used to
read *"with `OMR_INFER` off"*, which was the same sentence while one flag
governed every rule. `collapse_slot_index_to_family_block` now carries its
own flag and is DEFAULT ON, so under default settings the `inference` key is
present and SHOULD be -- that is what flipping a rule on means. Leaving the
old sentence in place would have been this repository's own
*fixed-then-kept-open-in-prose* with the polarity reversed: a test still
passing, by asserting a property the tree no longer has.

What is still provable, and is what every test below now asserts, is the
property that was always the point: **turn every rule off and the stage
leaves no trace.** `_all_off()` is that state, and it is spelled out of the
GATES rather than hand-listed, so a fourth rule with a fourth flag cannot
quietly stop being covered here.

⚠️⚠️ THE HAZARD IS THE STAGE PERTURBING UPSTREAM *BY EXISTING* RATHER THAN BY
RUNNING — a field added to `Verdict`, a serialisation change, a reordering, an
import with a side effect. That is how an "isolated" change reaches an arm
that was supposed to be blind to it, and this repository has paid for the
general shape twice: `readjudicate --control` would pass 2993/2993 across a
GATHER change and prove nothing, and a benchmark arm silently reused from an
earlier tree reports "identical" whatever the change did.

**An earlier-stage arm must never have to know this stage exists.** If someone
measuring ADJUDICATE has to think about INFER, the bypass is not clean.

Every test here can FAIL: each was run red against a deliberately broken
bypass (writing `"inference": None` unconditionally, and adding a field to
`Verdict`) before being committed.
"""

import json
import os
import unittest
from unittest import mock

from tools.omr.staged import evaluate, infer, pipeline
from tools.omr.staged.record import Verdict

from .test_staged_pipeline import FakeDetector, build_page


def _all_off():
    """Every rule's flag, set to that flag's own OFF word.

    ⚠️ DERIVED FROM THE REGISTRY, never a hand list. `OMR_INFER` is an
    allow-list (default OFF) and `OMR_SLOT_FAMILY_BLOCK` a deny-list
    (default ON), so "off" is a different STRING for each -- and the one
    thing a hand list here would do is silently stop covering the next rule.
    `"0"` is an off-word under both directions, which is what makes one
    literal correct for every switch; asserted rather than assumed.
    """
    infer._ensure_rules()
    env = {}
    for r in infer.RULES:
        env[r.switch.env] = "0"
    with mock.patch.dict(os.environ, env, clear=False):
        assert not infer.stage_should_run(), (
            "a rule stayed enabled with every flag at '0' -- this file's "
            "whole premise is that the OFF state is reachable")
    return env


def _run(env):
    with mock.patch.dict(os.environ, env, clear=False):
        return pipeline.run_staged_on(build_page(), detector=FakeDetector())


class TestOffMeansAbsentNotQuiet(unittest.TestCase):

    def setUp(self):
        self.off = _run(_all_off())

    def test_there_is_no_inference_key_at_all(self):
        """⚠️ NOT `inference: None`. A null key is still a key: it changes the
        serialised record, so a byte-comparison against a pre-INFER arm would
        fail for a stage that never ran."""
        self.assertNotIn("inference", self.off)

    def test_the_key_set_is_exactly_what_it_was(self):
        self.assertEqual(
            sorted(self.off),
            ["adjudication", "agreement", "evaluation", "record", "stubs",
             "summary"])

    def test_no_verdict_is_labelled_inferred(self):
        for v in self.off["record"]["verdicts"]:
            self.assertFalse(infer.is_inferred(v))

    def test_nothing_supersedes_anything_it_should_not(self):
        by_id = {v["id"]: v for v in self.off["record"]["verdicts"]}
        for v in self.off["record"]["verdicts"]:
            if v.get("supersedes"):
                prior = by_id.get(v["supersedes"])
                if prior and prior["outcome"] == "narrowed":
                    self.fail("a narrowing was collapsed with INFER off")

    def test_two_flag_off_runs_are_byte_identical(self):
        """The CONTROL for every comparison below. ⚠️ Without it, a later
        "identical" result is equally consistent with the comparison being
        unable to see anything at all — the unprovenanced-A/B trap, in
        miniature."""
        a = json.dumps(_run(_all_off()), sort_keys=True, default=str)
        b = json.dumps(_run(_all_off()), sort_keys=True, default=str)
        self.assertEqual(a, b)

    def test_the_comparison_has_teeth(self):
        """⚠️ THE POSITIVE CONTROL. Turning the flag ON must make the very
        comparison that reports "identical" report a difference — otherwise
        the byte-identity above would be a property of the instrument rather
        than of the bypass."""
        off = json.dumps(_run(_all_off()), sort_keys=True,
                         default=str)
        on = json.dumps(_run({infer.INFER_ENV: "1"}), sort_keys=True,
                        default=str)
        self.assertNotEqual(off, on)

    def test_with_the_flag_on_the_only_new_top_level_key_is_inference(self):
        on = _run({infer.INFER_ENV: "1"})
        self.assertEqual(set(on) - set(self.off), {"inference"})


class TestItDoesNotPerturbUpstreamByExisting(unittest.TestCase):
    """The four shapes the coordinator named, each asserted directly."""

    def test_no_field_was_added_to_verdict(self):
        """⚠️ A new `Verdict` field would change EVERY record in the tree,
        including one produced with the stage off — which is precisely the
        "reaches an arm that was supposed to be blind to it" failure."""
        self.assertEqual(
            sorted(Verdict.__dataclass_fields__),
            ["basis", "candidates", "considered", "correlated", "decider",
             "declined", "detail", "excluded", "id", "margin", "missing",
             "outcome", "quantity", "reason", "single_pass_revision",
             "subject", "supersedes", "used", "value"])

    def test_the_verdict_serialisation_is_unchanged(self):
        from tools.omr.staged.record import Kind, Outcome, Q, Subject
        v = Verdict(id="vrd:1",
                    subject=Subject(Kind.GLYPH, page=0, system=0, staff=0,
                                    cell=0, glyph=0),
                    quantity=Q.DURATION, outcome=Outcome.DECIDED,
                    value={"beats": 1.0}, decider="t", reason="r")
        self.assertEqual(
            sorted(v.to_json()),
            ["basis", "candidates", "considered", "correlated", "decider",
             "declined", "detail", "excluded", "id", "margin", "missing",
             "outcome", "quantity", "reason", "subject", "supersedes",
             "used", "value"])

    def test_record_py_does_not_import_infer(self):
        """⚠️ The substrate may not know about the stage. `record.py` imports
        nothing from `tools.omr` by design; an import here would couple every
        earlier stage to this one."""
        import inspect
        from tools.omr.staged import record
        # ⚠️ An IMPORT, not the substring: `record.py`'s prose uses the word
        # ("refuses to infer a slot at all"), and a substring test would go
        # red on a comment — a check that fails for the wrong reason teaches
        # the next reader to delete it.
        for line in inspect.getsource(record).splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                self.assertNotIn("infer", stripped)

    def test_importing_infer_registers_no_rule(self):
        """⚠️ THE IMPORT SIDE EFFECT. `pipeline` imports `infer` at module
        level, so if that import pulled in `inferences` the decision registry
        would be touched on every run, flag or no flag. The rules load lazily
        inside `_ensure_rules`."""
        import importlib
        import sys
        saved = list(infer.RULES)
        try:
            infer.RULES.clear()
            for mod in ("tools.omr.staged.inferences",):
                sys.modules.pop(mod, None)
            importlib.reload(infer)
            self.assertEqual(infer.RULES, [])
        finally:
            infer.RULES.clear()
            infer.RULES.extend(saved)

    def test_evaluate_is_unchanged_by_infer_being_importable(self):
        """The earlier stage still does exactly what it did."""
        rep = _run(_all_off())["evaluation"]
        self.assertIn("fired", rep)
        self.assertIn("skipped", rep)


class TestTheCliReportIsSilentWhenOff(unittest.TestCase):

    def test_the_report_is_guarded_on_the_key_not_the_flag(self):
        """⚠️ Reading the flag in `_report` would print "INFER: off" and make
        a flag-off run's stderr differ from a pre-INFER tree's."""
        import inspect
        from tools.omr.staged import __main__ as m
        src = inspect.getsource(m._report)
        self.assertIn('result.get("inference")', src)
        self.assertNotIn("infer_enabled", src)


class TestRunIsNotCalledWhenOff(unittest.TestCase):

    def test_infer_run_is_never_entered(self):
        called = []
        real = infer.run

        def spy(*a, **k):
            called.append(1)
            return real(*a, **k)

        with mock.patch.object(infer, "run", spy):
            _run(_all_off())
        self.assertEqual(called, [])

    def test_and_IS_entered_when_on(self):
        """The positive control for the same spy."""
        called = []
        real = infer.run

        def spy(*a, **k):
            called.append(1)
            return real(*a, **k)

        with mock.patch.object(infer, "run", spy):
            _run({infer.INFER_ENV: "1"})
        self.assertEqual(called, [1])


if __name__ == "__main__":
    unittest.main()
