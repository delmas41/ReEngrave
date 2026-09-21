"""Mutation battery over this benchmark's two probes.

⚠️ THE RULE THIS OBEYS, AND WHY IT IS STATED HERE RATHER THAN ASSUMED:
**a mutation battery must leave the tree as it FOUND it -- which is not the
same as leaving it as GIT has it, AND AN INTERRUPTED BATTERY OBEYS NEITHER.**
CLAUDE.md records both halves being paid for: a battery that restored from
HEAD annihilated the change it had just certified, and a battery killed
mid-arm left a mutation on disk that `git status` could not distinguish from
a legitimate edit.

So: a BYTE snapshot is taken before the first arm and md5-verified on
restore; an IN-FLIGHT SENTINEL is written before the first arm and deleted
only on a clean exit, and a run that finds one REFUSES to start and names
every file at risk with the hash it should have; and a DIRTY TREE is refused
without --force, because a battery over an uncommitted change restores the
change away.

An arm is RED when the mutated tool's `--check` exits non-zero. A positive
control in the same class runs FIRST: the unmutated tools must both exit 0,
or a battery of refusals can pass by refusing everything.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

_HERE = Path(__file__).resolve().parent
_SENTINEL = _HERE / ".mutation-in-flight"
_DVR = _HERE / "declared_vs_read.py"
_COV = _HERE / "coverage.py"
_ROOT = _HERE.parents[2]

#: `(file, find, replace, why this arm should go RED)`
ARMS: List[Tuple[Path, str, str, str]] = [
    (_DVR, "tree = _body_only(ast.parse(_dedent(src)))",
     "tree = ast.parse(_dedent(src))",
     "stop stripping decorators -- `wants` lives there, so every declared "
     "input reads as used and the unreached control must fire"),
    (_DVR, "if not adjudicate.REGISTRY:", "if False:",
     "accept an empty registry -- the decorator-registration trap"),
    (_DVR, 'if node.value.id == "Q"', 'if node.value.id == "QQ"',
     "find no quantities at all -- the 'scan matches nothing' control"),
    (_DVR, "if not any_unreached:", "if False:",
     "delete the unreached positive control"),
    (_DVR, "if not any_reads:", "if False:",
     "delete the reads-something positive control"),
    (_COV, "if by_cat != PUBLISHED:", "if False:",
     "accept a parse that disagrees with the registry's own Counts table"),
    (_COV, 'line.startswith("### ") and cat', 'line.startswith("#### ") and cat',
     "parse no entries -- the denominator collapses to zero"),
    (_COV, "if not claimed:", "if False:",
     "accept a join that claims nothing (every convention reads as uncovered)"),
    (_COV, "if unknown_ids:\n            print(f\"REFUSED: the join names ids",
     "if False:\n            print(f\"REFUSED: the join names ids",
     "accept a join naming conventions the registry does not hold"),
    (_COV, "if not (derived == len(ids_join) == len(ids_verd)):",
     "if False:",
     "accept a reading that has drifted from the statements the tree declares"),
    (_COV, "if ids_join != ids_verd:", "if False:",
     "accept join.json and verdicts.json disagreeing about which statements exist"),
]


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def _check(mod: str) -> int:
    return subprocess.run(
        [sys.executable, "-m",
         f"benchmarks.omr-convention-coverage-2026-09.probe.{mod}", "--check"],
        cwd=_ROOT, capture_output=True, text=True).returncode


def _both_green() -> bool:
    return _check("declared_vs_read") == 0 and _check("coverage") == 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true",
                    help="run over a dirty tree (restores the tree as FOUND, "
                         "not as git has it -- but do not rely on it)")
    args = ap.parse_args()

    if _SENTINEL.exists():
        print("REFUSED: an in-flight sentinel exists, so a previous battery "
              "was interrupted and a mutation may still be on disk. Files at "
              "risk and the hash each should have:\n"
              + _SENTINEL.read_text(), file=sys.stderr)
        return 2

    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=_ROOT,
                           capture_output=True, text=True).stdout.strip()
    if dirty and not args.force:
        print(f"REFUSED: the tree is dirty and a battery restores from its "
              f"own snapshot, which would take an uncommitted change with "
              f"it.\n{dirty}", file=sys.stderr)
        return 2

    snapshot = {p: p.read_bytes() for p in (_DVR, _COV)}
    _SENTINEL.write_text("\n".join(f"{p}  {_md5(p)}" for p in snapshot))

    try:
        print("POSITIVE CONTROL (unmutated, both tools must pass): ", end="")
        if not _both_green():
            print("FAILED -- the battery is measuring a broken baseline.")
            return 2
        print("green\n")

        survivors = []
        for i, (path, find, repl, why) in enumerate(ARMS, 1):
            src = snapshot[path].decode()
            if find not in src:
                print(f"  arm {i:2d}  BAD ANCHOR -- {find[:50]!r} not in "
                      f"{path.name}")
                survivors.append((i, why, "BAD ANCHOR"))
                continue
            if src.count(find) != 1:
                print(f"  arm {i:2d}  AMBIGUOUS ANCHOR ({src.count(find)}x) "
                      f"-- it would mutate the wrong line")
                survivors.append((i, why, "AMBIGUOUS ANCHOR"))
                continue
            path.write_text(src.replace(find, repl, 1))
            mod = "declared_vs_read" if path == _DVR else "coverage"
            rc = _check(mod)
            path.write_bytes(snapshot[path])
            state = "RED" if rc != 0 else "SURVIVED"
            print(f"  arm {i:2d}  {state:8s}  {why}")
            if rc == 0:
                survivors.append((i, why, "SURVIVED"))

        print()
        for path, blob in snapshot.items():
            path.write_bytes(blob)
            if _md5(path) != hashlib.md5(blob).hexdigest():
                print(f"REFUSED: restore of {path} did not verify.",
                      file=sys.stderr)
                return 2
        print(f"restore verified (md5) for {len(snapshot)} files")
        print(f"arms: {len(ARMS)}, red: {len(ARMS) - len(survivors)}, "
              f"not red: {len(survivors)}")
        for i, why, state in survivors:
            print(f"  ⚠️ arm {i} {state}: {why}")
        return 1 if survivors else 0
    finally:
        for path, blob in snapshot.items():
            path.write_bytes(blob)
        _SENTINEL.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
