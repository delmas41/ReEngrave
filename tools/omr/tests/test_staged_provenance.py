"""The provenance stamp, and the FALLBACK branches nobody exercises.

⚠️⚠️ THIS FILE EXISTS BECAUSE OF ONE SENTENCE FROM THE METER/BOUNDARY SESSION:
**a guard can contain the failure it guards against, and the fallback branch is
where it hides — because the fallback is the branch nobody exercises and
nobody writes a test for.** They found two in their own guard:
`except Exception: return "unknown"` (two failing machines stamp the same
string and it compares EQUAL), and `subprocess.run` without `check=True`
(a non-zero exit is empty stdout with no exception, so the id is `""` and two
empty stamps also match).

Checked here: this module is safe from both — `check_output` raises, and the
failure value is `None`, which the consumer refuses on. ⚠️ But it had a THIRD
of the same family that theirs did not: `git rev-parse` succeeding while
`git status` failed left a record claiming a COMMIT with dirtiness UNKNOWN,
and a consumer reading `dirty` as falsy calls that tree CLEAN.

The rule, generalised from their dirty rule: **anything that cannot uniquely
name a tree must never compare equal to anything, including itself.** A
half-named tree is not a named tree.
"""

from __future__ import annotations

import subprocess
import unittest

from tools.omr.staged.__main__ import _provenance


def _control():
    """Load `regather_control.py` — it lives in `benchmarks/`, not a package.

    ⚠️ IT IS LOADED RATHER THAN SKIPPED BECAUSE THE UNTESTED HALF WAS THE
    CONSUMER. See `TestTheConsumerActuallyRefuses` below.
    """
    import importlib.util
    from pathlib import Path
    path = (Path(__file__).resolve().parents[3]
            / "benchmarks" / "omr-staged-notations-2026-09"
            / "regather_control.py")
    spec = importlib.util.spec_from_file_location("_rc", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestTheHappyPath(unittest.TestCase):
    def test_inside_a_checkout_it_names_the_tree(self):
        p = _provenance()
        self.assertTrue(p["commit"], "should name a commit in this repo")
        self.assertIsNotNone(p["dirty"], "and say whether it was dirty")


class TestTheFallbackBranchesNobodyExercises(unittest.TestCase):

    def _under(self, fake):
        real = subprocess.check_output
        subprocess.check_output = fake
        try:
            return _provenance()
        finally:
            subprocess.check_output = real

    def test_git_missing_entirely_invents_NOTHING(self):
        """⚠️ Not `"unknown"`, not `""` — both compare equal to themselves."""
        def boom(*a, **k):
            raise FileNotFoundError("git")
        p = self._under(boom)
        self.assertIsNone(p["commit"])
        self.assertIsNone(p["dirty"])
        self.assertIn("error", p)

    def test_a_HALF_named_tree_claims_no_commit(self):
        """⚠️ THE ONE THIS MODULE ACTUALLY HAD. `rev-parse` succeeds and
        `status` fails: the pre-fix code kept the commit and left `dirty` as
        None, which a consumer reads as CLEAN. The two facts are atomic now —
        both are set together or neither is."""
        def half(args, **k):
            if args[1] == "rev-parse":
                return b"deadbeef" * 5 + b"\n"
            raise subprocess.CalledProcessError(128, args)
        p = self._under(half)
        self.assertIsNone(p["commit"], "a half-named tree is not a named tree")
        self.assertIsNone(p["dirty"])

    def test_it_uses_check_output_and_never_a_silent_run(self):
        """⚠️ Anti-drift on the meter session's second hole: `subprocess.run`
        without `check=True` returns a non-zero exit as EMPTY STDOUT with no
        exception raised, so the id would be `""` and two empty stamps match."""
        import inspect
        src = inspect.getsource(_provenance)
        self.assertIn("check_output", src)
        self.assertNotIn("subprocess.run(", src)


class TestTheConsumerActuallyRefuses(unittest.TestCase):
    """⚠️⚠️ WRITTEN BECAUSE A MUTATION BATTERY FOUND EVERY RULE HERE UNTESTED.

    The four tests above cover `_provenance()` — the WRITER. The refusals in
    `regather_control.check_provenance` — the whole point of the guard, and
    what the commit message claimed — were covered by NOTHING in the suite.
    Five mutations, including deleting the guard's `raise` outright, all
    passed 4/4 green.

    I had verified them by hand once, in a throwaway `/tmp` script, and never
    committed it. **A habit, not a mechanism** — the phrase the meter/boundary
    session used about its own cached-arm guard, arriving in my tests.

    ⚠️ And it is their sharper finding one level on: *a test can be named for
    a hazard it does not reach, and only a mutation says so.* Mine were not
    even named for it. Four green arms are the reassurance that hides the
    fifth; here all five were green.
    """

    def setUp(self):
        self.rc = _control()

    def _refuses(self, before, after):
        with self.assertRaises(SystemExit) as cm:
            self.rc.check_provenance({"provenance": before},
                                     {"provenance": after})
        self.assertEqual(cm.exception.code, 2)

    def _accepts(self, before, after):
        self.rc.check_provenance({"provenance": before}, {"provenance": after})

    CLEAN_A = {"commit": "a" * 40, "dirty": False}
    CLEAN_B = {"commit": "b" * 40, "dirty": False}

    def test_two_distinct_clean_trees_are_ACCEPTED(self):
        """The positive control. Without it every refusal below could pass by
        refusing everything."""
        self._accepts(self.CLEAN_A, self.CLEAN_B)

    def test_an_UNSTAMPED_pair_is_refused(self):
        self._refuses({"commit": None, "dirty": None},
                      {"commit": None, "dirty": None})

    def test_one_unstamped_side_is_enough_to_refuse(self):
        self._refuses(self.CLEAN_A, {"commit": None, "dirty": None})

    def test_the_SAME_clean_tree_twice_is_refused(self):
        """⚠️ `MOVED: nothing` from one tree compared with itself is the
        headline failure this guard exists for."""
        self._refuses(self.CLEAN_A, dict(self.CLEAN_A))

    def test_a_DIRTY_tree_is_refused_even_at_a_different_commit(self):
        """⚠️ A SHA cannot tell two sets of uncommitted edits apart, so a
        dirty stamp proves neither sameness nor difference."""
        self._refuses({"commit": "a" * 40, "dirty": True}, self.CLEAN_B)

    def test_UNKNOWN_dirtiness_is_refused_and_is_not_read_as_clean(self):
        """⚠️ THE THIRD HOLE, and the one with no equality comparison in it: a
        fallback converting *cannot tell* into a definite NEGATIVE. Distinct
        commits, both `dirty: None` — under the pre-fix consumer this passed."""
        self._refuses({"commit": "a" * 40, "dirty": None},
                      {"commit": "b" * 40, "dirty": None})

    def test_allow_unstamped_overrides_but_only_deliberately(self):
        self.rc.check_provenance({"provenance": {"commit": None, "dirty": None}},
                                 {"provenance": {"commit": None, "dirty": None}},
                                 allow_unstamped=True)
