"""Fixture resolution for the shared-delta probes. FAILS LOUD on an empty set.

Same contract as `benchmarks/omr-pipeline-audit-2026-09/probe/_fixtures.py`:
the reference encodings are gitignored build products that live in the MAIN
checkout only, so a worktree-relative glob resolves to nothing and a probe
that globs nothing prints a clean all-zero table at exit 0. This module
RAISES instead, and every caller exits non-zero.

`OMR_LIBRARY_ROOT` overrides the checkout to read from.
"""
from __future__ import annotations

import glob as _glob
import os
import sys


def _repo_root() -> str:
    """The checkout THIS FILE lives in — never the CWD."""
    return os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))


def _main_checkout(root: str) -> str:
    """A git WORKTREE resolved to the checkout that holds `library/`."""
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


DEFAULT_ROOT = _main_checkout(_repo_root())

REFERENCE = "library/reference/*/*/*"


def root() -> str:
    return os.environ.get("OMR_LIBRARY_ROOT", DEFAULT_ROOT)


def encodings(*, expect_at_least: int = 1000) -> list[str]:
    """Every reference MusicXML / MXL. Never returns [] — raises instead."""
    hits = sorted(
        p for p in _glob.glob(os.path.join(root(), REFERENCE))
        if p.lower().endswith((".mxl", ".musicxml", ".xml"))
    )
    if len(hits) < expect_at_least:
        sys.stderr.write(
            f"FATAL: {len(hits)} reference encodings under {root()!r} "
            f"(expected at least {expect_at_least}).\n"
            f"       Pattern: {REFERENCE}\n"
            f"       A probe that measures nothing prints a clean table of "
            f"zeros. Refusing.\n"
        )
        raise SystemExit(2)
    return hits
