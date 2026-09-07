"""Shared: where a probe's inputs live, and a refusal when they are not there.

⚠️ THE HAZARD THIS EXISTS FOR. A probe that globs a directory and finds nothing
prints a clean all-zero table and exits 0. Nothing about the output invites
suspicion — it is the cached-A/B failure shape (`scan_eval` reusing an arm and
reporting a flawless "no change") arriving in the audit's own instruments. The
verifier found it in two agents' probe sets on 2026-09-07; this is the endorsed
fix, applied here.

    OMR_FIXTURE_ROOT   overrides where gitignored build products (fixtures/,
                       cells/) are looked for. Committed artefacts are always
                       read relative to the repo the probe lives in.

`require_nonempty` turns an empty glob into a non-zero exit with the path and
the pattern named, so a wrong root fails loudly instead of scoring zero.

⚠️ **A SIBLING MODULE EXISTS AND THEY AGREE.** Another agent of this audit wrote
`probe/_fixtures.py` independently, for the same reason and honouring the same
`OMR_FIXTURE_ROOT`; its `fixtures()` resolves and globs a fixture directory,
raising on empty. This module is the narrower half — a root resolver and a
guard — used by probes that read COMMITTED artefacts rather than fixtures.
They were not merged at the end of a session because converging four working
probes onto a different API is a change with no measurement behind it. **If one
survives, it should be `_fixtures.py`**; this docstring exists so the next
reader does not have to work out whether the two disagree. They do not.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def fixture_root(default: Path) -> Path:
    env = os.environ.get("OMR_FIXTURE_ROOT")
    return Path(env) if env else default


def require_nonempty(items, what: str, where, pattern: str = ""):
    """Refuse loudly rather than reporting an all-zero table at exit 0."""
    items = list(items)
    if items:
        return items
    print(
        "REFUSING: found no %s under %s%s.\n"
        "  A probe that globs nothing prints a clean zero and exits 0 — that is\n"
        "  the failure this guard exists to prevent. Set OMR_FIXTURE_ROOT, or\n"
        "  run from a checkout that has these files." % (
            what, where, (" matching %r" % pattern) if pattern else ""),
        file=sys.stderr)
    raise SystemExit(3)
