#!/usr/bin/env python3
"""Mutation battery for the two SCOPE tests added 2026-09-22.

Those tests pin a fact about the tree — that `OMR_ROSTER_LABELS` gates the
legacy reader and NOTHING else, and that the staged identity decision calls
the rule ungated. A test that reads the tree is exactly the kind that passes
for the wrong reason, so each arm breaks the fact and requires the test to go
RED.

⚠️⚠️ **THE ARMS RUN ON AN ISOLATED COPY OF THE TREE, NOT ON THIS WORKTREE.**
Two of the four files an arm must touch (`contextual.py`,
`staged/adjudicators/identity.py`) belong to other lanes, and sibling sessions
run multi-hour gathers that import the whole tree. A battery that mutated them
in place would hand a sibling a corrupted module and the failure would be
attributed to their change. So `tools/`, `data/score-library/` and
`pytest.ini` are copied into a scratch root, every arm mutates THERE, and this
worktree is never written to at all.

Three hazards this repo has paid for, all handled:

* **`PYTHONDONTWRITEBYTECODE=1` in every arm's environment.** `shutil.copy2`
  preserves mtime, so a `.pyc` written during one arm still satisfies Python's
  `(mtime, size)` validity check during the next — the arm then imports the
  UNMUTATED code and reports NOT RED. That voided two published batteries.
* **pytest's elapsed time is stripped from the judge.** The summary line ends
  `" in 0.57s"` and differs between two runs of an unmutated tree, so a
  verbatim comparison scores every arm RED for free. That voided two more.
* **The mutation is verified BY HASH.** An anchor that matched and a write
  that succeeded are not evidence that anything moved.

    python3 benchmarks/omr-roster-truncation-reprice-2026-09/mutate.py
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
TESTS = "tools/omr/tests/test_work_roster.py"

#: (name, file, anchor, replacement, the test that MUST go red)
ARMS = [
    ("legacy_gate_removed", "tools/omr/contextual.py",
     "if not work_roster.enabled() or not labels:",
     "if not labels:",
     "test_the_flag_governs_the_legacy_path_only"),
    ("second_caller_appears", "tools/omr/roster.py",
     "def enabled() -> bool:",
     "def _unused_scope_probe():\n"
     "    from . import work_roster\n"
     "    return work_roster.enabled()\n\n\n"
     "def enabled() -> bool:",
     "test_the_flag_governs_the_legacy_path_only"),
    ("staged_gains_a_flag_gate", "tools/omr/staged/adjudicators/identity.py",
     "    decided = WR.decide(text, roster, hit=match)",
     "    if not WR.enabled():\n"
     "        roster = None\n"
     "    decided = WR.decide(text, roster, hit=match)",
     "test_the_staged_identity_decision_is_ungated"),
    ("staged_stops_consuming_the_rule",
     "tools/omr/staged/adjudicators/identity.py",
     "    decided = WR.decide(text, roster, hit=match)",
     "    decided = WR.Decision('unchanged', match)",
     "test_the_staged_identity_decision_is_ungated"),
]

_ELAPSED = re.compile(r" in \d+\.\d+s")


def judge(out: str) -> str:
    """pytest's verdict with its own clock removed — see the module docstring."""
    tail = [ln for ln in out.splitlines()
            if ("passed" in ln or "failed" in ln or "error" in ln)]
    return _ELAPSED.sub("", "\n".join(tail[-3:]))


def run(root: Path) -> tuple[int, str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(root)
    env.pop("OMR_ROSTER_LABELS", None)
    p = subprocess.run([sys.executable, "-m", "pytest", TESTS, "-q"],
                       cwd=root, env=env, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def digest(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    scratch = Path(tempfile.mkdtemp(prefix="roster-battery-"))
    root = scratch / "tree"
    print(f"isolated copy -> {root}")
    (root).mkdir(parents=True)
    shutil.copytree(ROOT / "tools", root / "tools")
    (root / "data").mkdir()
    shutil.copytree(ROOT / "data" / "score-library",
                    root / "data" / "score-library")
    shutil.copy2(ROOT / "pytest.ini", root / "pytest.ini")

    # A sentinel, in case this process is killed mid-arm. The scratch root is
    # disposable, so an interrupted battery cannot leave a mutant anywhere that
    # matters -- but the file names what happened if anyone finds the dir.
    sentinel = scratch / "IN_FLIGHT"
    sentinel.write_text("a battery was interrupted; this tree is disposable\n")

    snapshot = {a[1]: (root / a[1]).read_bytes() for a in ARMS}
    hashes = {f: hashlib.md5(b).hexdigest() for f, b in snapshot.items()}

    code, out = run(root)
    base = judge(out)
    print(f"\nPOSITIVE CONTROL (unmutated copy): rc={code}  {base.strip()}")
    if code != 0:
        print("the copy does not pass clean -- the battery would be meaningless")
        return 2

    results = []
    for name, rel, anchor, repl, want_red in ARMS:
        path = root / rel
        src = path.read_text("utf8")
        n = src.count(anchor)
        if n != 1:
            results.append((name, f"BAD ANCHOR (matches {n}x)"))
            print(f"  {name:32} BAD ANCHOR: {n} matches")
            continue
        path.write_text(src.replace(anchor, repl), "utf8")
        if digest(path) == hashes[rel]:
            results.append((name, "WRITE DID NOT MOVE THE FILE"))
            print(f"  {name:32} NO-OP WRITE")
            continue
        code, out = run(root)
        red = (code != 0) and (want_red in out or "failed" in judge(out))
        named = want_red in out
        results.append((name, "RED" if red else "SURVIVED"))
        print(f"  {name:32} {'RED  ' if red else 'SURVIVED'} "
              f"(rc={code}, names its test={named})  {judge(out).strip()[:60]}")
        path.write_bytes(snapshot[rel])
        assert digest(path) == hashes[rel], f"restore failed for {rel}"

    code, out = run(root)
    print(f"\nrestored: rc={code}  {judge(out).strip()}")
    assert judge(out) == base, "the restored copy does not match the baseline"

    red = sum(1 for _, r in results if r == "RED")
    print(f"\n{red} RED / {len(ARMS)} arms, {len(ARMS)-red} survivors")
    sentinel.unlink()
    if not args.keep:
        shutil.rmtree(scratch, ignore_errors=True)
    else:
        print(f"kept {scratch}")
    return 0 if red == len(ARMS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
