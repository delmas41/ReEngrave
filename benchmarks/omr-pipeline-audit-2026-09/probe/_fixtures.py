"""Shared fixture resolution for this benchmark's probes.

⚠️ Two failure modes this exists to prevent, both found in this audit:

1. **CWD-relative globs** resolve to nothing in a git worktree (fixtures are
   gitignored build products that live in the MAIN checkout only), and a probe
   that globs nothing prints a clean all-zero table and exits 0. Agent I's
   round-2 probes had this; my round-1 probes had the mirror defect (absolute
   paths hard-coded to one machine).
2. **A silently empty arm looks like a null result.** So `fixtures()` RAISES,
   and every probe that uses it exits non-zero on an empty glob.

`OMR_FIXTURE_ROOT` overrides the checkout to read from.
"""
from __future__ import annotations

import glob as _glob
import os
import sys


def _repo_root() -> str:
    """The checkout THIS FILE lives in — never the CWD.

    `<root>/benchmarks/omr-pipeline-audit-2026-09/probe/_fixtures.py`
    """
    return os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))


def _main_checkout(root: str) -> str:
    """A git WORKTREE resolved to the checkout that holds the build products.

    ⚠️ Fixtures are gitignored, so they exist only in the main checkout. This
    used to be handled by hard-coding one machine's absolute path — which is
    the mirror of the CWD defect this module was written against: it does not
    silently glob nothing, it silently globs ANOTHER TREE, or nothing at all on
    any other machine. A worktree's `.git` is a file naming
    `<main>/.git/worktrees/<name>`, so the main checkout is derivable.
    """
    dot_git = os.path.join(root, ".git")
    if not os.path.isfile(dot_git):
        return root
    try:
        line = open(dot_git).readline().strip()
    except OSError:
        return root
    if not line.startswith("gitdir:"):
        return root
    gitdir = line.split(":", 1)[1].strip()
    marker = os.sep + ".git" + os.sep + "worktrees" + os.sep
    if marker not in gitdir:
        return root
    return os.path.dirname(gitdir.split(marker)[0] + os.sep + ".git")


#: Resolved from `__file__`, then from git — never from the CWD and never from
#: one machine's home directory. `OMR_FIXTURE_ROOT` still overrides everything.
DEFAULT_ROOT = _main_checkout(_repo_root())

SCAN = "benchmarks/omr-scan-e2e-2026-09/fixtures/*..graft09.omr.json"
ENGRAVED = "benchmarks/omr-orchestral-e2e/fixtures/*.omr.json"
CONTESTS = "benchmarks/omr-additive-vs-gated-2026-09/out/contests/*.contests.json"


def root() -> str:
    return os.environ.get("OMR_FIXTURE_ROOT", DEFAULT_ROOT)


def fixtures(pattern: str, *, expect_at_least: int = 1) -> list[str]:
    """Every file matching `pattern` under the fixture root. Never returns []."""
    hits = sorted(_glob.glob(os.path.join(root(), pattern)))
    if len(hits) < expect_at_least:
        sys.stderr.write(
            f"FATAL: {len(hits)} file(s) matched {pattern!r} under {root()!r}; "
            f"expected at least {expect_at_least}.\n"
            "Fixtures are gitignored build products and live in the MAIN "
            "checkout. Set OMR_FIXTURE_ROOT to it.\n")
        raise SystemExit(2)
    return hits


def families() -> list[tuple[str, list[str]]]:
    return [("scan", fixtures(SCAN, expect_at_least=11)),
            ("engraved", fixtures(ENGRAVED, expect_at_least=11))]


def chdir_root() -> None:
    """`cd` to the fixture root, failing loudly (exit 2) if it is not there."""
    r = root()
    if not os.path.isdir(r):
        sys.stderr.write(
            f"FATAL: fixture root {r!r} is not a directory. "
            "Set OMR_FIXTURE_ROOT to the MAIN checkout.\n")
        raise SystemExit(2)
    os.chdir(r)
