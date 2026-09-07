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

DEFAULT_ROOT = "/Users/seanjohnson/Desktop/ReEngrave"

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
