"""THE MUTATION BATTERY for `notehead_is_a_whole_rest`.

⚠️ ONE RED ARM IS NOT A BATTERY. Running a single mutation, seeing red and
stopping is the reassurance that hides the rest -- measured elsewhere in this
repo at five of six surviving behind one that did not.

⚠️ A BATTERY OF REFUSAL TESTS CAN PASS BY REFUSING EVERYTHING, so `refuse
everything` is an arm here: it must fail exactly the ACCEPT tests. A suite that
stayed green under it would be certifying a rule that never fires.

⚠️ IT `git checkout`s THE FILES IT MUTATES, so it must not run beside an A/B
arm that reads the working tree. That collision has already cost a session its
first three-arm run.

⚠️ AN ANCHOR THAT OCCURS TWICE MUTATES THE WRONG FUNCTION. Every anchor below
is asserted UNIQUE in its file before anything is written, and a non-unique or
missing anchor is reported as an ERROR rather than passing as a silent green --
which is how a sibling battery silently mutated `arc_owner` instead of the
function it named.

    python3 benchmarks/omr-note-where-silence-2026-09/mutate.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADJ = ROOT / "tools/omr/staged/adjudicators/rhythm.py"
EXP = ROOT / "tools/omr/staged/export.py"
TESTS = ["tools/omr/tests/test_staged_whole_rest_ink.py",
         "tools/omr/tests/test_staged_export.py",
         "tools/omr/tests/test_staged_voices.py"]

ARMS = [
    ("the SHAPE witness is gone", ADJ,
     "    if not _rest_shaped(h, aspect):",
     "    if False:"),
    ("the POSITION witness is gone", ADJ,
     "    at_the_slot = abs(step - WHOLE_REST_STEP) <= WHOLE_REST_STEP_TOLERANCE",
     "    at_the_slot = True"),
    ("the upper aspect bound is gone", ADJ,
     "WHOLE_REST_INK_MAX_ASPECT = 3.09",
     "WHOLE_REST_INK_MAX_ASPECT = 99.0"),
    ("the height cut is gone", ADJ,
     "WHOLE_REST_INK_MAX_HEIGHT_SPACES = 0.84",
     "WHOLE_REST_INK_MAX_HEIGHT_SPACES = 99.0"),
    ("it reads the CANONICAL box, not the page box", ADJ,
     '        page_box = (r.detail or {}).get("bbox_page_px") or page_box',
     "        page_box = r.value[1:5] or page_box"),
    ("the neighbour reaches the whole staff", ADJ,
     "WHOLE_REST_NEIGHBOUR_BARS = 2",
     "WHOLE_REST_NEIGHBOUR_BARS = 999"),
    ("the neighbour may sit anywhere on the staff", ADJ,
     "WHOLE_REST_NEIGHBOUR_STEPS = 1.5",
     "WHOLE_REST_NEIGHBOUR_STEPS = 99.0"),
    ("it refuses EVERYTHING (the positive control)", ADJ,
     "    if at_the_slot or neighbour is not None:",
     "    if False:"),
    ("the exporter ignores the verdict", EXP,
     "        if not is_rest and rec.value(Q.NOTEHEAD_IS_A_WHOLE_REST, sub) is True:",
     "        if False:"),
    ("the exporter refuses but does not COUNT it", EXP,
     '            dropped["ink_is_a_whole_rest"] += 1\n            continue',
     "            continue"),
    ("the exporter refuses a FALSE verdict too", EXP,
     "        if not is_rest and rec.value(Q.NOTEHEAD_IS_A_WHOLE_REST, sub) is True:",
     "        if not is_rest and rec.obs(Q.NOTEHEAD_CLASS, sub) and "
     "rec.verdict(Q.NOTEHEAD_IS_A_WHOLE_REST, sub) is not None:"),
]


def run_tests():
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", *TESTS],
                       cwd=ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout or "").strip().splitlines()[-1:]


def main():
    dirty = subprocess.run(["git", "status", "--porcelain", "--",
                            str(ADJ), str(EXP)],
                           cwd=ROOT, capture_output=True, text=True).stdout
    print("⚠️ this battery `git checkout`s the files it mutates. "
          "Uncommitted work in them will be LOST." if dirty.strip()
          else "working tree clean for the mutated files")

    rc, tail = run_tests()
    print(f"\nBASELINE (unmutated): rc={rc}  {tail}")
    if rc != 0:
        print("THE SUITE IS ALREADY RED — a battery run now measures nothing.")
        return 2

    results = []
    for name, path, old, new in ARMS:
        src = path.read_text()
        n = src.count(old)
        if n != 1:
            results.append((name, "BAD ANCHOR", f"occurs {n} times"))
            print(f"\n=== {name}\n  BAD ANCHOR: occurs {n} times in "
                  f"{path.name} — this arm mutated NOTHING (or the wrong "
                  f"thing) and is reported as an error, not a pass.")
            continue
        path.write_text(src.replace(old, new))
        try:
            rc, tail = run_tests()
        finally:
            subprocess.run(["git", "checkout", "--", str(path)], cwd=ROOT,
                           check=True)
        state = "RED" if rc != 0 else "SURVIVED"
        results.append((name, state, tail[0] if tail else ""))
        print(f"\n=== {name}\n  {state}  {tail}")

    print("\n" + "=" * 70)
    bad = [r for r in results if r[1] != "RED"]
    for name, state, note in results:
        print(f"  {state:<11} {name}   {note}")
    print(f"\n{len(results) - len(bad)} of {len(results)} arms RED")
    if bad:
        print("⚠️ A SURVIVOR IS EITHER A TEST GAP OR AN EQUIVALENT MUTANT, "
              "and the two need different repairs. Name which before moving on.")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
