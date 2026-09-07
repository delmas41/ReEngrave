#!/usr/bin/env python3
"""Where a probe reads from, and what it does when there is nothing there.

⚠️ **THIS MODULE EXISTS BECAUSE THE AUDIT'S OWN INSTRUMENTS HAD THE FAULT THE
AUDIT WAS CONVENED TO FIND.** `VERIFICATION.md` §D16 demonstrates it: seven
round-2 probes glob CWD-relative, so run from anywhere but the main checkout
they print

    === scan: 0 pages, 0 measures
       uncorroborated meter changes REVERTED: 0
       measures carrying rhythm_sum_warning: 0 (0.0%)  severity {}

and **exit 0**. That is not a null result, it is a believable wrong answer:
"the guard never fired, and no measure anywhere fails its bar-sum". Six
round-1 probes have the mirror defect — a hard-coded
`/Users/seanjohnson/Desktop/ReEngrave` committed *into the audit tree*, so
they silently measure a DIFFERENT tree the moment the trees diverge, which is
the stale-tree incident the charter opens with.

⚠️ **THE OBVIOUS FIX — "make the paths relative" — IS WRONG, AND WAS WITHDRAWN
AS GLIB IN VERIFICATION.md.** `benchmarks/*/fixtures/` is gitignored. It
exists only in the main checkout. A relative path genuinely cannot work from a
worktree. So the fix is not one root, it is TWO, distinguished by whether the
artefact is committed:

    repo_root()      the tree the probe LIVES IN (Path(__file__).parents[3]).
                     Committed artefacts — out/contests/, results*.json,
                     verdicts/, current-accuracy.json. Reading these from
                     anywhere else is the M4 defect: measuring another tree.

    fixture_root()   where GITIGNORED build products live — fixtures/,
                     library/. Overridable with OMR_FIXTURE_ROOT; defaults to
                     the main checkout, DERIVED from git rather than spelled
                     out, so it survives a clone.

...and the second half, which is the part that actually closes the bug:

    must_glob()      a glob that matches nothing EXITS 2 and says which
                     absolute pattern it tried and how the root was chosen.

The path was never really the bug. The bug was that **emptiness and a negative
result were indistinguishable**, which is the same "an abstention and a failure
look alike" fault Agent II diagnoses for `_assign` in §R1.4 — here installed in
the measuring instrument instead of the pipeline.

Every message this module writes goes to **stderr**, on purpose: the committed
`out/*.txt` are stdout captures, and a hygiene fix that changes a measured
number is a bug.

Usage from a probe (which is run as a script from an arbitrary cwd, so it must
put its own directory on the path first):

    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from fixture_root import fixture_glob, repo_root, must_glob

    files = fixture_glob("benchmarks/omr-scan-e2e-2026-09/fixtures/*..graft09.omr.json")
"""
from __future__ import annotations

import glob as _glob
import os
import subprocess
import sys
from pathlib import Path

#: The machine this project is developed on. Last resort only — `_derive()`
#: normally finds the same path from git, which also works on a clone.
BUILTIN_DEFAULT = "/Users/seanjohnson/Desktop/ReEngrave"

#: exit status for "I looked and there was nothing there". Distinct from 1,
#: which several probes already use for their own analysis-level refusals.
EXIT_NO_FIXTURES = 2

_resolved: tuple[Path, str] | None = None
_announced = False


def repo_root() -> Path:
    """The checkout this probe FILE lives in.

    Use for committed artefacts. A probe that reads a committed artefact from
    anywhere else is measuring a tree it was not shipped with — M4.
    """
    return Path(__file__).resolve().parents[3]


def audit_dir() -> Path:
    """`benchmarks/omr-pipeline-audit-2026-09/` in this probe's own tree."""
    return Path(__file__).resolve().parents[1]


