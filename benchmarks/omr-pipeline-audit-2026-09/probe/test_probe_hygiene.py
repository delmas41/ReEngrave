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


#: ⚠️ A hard-coded checkout is tolerated in exactly one shape — as the FALLBACK
#: beside an `OMR_FIXTURE_ROOT` lookup on the same line or the line above — plus
#: one named, deliberate pin. Anything else is the M4 defect.
PIN_ALLOWED = {"probe_structural_floor.py"}
MACHINE_PATH = re.compile(r"[\"']/Users/[^\"']+[\"']")


def probe_files():
    """⚠️ THIS USED TO BE `HERE.glob("*.py")` — NON-RECURSIVE — SO `verify/` WAS
    NEVER LINTED, and all four files in it carried the exact defects this module
    exists to catch (three hard-coded a checkout, one globbed CWD-relative).

    The lint had the shape of the bug it lints for: it looked in one place, found
    a clean set, and reported success. Fixed 2026-09-07 together with those four
    files; `test_the_lint_descends_into_subdirectories` keeps it fixed.
    """
    files = [p for p in HERE.rglob("*.py") if p.name not in SKIP]
    return sorted(f for f in files if "__pycache__" not in f.parts)


def test_there_are_probes_to_lint():
    """The lint's own version of the bug it lints for: an empty file set would
    make every test below pass vacuously."""
    assert len(probe_files()) >= 20


def test_the_lint_descends_into_subdirectories():
    """⚠️ THE BLIND SPOT, PINNED. A non-recursive glob here does not fail — it
    silently shrinks the lint's reach, which is exactly the failure mode under
    test everywhere else in this file.

    MUTATION: put `HERE.glob` back in `probe_files()` — this fails."""
    subdirs = {p.parent for p in probe_files() if p.parent != HERE}
    assert subdirs, ("probe_files() returned nothing outside the probe directory "
                     "itself — verify/ exists and holds probes, so the lint is "
                     "not reaching them")
    assert any(p.name == "verify" for p in subdirs)


@pytest.mark.parametrize("path", probe_files(), ids=lambda p: p.name)
def test_no_probe_hard_codes_a_checkout(path):
    """⚠️ THE MIRROR DEFECT, at probe level. `test_no_probe_resolves_its_inputs
    _from_the_cwd` catches only the CWD half; a probe pinned to
    `/Users/<someone>/…` does not glob nothing, it globs ANOTHER TREE — the
    stale-tree incident this audit opens with. All four `verify/` files passed
    every existing test while carrying it.

    Tolerated: an absolute used as the FALLBACK of an `OMR_FIXTURE_ROOT` lookup,
    and `probe_structural_floor.py`'s deliberate pin to the `reconciliation`
    worktree (whose fixtures it sha256-checks against the canonical arm).

    MUTATION: re-add `ROOT = "/Users/…"` to any verify/ file — this fails."""
    if path.name in PIN_ALLOWED:
        pytest.skip("named, deliberate pin — see the file's own docstring")
    lines = path.read_text().split("\n")
    for i, line in enumerate(lines):
        if line.lstrip().startswith("#") or not MACHINE_PATH.search(line):
            continue
        # ⚠️ The override may live INSIDE a helper rather than on this line:
        # `probe_sauvola_dpi_scale.py` passes its default to
        # `_fixtureroot.fixture_root()`, which reads the env itself. A
        # line-local test called that a defect. What is actually forbidden is a
        # file with NO route to an override at all, so ask the file.
        whole = path.read_text()
        if ("OMR_FIXTURE_ROOT" in whole
                or "fixture_root(" in whole or "env_path(" in whole):
            continue
        assert False, (
            f"{path.name}:{i + 1} hard-codes a checkout with no env override — "
            f"it will silently read another tree.\n     {line.strip()[:100]}")


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
