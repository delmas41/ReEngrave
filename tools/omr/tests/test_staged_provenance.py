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