def _derive() -> tuple[Path, str]:
    """(root, how_it_was_chosen). Never raises; validity is checked by callers."""
    env = os.environ.get("OMR_FIXTURE_ROOT")
    if env:
        return Path(env).expanduser().resolve(), "OMR_FIXTURE_ROOT"

    # A linked worktree's --git-common-dir is the MAIN checkout's .git, so this
    # finds the main checkout from inside a worktree — the same move
    # `library_root()` makes for the score library. Derived beats spelled out:
    # it survives a clone, and it cannot drift from the tree it names.
    try:
        out = subprocess.run(
            ["git", "-C", str(Path(__file__).resolve().parent),
             "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            common = Path(out.stdout.strip())
            if common.name == ".git" and common.parent.is_dir():
                return common.parent.resolve(), "git --git-common-dir"
    except Exception:
        pass

    return Path(BUILTIN_DEFAULT).resolve(), "built-in default"


def fixture_root(announce: bool = True) -> Path:
    """Where gitignored build products live. Resolved once per process.

    ⚠️ Announces the root and HOW IT WAS CHOSEN on stderr the first time it is
    called. The whole family of bugs this module closes is "the probe read a
    tree nobody named", so the tree is never implicit again. Set
    `OMR_FIXTURE_ROOT_QUIET=1` to suppress (scripts that parse their own
    stderr; nothing here does).
    """
    global _resolved, _announced
    if _resolved is None:
        _resolved = _derive()
        root, how = _resolved
        if how == "OMR_FIXTURE_ROOT" and not root.is_dir():
            print(
                f"\nFIXTURE ROOT DOES NOT EXIST\n"
                f"  OMR_FIXTURE_ROOT = {root}\n"
                f"  It is set, so it is not guessed — but there is no directory there.\n",
                file=sys.stderr,
            )
            raise SystemExit(EXIT_NO_FIXTURES)
    root, how = _resolved
    if announce and not _announced and not os.environ.get("OMR_FIXTURE_ROOT_QUIET"):
        _announced = True
        same = " (same tree as this probe)" if root == repo_root() else \
               " (⚠️ NOT the tree this probe lives in)"
        print(f"[fixture_root] {root}  via {how}{same}", file=sys.stderr)
    return root


def _die_empty(pattern: str, what: str, root: Path, how: str) -> None:
    hint = (
        "  Set OMR_FIXTURE_ROOT to the checkout that HAS the fixtures:\n"
        f"    OMR_FIXTURE_ROOT={BUILTIN_DEFAULT} python3 {Path(sys.argv[0]).name}\n"
        if how != "OMR_FIXTURE_ROOT" else
        "  OMR_FIXTURE_ROOT is set and points somewhere real, but holds no such files.\n"
    )
    print(
        f"\nNO {what.upper()} FOUND — refusing to report a number computed over nothing.\n"
        f"  pattern : {pattern}\n"
        f"  root    : {root}   (chosen via {how})\n"
        f"  ⚠️ This is the failure this guard exists for: without it the probe\n"
        f"     would print a clean all-zero table and exit 0, and an empty glob\n"
        f"     would be indistinguishable from a genuine negative result.\n"
        f"{hint}",
        file=sys.stderr,
    )
    raise SystemExit(EXIT_NO_FIXTURES)


def must_glob(pattern: str, what: str = "files", root: Path | None = None) -> list[str]:
    """Sorted matches for a root-relative `pattern`. **Exits 2 if empty.**"""
    if root is None:
        root, how = repo_root(), "probe's own tree"
    else:
        how = _resolved[1] if _resolved else "explicit"
    full = str(root / pattern)
    # ⚠️ `recursive=True` is required for `**` to cross directories, and its
    # absence is NOT loud: `benchmarks/**/*.json` silently matches one level
    # only, where `Path.rglob` matches all of them. Caught converting
    # probe_measurement_hygiene's rglob — it reported 48 artefacts instead of
    # 69 and looked entirely plausible. No-op for patterns without `**`.
    hits = sorted(_glob.glob(full, recursive=True))
    if not hits:
        _die_empty(full, what, root, how)
    return hits


def fixture_glob(pattern: str, what: str = "fixtures") -> list[str]:
    """`must_glob` against `fixture_root()` — for GITIGNORED build products."""
    root = fixture_root()
    return must_glob(pattern, what=what, root=root)


def repo_glob(pattern: str, what: str = "committed artefacts") -> list[str]:
    """`must_glob` against `repo_root()` — for COMMITTED artefacts."""
    return must_glob(pattern, what=what, root=repo_root())


def must_exist(path: Path | str, what: str = "artefact") -> Path:
    """Return `path`, or exit 2 naming it. For a single required file."""
    p = Path(path)
    if not p.exists():
        print(
            f"\nMISSING {what.upper()}\n  {p}\n"
            f"  Refusing to continue — a probe that carries on without its input\n"
            f"  reports the absence as a measurement.\n",
            file=sys.stderr,
        )
        raise SystemExit(EXIT_NO_FIXTURES)
    return p


def env_path(var: str, default: str, what: str = "directory") -> Path:
    """A single overridable path constant. Default is used verbatim when unset.

    For the two probes pinned to a specific tree on purpose
    (`probe_structural_floor` to the `reconciliation` worktree, whose fixtures
    it sha256-checks; `probe_beam_bar_positions` to `library/`). Their defaults
    are unchanged, so behaviour with no env set is identical — the only new
    property is that the pin is nameable and its absence is loud.
    """
    return Path(os.environ.get(var, default)).expanduser()


def add_repo_to_syspath(root: Path | None = None) -> Path:
    """Put a checkout on `sys.path` so `import tools.omr...` resolves."""
    r = root or repo_root()
    s = str(r)
    if s not in sys.path:
        sys.path.insert(0, s)
    return r


def _self_test() -> int:
    """`python3 fixture_root.py` — show what this tree resolves to."""
    root = fixture_root()
    print(f"repo_root()    = {repo_root()}")
    print(f"fixture_root() = {root}   via {_resolved[1]}")
    print(f"audit_dir()    = {audit_dir()}")
    probe = "benchmarks/omr-scan-e2e-2026-09/fixtures/*..graft09.omr.json"
    n = len(_glob.glob(str(root / probe)))
    print(f"scan fixtures visible: {n}   ({probe})")
    return 0 if n else EXIT_NO_FIXTURES


if __name__ == "__main__":
    raise SystemExit(_self_test())
