"""Run the bracket-reader tests with each mechanism disabled in turn.

A green suite proves nothing on its own — this shows every test fails when the
thing it is about is removed, which is the only way to know it exercises the
mechanism.  Restores the file afterwards and re-runs to confirm green.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
MOD = ROOT / "tools/omr/bracket_reader.py"
TESTS = "tools/omr/tests/test_bracket_reader.py"

ARMS = {
    "partial reading disabled (always abstain)": (
        '    cands = [lv for lv in levels if lv["n_partial"] >= 2]',
        "    cands = []"),
    "_overlap switched to IoU (the refused variant)": (
        "    shorter = min(a[1] - a[0], b[1] - b[0]) + 1",
        "    shorter = max(a[1], b[1]) - min(a[0], b[0]) + 1"),
    "run-level gap filter removed (artefact absorbed into the barline)": (
        "    if require_gap_crossing:\n        runs = [[r for r in rs",
        "    if False:\n        runs = [[r for r in rs"),
    "gap-crossing filter removed (trap 1 re-opened)": (
        "        if require_gap_crossing and not any(",
        "        if False and not any("),
    "shape gate widened to admit blobs": (
        "MAX_RULE_THICKNESS_SPACINGS = 1.75",
        "MAX_RULE_THICKNESS_SPACINGS = 99.0"),
    "a level holding a spanning rule disqualified (refused variant)": (
        '    cands = [lv for lv in levels if lv["n_partial"] >= 2]',
        '    cands = [lv for lv in levels if lv["n_partial"] >= 2'
        ' and lv["n_spanning"] == 0]'),
    "level tolerance widened back to 1.5 spacings": (
        "LEVEL_TOL_SPACINGS = 0.75",
        "LEVEL_TOL_SPACINGS = 1.5"),
}


def run() -> str:
    r = subprocess.run([sys.executable, "-m", "pytest", TESTS, "-q"],
                       capture_output=True, text=True, cwd=ROOT)
    lines = [ln for ln in r.stdout.strip().splitlines()
             if "passed" in ln or "failed" in ln or "error" in ln]
    return lines[-1] if lines else r.stdout[-200:]


def main() -> None:
    orig = MOD.read_text()
    try:
        print(f"{'baseline':<62} -> {run()}")
        for name, (a, b) in ARMS.items():
            if a not in orig:
                print(f"{name:<62} -> ANCHOR NOT FOUND")
                continue
            MOD.write_text(orig.replace(a, b))
            print(f"{name:<62} -> {run()}")
    finally:
        MOD.write_text(orig)
    print(f"{'restored':<62} -> {run()}")


if __name__ == "__main__":
    main()
