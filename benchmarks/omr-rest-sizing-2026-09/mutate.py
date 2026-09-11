"""A MUTATION BATTERY for the rest-padding counter, with a positive control.

⚠️ ONE RED ARM IS NOT A BATTERY -- this repo has measured five of six mutants
surviving behind one that did not. Every arm below is applied to a SNAPSHOT of
the tree, the named tests are run, and the arm is required to go RED.

⚠️ AND A BATTERY OF "the counter is present" ARMS CAN PASS BY BEING PRESENT
ALWAYS, so arm P is a positive control in the same class: it asserts the
counter still COUNTS on the branch it is about, i.e. that making it always-zero
is caught too.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
TARGET = "tools/omr/staged/export.py"
TESTS = ("tools/omr/tests/test_staged_export.py", "-k",
         "PaidForPositions or MeterIsReadPerBAR or RestsReachTheFile")

LIVE = '''                counters["empty_bars_padded_without_meter"] += (
                    1 if meter is None else 0)'''

ARMS = {
    "A the pre-fix form: increment only on the bad branch, so a clean run "
    "reports NO KEY":
        '''                if meter is None:
                    counters["empty_bars_padded_without_meter"] += 1''',
    "B the counter is deleted outright":
        '''                pass''',
    "P POSITIVE CONTROL: always zero -- present, and no longer counting":
        '''                counters["empty_bars_padded_without_meter"] += 0''',
    "C the sense is inverted -- it counts the bars that HAVE a meter":
        '''                counters["empty_bars_padded_without_meter"] += (
                    1 if meter is not None else 0)''',
}


def run(tree: pathlib.Path) -> bool:
    """True when the suite is GREEN in `tree`."""
    p = subprocess.run([sys.executable, "-m", "pytest", *TESTS, "-q"],
                       cwd=tree, capture_output=True, text=True)
    return p.returncode == 0


def main() -> int:
    src = (ROOT / TARGET).read_text()
    if LIVE not in src:
        print("BAD ANCHOR: the live form is not in %s -- the battery would "
              "mutate nothing and report a pass." % TARGET)
        return 2

    with tempfile.TemporaryDirectory() as tmp:
        tree = pathlib.Path(tmp) / "tree"
        shutil.copytree(ROOT, tree, symlinks=True,
                        ignore=shutil.ignore_patterns(
                            ".git", "library", "benchmarks", "*.pyc",
                            "__pycache__", ".venv*", "out"))
        if not run(tree):
            print("THE UNMUTATED SNAPSHOT IS ALREADY RED -- the battery "
                  "cannot say anything.")
            return 2
        print("positive control: the unmutated snapshot is GREEN\n")

        failures = 0
        for name, body in ARMS.items():
            (tree / TARGET).write_text(src.replace(LIVE, body))
            green = run(tree)
            print("%-6s %s" % ("SURVIVED" if green else "red", name))
            if green:
                failures += 1
            (tree / TARGET).write_text(src)
        print("\n%d of %d arms survived" % (failures, len(ARMS)))
        return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
