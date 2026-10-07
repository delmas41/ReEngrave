"""Verify the anti-drift tests FAIL when each call site is removed.

An anti-drift test that passes vacuously is worse than none, and this repo has
already shipped one (`benchmarks/omr-margin-labels-blob-2026-09`: a regression
test that asserted on label LENGTH and passed either way). So each wiring test
is run against a tree with its own call site mutated out, and must go red.

Run from the repo root. Restores `contextual.py` unconditionally.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

P = pathlib.Path("tools/omr/contextual.py")

MUTATIONS = {
    "no find_contradictions call": (
        "_contradictions = find_contradictions(\n        staff_keys=_keys",
        "_contradictions = []\n    _unused = dict(\n        staff_keys=_keys"),
    "no summary assignment": (
        'summary["label_contradiction"] = summarise_contradictions(',
        "x_summary = summarise_contradictions("),
    "no per-staff write": (
        'staff["label_contradiction"] = {',
        'staff["x_label_contradiction"] = {'),
    "no warning": (
        "CONTRADICT their own margin ",
        "disagree with their own margin "),
    "gated behind a flag": (
        "    _contradictions = find_contradictions(",
        '    _contradictions = []\n    if os.environ.get("X"):\n'
        "        _contradictions = find_contradictions("),
}


def run() -> str:
    r = subprocess.run(
        ["python3", "-m", "pytest",
         "tools/omr/tests/test_label_contradiction.py", "-q"],
        capture_output=True, text=True)
    return r.stdout.strip().splitlines()[-1]


def main() -> int:
    orig = P.read_text()
    bad = []
    try:
        for name, (a, b) in MUTATIONS.items():
            mut = orig.replace(a, b)
            if mut == orig:
                bad.append(f"{name}: the anchor text is gone, cannot mutate")
                continue
            P.write_text(mut)
            line = run()
            print(f"{name:32} -> {line}")
            if "failed" not in line:
                bad.append(f"{name}: the suite stayed GREEN")
    finally:
        P.write_text(orig)
    print(f"{'restored':32} -> {run()}")
    for b in bad:
        print("VACUOUS: " + b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
