"""The mutation battery for the document-wide measure numbering.

    python3 benchmarks/omr-measure-numbering-2026-09/probe/mutate_numbering.py

⚠️⚠️ **NEVER RUN THIS BESIDE AN A/B ARM.** It edits `tools/omr/staged/export.py`
in place, and `numbering_arm.py` IMPORTS that module — this repo has already
lost a session's first three-arm run to exactly that collision, twice.

⚠️⚠️ **AND IT NO LONGER `git checkout`s, BECAUSE THAT DESTROYED THIS VERY
CHANGE.** The recorded recipe ends its battery with `git checkout -- <file>` as
a safety net; run against an UNCOMMITTED change that net is the hazard — the
first run of this battery went ten-for-ten red and then reverted the function
it had just certified, silently, because `checkout` restores HEAD and HEAD did
not have it. The restore is now byte-for-byte from the snapshot taken before
the first arm, and it is VERIFIED rather than assumed. **A battery must leave
the tree as it found it, which is not the same as leaving it as git has it.**

⚠️ ONE RED ARM IS NOT A BATTERY, and a battery of REFUSAL tests can pass by
refusing everything — so `everything_refuses` is here as the POSITIVE control
in the same class: it must fail the tests that assert a document IS numbered.
Without it, a rule that simply never fires would look perfect.

⚠️ EVERY ANCHOR IS ASSERTED UNIQUE before it is used. The fermata battery
silently mutated a different function because its anchor occurred twice, and
the part-join battery repeated it on two `pdf_path` forwards one space apart;
a BAD ANCHOR is reported as an error here, never as a silent pass.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / "tools/omr/staged/export.py"
TESTS = ["tools/omr/tests/test_staged_measure_numbering.py",
         "tools/omr/tests/test_staged_export.py",
         "tools/omr/tests/test_staged_part_join.py"]

ARMS = [
    ("off_by_one",
     "f'    <measure number=\"{number if base is None else base + i + 1}\">')",
     "f'    <measure number=\"{number if base is None else base + i}\">')"),
    ("offsets_ignored",
     "{number if base is None else base + i + 1}",
     "{number}"),
    ("abstention_votes_zero",
     "            if run.n_measures_decided:\n                tally[int(run.n_measures)] += 1",
     "            if True:\n                tally[int(run.n_measures)] += 1"),
    ("majority_wins",
     "        bars = next(iter(tally)) if len(tally) == 1 else None",
     "        bars = tally.most_common(1)[0][0] if tally else None"),
    ("empty_system_is_zero_bars",
     "        bars = next(iter(tally)) if len(tally) == 1 else None",
     "        bars = next(iter(tally)) if len(tally) == 1 else (0 if not tally else None)"),
    ("collision_unguarded",
     "            if n > 1:\n                collisions.append",
     "            if n > 99:\n                collisions.append"),
    ("collision_numbers_anyway",
     "        report[\"colliding_systems\"] = sorted(set(collisions))\n        return None, report",
     "        report[\"colliding_systems\"] = sorted(set(collisions))\n        return offsets, report"),
    ("offset_never_advances",
     "        offset += bars",
     "        offset += 0"),
    ("report_not_written",
     "    report[\"measure_numbering\"] = numbering",
     "    report[\"measure_numbering\"] = {\"scheme\": \"document\"}"),
    # POSITIVE CONTROL, same class: nothing is ever numbered document-wide.
    ("everything_refuses",
     "        rows.append({\n            \"system\": f\"{key[0]}/{key[1]}\",",
     "        bars = None\n        rows.append({\n            \"system\": f\"{key[0]}/{key[1]}\","),
]


def run_tests() -> bool:
    p = subprocess.run([sys.executable, "-m", "pytest", "-x", "-q", *TESTS],
                       cwd=ROOT, capture_output=True, text=True)
    return p.returncode == 0


def main() -> int:
    original = TARGET.read_text()
    print("positive control (unmutated tree): ", end="", flush=True)
    green = run_tests()
    print("GREEN" if green else "RED  <-- the suite is already failing")
    if not green:
        return 2

    survivors, bad = [], []
    try:
        for name, old, new in ARMS:
            src = TARGET.read_text()
            n = src.count(old)
            if n != 1:
                bad.append((name, n))
                print("%-28s BAD ANCHOR (%d occurrences)" % (name, n))
                continue
            TARGET.write_text(src.replace(old, new))
            ok = run_tests()
            TARGET.write_text(original)
            print("%-28s %s" % (name, "SURVIVED  <--" if ok else "red"))
            if ok:
                survivors.append(name)
    finally:
        TARGET.write_text(original)
        # ⚠️ VERIFIED, not assumed. The restore is the one step whose failure
        # is silent and expensive, so it is checked here rather than trusted.
        if TARGET.read_text() != original:
            print("RESTORE FAILED — %s does not match the pre-run snapshot"
                  % TARGET)
            return 3

    print()
    print("arms: %d   survivors: %d   bad anchors: %d"
          % (len(ARMS), len(survivors), len(bad)))
    if survivors:
        print("SURVIVORS:", ", ".join(survivors))
    return 1 if (survivors or bad) else 0


if __name__ == "__main__":
    sys.exit(main())
