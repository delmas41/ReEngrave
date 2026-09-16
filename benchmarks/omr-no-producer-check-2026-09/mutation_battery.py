#!/usr/bin/env python3
"""Mutation battery for `tools/omr/no_producer.py` and its tests.

⚠️ **ONE RED ARM IS NOT A BATTERY.** A session in this repo ran a single
mutation, saw red, and stopped; five of six had survived behind it. Every arm
below is run, every anchor is checked to occur EXACTLY ONCE (a battery that
mutates the wrong occurrence silently tests a different function), and a
POSITIVE CONTROL runs unmutated so a suite that is red for its own reasons
cannot be read as a battery passing.

⚠️ It edits `tools/omr/no_producer.py` in place and restores it with
`git checkout`. **Do not run it beside an A/B arm that reads the working
tree** — that collision has cost this repo a session's first three-arm run.

    python3 benchmarks/omr-no-producer-check-2026-09/mutation_battery.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TARGET = REPO / "tools" / "omr" / "no_producer.py"
TESTS = "tools/omr/tests/test_no_producer.py"

ARMS = [
    ("tests count as producers by default",
     "def scan(roots: Sequence[Path], *, tests_produce: bool = False,",
     "def scan(roots: Sequence[Path], *, tests_produce: bool = True,"),

    ("the guard discriminator is dropped (report every unsupplied chain)",
     "        findings=guarded if require_guard else findings,",
     "        findings=findings,"),

    ("a single-node chain counts as a chain",
     "        if len(keys) < 2:",
     "        if len(keys) < 0:"),

    ("the fixpoint stops after one hop",
     "    changed = True\n    while changed:",
     "    changed = False\n    while changed:"),

    ("a splat no longer marks everything supplied",
     "            if not is_test:\n                splat_functions.add(s.func)",
     "            if not is_test:\n                pass"),

    ("positional arguments stop counting as producers",
     "            names = []\n            for ordered in func_orders.get(s.func, []):",
     "            names = []\n            for ordered in []:"),

    ("an external module's method counts as ours again",
     "            if isinstance(base, ast.Name) and base.id in self._foreign:",
     "            if False:"),

    ("`is None` is no longer read as an absence test",
     "        if isinstance(op, ast.Is) and isinstance(right, ast.Constant) and right.value is None:",
     "        if False:"),

    ("a guard body need not abstain",
     "            if abstains:\n                for p in named:",
     "            if True:\n                for p in named:"),

    ("decorators are visited inside the function again",
     "        for dec in node.decorator_list:\n            self.visit(dec)",
     "        pass"),

    ("keyword arguments stop being recorded at all",
     "            for kw in node.keywords:\n                if kw.arg is None:",
     "            for kw in []:\n                if kw.arg is None:"),
]


def run_tests() -> bool:
    out = subprocess.run([sys.executable, "-m", "pytest", TESTS, "-q"],
                         cwd=REPO, capture_output=True, text=True)
    return out.returncode == 0


def restore() -> None:
    subprocess.run(["git", "checkout", "--", str(TARGET.relative_to(REPO))],
                   cwd=REPO, check=True)


def main() -> int:
    original = TARGET.read_text()
    if subprocess.run(["git", "diff", "--quiet", "--", str(TARGET.relative_to(REPO))],
                      cwd=REPO).returncode != 0:
        print("REFUSING: the target is already dirty; `git checkout` would "
              "discard uncommitted work.", file=sys.stderr)
        return 2

    print("POSITIVE CONTROL (unmutated) ...", end=" ", flush=True)
    if not run_tests():
        print("RED — the suite fails on its own; every arm below is meaningless.")
        return 2
    print("green")

    survivors = []
    bad_anchors = []
    for name, needle, replacement in ARMS:
        n = original.count(needle)
        if n != 1:
            bad_anchors.append((name, n))
            print(f"  BAD ANCHOR ({n} occurrences): {name}")
            continue
        TARGET.write_text(original.replace(needle, replacement))
        try:
            green = run_tests()
        finally:
            restore()
        print(f"  {'SURVIVED' if green else 'red     '}  {name}")
        if green:
            survivors.append(name)

    print()
    print(f"{len(ARMS)} arms, {len(survivors)} survivor(s), "
          f"{len(bad_anchors)} bad anchor(s)")
    for s in survivors:
        print(f"  SURVIVOR: {s}")
    return 1 if (survivors or bad_anchors) else 0


if __name__ == "__main__":
    raise SystemExit(main())
