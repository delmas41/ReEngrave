"""The benchmark harness's tree-stamp guard, and its FALLBACK branch.

⚠️⚠️ THIS FILE EXISTS BECAUSE THE LESSON WAS WRITTEN DOWN AND NOT APPLIED.
CLAUDE.md says of the failed-control family: *"the fallback is where it hides,
because it is the branch nobody exercises and nobody writes a test for"* — and
the guard that sentence describes shipped with its own fallback untested. Both
of its bugs lived exactly there.

⚠️ **A guard's fallback branch is the one place where "cannot tell" gets
silently converted into a definite answer.** In this harness it was converted
into *"same tree"* (two `"unknown"` stamps compared equal; so did two `""`
ones); in a sibling session's provenance stamp it was converted into *"clean"*
(`git rev-parse` succeeding while `git status` failed). Neither conversion is
ever the safe default, and neither branch runs on a machine that has git and a
clean checkout — which is every machine anyone develops on.
"""

from __future__ import annotations

import ast
import importlib.util
import pathlib
import subprocess
import sys

import pytest

_SRC = (pathlib.Path(__file__).resolve().parents[3]
        / "benchmarks" / "omr-staged-meter-boundary-2026-09" / "run_arms.py")


def _load():
    spec = importlib.util.spec_from_file_location("_run_arms", _SRC)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_run_arms"] = mod
    spec.loader.exec_module(mod)
    return mod


run_arms = _load()


class _Proc:
    def __init__(self, out="", rc=0):
        self.stdout, self.returncode, self.stderr = out, rc, ""


class TestATreeThatCannotBeNamedIsNone:
    """The failure value must not be a string, because a string compares equal
    to itself and that is the whole bug."""

    def test_git_missing_is_None_not_a_magic_string(self, monkeypatch):
        monkeypatch.setattr(run_arms.subprocess, "run",
                            lambda *a, **k: (_ for _ in ()).throw(OSError()))
        assert run_arms._tree_id() is None

    def test_a_failed_git_command_is_None_not_empty_string(self, monkeypatch):
        """⚠️ THE BUG THAT NEVER REACHED THE `except`. `subprocess.run` without
        `check=True` reports a non-zero exit as EMPTY STDOUT and raises
        nothing, so outside a git checkout the id was `""` — and two empty
        stamps matched."""
        def fake(*a, **k):
            if k.get("check"):
                raise subprocess.CalledProcessError(128, a[0])
            return _Proc("", rc=128)
        monkeypatch.setattr(run_arms.subprocess, "run", fake)
        assert run_arms._tree_id() is None

    def test_a_dirty_tree_is_None(self, monkeypatch):
        monkeypatch.setattr(run_arms.subprocess, "run",
                            lambda *a, **k: _Proc("abc1234")
                            if "rev-parse" in a[0] else _Proc(" M CLAUDE.md"))
        assert run_arms._tree_id() is None

    def test_a_clean_tree_IS_named(self, monkeypatch):
        """The positive control: without it every assertion above passes for
        free the moment `_tree_id` returns None unconditionally."""
        monkeypatch.setattr(run_arms.subprocess, "run",
                            lambda *a, **k: _Proc("abc1234")
                            if "rev-parse" in a[0] else _Proc(""))
        assert run_arms._tree_id() == "abc1234"

    def test_the_source_uses_check_True_so_the_hole_cannot_return(self):
        """⚠️ An AST guard, not a grep: a `subprocess.run` in `_tree_id`
        without `check=True` silently reinstates the empty-stdout bug."""
        tree = ast.parse(_SRC.read_text())
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "_tree_id")
        calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call)]
        runs = [c for c in calls
                if isinstance(c.func, ast.Attribute) and c.func.attr == "run"]
        assert runs, "no subprocess.run in _tree_id — did it move?"
        for c in runs:
            kw = {k.arg: k.value for k in c.keywords}
            assert "check" in kw and getattr(kw["check"], "value", False) is True, \
                "subprocess.run without check=True returns failure as empty stdout"


class TestAnUnprovableReuseIsRefused:
    """The read side. Refusing costs a re-run; reusing costs a published
    number that is wrong."""

    @pytest.fixture
    def arm(self, tmp_path, monkeypatch):
        monkeypatch.setattr(run_arms, "HERE", tmp_path)
        (tmp_path / "out").mkdir()
        out = tmp_path / "out" / "t-OFF.json"
        out.write_text("{}")
        return out

    def _run(self, **kw):
        return run_arms.run(pathlib.Path("x.pdf"), "0", "t", "OFF",
                            force=False, **kw)

    def test_a_matching_stamp_skips(self, arm, monkeypatch):
        arm.with_suffix(".tree.txt").write_text("abc1234\n")
        monkeypatch.setattr(run_arms, "_tree_id", lambda: "abc1234")
        assert self._run() == arm

    def test_a_missing_stamp_REFUSES(self, arm, monkeypatch):
        monkeypatch.setattr(run_arms, "_tree_id", lambda: "abc1234")
        with pytest.raises(SystemExit):
            self._run()

    def test_a_DIFFERENT_stamp_refuses(self, arm, monkeypatch):
        arm.with_suffix(".tree.txt").write_text("deadbee\n")
        monkeypatch.setattr(run_arms, "_tree_id", lambda: "abc1234")
        with pytest.raises(SystemExit):
            self._run()

    def test_an_UNNAMEABLE_tree_refuses_even_WITH_a_stamp(self, arm, monkeypatch):
        """⚠️⚠️ THE FALLBACK, AND THE BUG THAT WAS HERE. `None == None` is True,
        so an unnameable tree matched a missing stamp and skipped. It must
        refuse even when a stamp is present, because it cannot prove anything
        about it."""
        arm.with_suffix(".tree.txt").write_text("abc1234\n")
        monkeypatch.setattr(run_arms, "_tree_id", lambda: None)
        with pytest.raises(SystemExit):
            self._run()

    def test_NO_stamp_AND_an_unnameable_tree_refuses(self, arm, monkeypatch):
        """⚠️⚠️ THE EXACT COMBINATION THE BUG NEEDED, and the first draft of
        this class did not test it — a mutation restoring `if was == here:`
        SURVIVED all ten tests.

        `was` is None when no stamp exists and `here` is None when the tree
        cannot be named, so `None == None` skipped. My other fallback test
        writes a stamp, which makes `was == here` False and lets the mutant
        pass. Naming the right hazard is not the same as exercising it.
        """
        assert not arm.with_suffix(".tree.txt").exists()
        monkeypatch.setattr(run_arms, "_tree_id", lambda: None)
        with pytest.raises(SystemExit):
            self._run()

    def test_reuse_stale_overrides_but_only_when_asked(self, arm, monkeypatch):
        monkeypatch.setattr(run_arms, "_tree_id", lambda: None)
        assert self._run(reuse_stale=True) == arm
