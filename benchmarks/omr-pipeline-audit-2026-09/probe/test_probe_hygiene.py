"""A probe that globs nothing must not exit 0.

⚠️ THE FAILURE THIS LINTS FOR, which this audit has now produced three ways:
a probe globs a directory, finds nothing, prints a clean all-zero table and
exits 0. Nothing about the output invites suspicion — it is the cached-A/B
shape (`scan_eval` reusing an arm and reporting a flawless "no change"), and
the tell is wall time, not the numbers. It produced the round-2 N4 retraction,
and on 2026-09-07 it was still live in `compare_arms.py`, whose `before` arm
compared nothing and reported no failures.

The designated helper is `_fixtures.py` (19 importers; `_fixtureroot.py`'s own
docstring nominates it as the survivor). Its `fixtures()` raises SystemExit(2)
on an empty glob.

    python3 -m pytest benchmarks/omr-pipeline-audit-2026-09/probe/test_probe_hygiene.py -q
"""
from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent

#: Any one of these in a file that globs means the author thought about empty.
GUARD_TOKENS = (
    "require_nonempty", "_require(", "fixtures(", "REFUSING", "FATAL:",
    "SystemExit", "sys.exit(", "raise ", "expect_at_least",
)

SKIP = {"test_probe_hygiene.py", "_fixtureroot.py"}


def probe_files():
    return sorted(p for p in HERE.glob("*.py") if p.name not in SKIP)


def test_there_are_probes_to_lint():
    """The lint's own version of the bug it lints for: an empty file set would
    make every test below pass vacuously."""
    assert len(probe_files()) >= 20


@pytest.mark.parametrize("path", probe_files(), ids=lambda p: p.name)
def test_a_globbing_probe_carries_an_empty_set_guard(path):
    """MUTATION: delete the `if not arm:` refusal from `compare_arms.py` — that
    file goes red. It was red before 2026-09-07."""
    src = path.read_text()
    if ".glob(" not in src and "glob.glob(" not in src:
        pytest.skip("does not glob")
    assert any(t in src for t in GUARD_TOKENS), (
        f"{path.name} globs and has no refusal on an empty set — it can print "
        "a clean zero and exit 0")


@pytest.mark.parametrize("path", probe_files(), ids=lambda p: p.name)
def test_no_probe_resolves_its_inputs_from_the_cwd(path):
    """Inputs come from `__file__` (or an explicit env override), never the CWD:
    a worktree run would otherwise resolve to nothing.

    MUTATION: replace a `Path(__file__).resolve().parents[n]` root with
    `Path.cwd()` or a bare relative literal — this fails."""
    src = path.read_text()
    assert not re.search(r"\bPath\.cwd\(\)", src), f"{path.name} resolves from the CWD"
    assert not re.search(r"os\.getcwd\(\)\s*\+", src), f"{path.name} joins onto the CWD"


def test_the_designated_helper_resolves_from_file_and_not_from_a_machine_path():
    """⚠️ THE MIRROR DEFECT. `_fixtures.py` guarded against CWD-relative globs
    by hard-coding one machine's home directory, which does not glob nothing —
    it globs ANOTHER TREE, or nothing at all on any other machine, which is the
    same clean-zero-at-exit-0 outcome by a different road.

    MUTATION: restore `DEFAULT_ROOT = "/Users/…"` — this fails."""
    src = (HERE / "_fixtures.py").read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "DEFAULT_ROOT":
                    assert not isinstance(node.value, ast.Constant), (
                        "DEFAULT_ROOT is a literal — it must be derived from "
                        "__file__")
    assert "__file__" in src


def test_the_designated_helper_refuses_an_empty_glob():
    sys.path.insert(0, str(HERE))
    import _fixtures
    with pytest.raises(SystemExit) as exc:
        _fixtures.fixtures("benchmarks/nothing/matches/this/*.nope")
    assert exc.value.code != 0


def test_the_designated_helper_honours_the_env_override(tmp_path):
    sys.path.insert(0, str(HERE))
    import _fixtures
    old = os.environ.get("OMR_FIXTURE_ROOT")
    os.environ["OMR_FIXTURE_ROOT"] = str(tmp_path)
    try:
        assert _fixtures.root() == str(tmp_path)
    finally:
        if old is None:
            os.environ.pop("OMR_FIXTURE_ROOT")
        else:
            os.environ["OMR_FIXTURE_ROOT"] = old


def test_compare_arms_refuses_an_empty_arm(tmp_path):
    """The live instance, end to end."""
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    r = subprocess.run([sys.executable, str(HERE / "compare_arms.py"), str(a), str(b)],
                       capture_output=True, text=True)
    assert r.returncode != 0, "an empty arm reported success"
    assert "REFUSING" in r.stderr


def test_compare_arms_refuses_a_missing_arm(tmp_path):
    b = tmp_path / "b"
    b.mkdir()
    r = subprocess.run([sys.executable, str(HERE / "compare_arms.py"),
                        str(tmp_path / "absent"), str(b)],
                       capture_output=True, text=True)
    assert r.returncode != 0
