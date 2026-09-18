#!/usr/bin/env python3
"""Mutation battery for the brake audit.

⚠️⚠️ THE RECORDED HAZARDS, ALL FOUR PAID FOR BY THIS REPO:

  * **Leave the tree as you FOUND it, which is not as GIT has it.** A battery
    that restores from HEAD destroys an uncommitted change under test —
    measured, on the measure-numbering session, which `git checkout`ed away
    the function it had just certified.
  * **An INTERRUPTED battery obeys neither.** A byte snapshot held in memory
    dies with the process and the mutation stays on disk, indistinguishable
    from a legitimate edit. So the snapshot is written to DISK and an
    in-flight SENTINEL is written before the first arm and removed on a clean
    exit; a run that finds one refuses to start and names each file at risk.
  * **Refuse a dirty tree** without `--force`.
  * **Expect the first run's survivors to be the battery's OWN faults** — a
    BAD ANCHOR (a string occurring twice, so the arm mutates the wrong site)
    is the commonest, and is reported as an ERROR rather than a silent pass.

Run:  python3 benchmarks/omr-brake-audit-2026-09/mutate.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
SENTINEL = pathlib.Path(__file__).resolve().parent / ".mutation-in-flight.json"

BRAKES = ROOT / "tools" / "omr" / "staged" / "brakes.py"
REACH = ROOT / "tools" / "omr" / "staged" / "reach.py"

#: (name, file, anchor, replacement, how the battery detects the wound)
#:
#: `detect` is one of:
#:   "check"  -- `brakes --check` must go NON-ZERO
#:   "tests"  -- the unit tests must go RED
#:   "reach"  -- `reach --check` must go NON-ZERO
ARMS = [
    ("positive_control_untouched", None, None, None, "green"),
    ("drop_the_inferences_import", BRAKES,
     "from . import inferences as _inferences       # POPULATES infer.RULES",
     "_inferences = None  # MUTANT",
     "tests"),
    # ⚠️ `drop_the_adjudicators_import` IS AN EQUIVALENT MUTANT AND IS HELD OUT
    # DELIBERATELY. Importing `inferences` populates `adjudicate.REGISTRY`
    # transitively (measured: 28 decisions with `adjudicators` never named),
    # so the arm can never go red. The import STAYS in `brakes.py` because it
    # declares the dependency rather than relying on another module's import
    # graph — but an arm that cannot fail trains the next reader to skim the
    # list, which is this repo's own recorded lesson from the wedge battery.
    ("readings_gap_finds_nothing", BRAKES,
     "            if reading not in spec.wants:",
     "            if False:  # MUTANT",
     "check"),
    ("vocabulary_gap_finds_nothing", BRAKES,
     "        if not missing:\n            continue",
     "        if True:  # MUTANT\n            continue",
     "check"),
    ("stale_entries_stop_being_reported", BRAKES,
     "    for pair in ACCOUNTED_READINGS:\n        if pair not in seen_readings:",
     "    for pair in ():  # MUTANT\n        if pair not in seen_readings:",
     "tests"),
    ("a_zero_control_stops_failing", BRAKES,
     "        if value == 0:\n            lines.append(f\"CONTROL AT ZERO:",
     "        if False:  # MUTANT\n            lines.append(f\"CONTROL AT ZERO:",
     "tests"),
    ("considered_compared_as_NAMES_not_IDS", BRAKES,
     "        touched = {quantity_of.get(i) for i in verdict[\"considered\"]}",
     "        touched = set(verdict[\"considered\"])  # MUTANT",
     "tests"),
    ("ancestors_are_not_reachable", BRAKES,
     "            for ancestor in Subject.from_key(key).ancestors():",
     "            for ancestor in ():  # MUTANT",
     "tests"),
    ("blind_ignores_an_empty_considered", BRAKES,
     "        if not verdict[\"considered\"]:",
     "        if False:  # MUTANT",
     "tests"),
    ("decided_verdicts_are_examined_too", BRAKES,
     "        if verdict[\"outcome\"] not in UNRESOLVED_OUTCOMES:\n            continue",
     "        if False:  # MUTANT\n            continue",
     "tests"),
    ("infer_targets_reads_an_empty_rule_set", BRAKES,
     "    return frozenset(r.target for r in infer.RULES)",
     "    return frozenset()  # MUTANT",
     "tests"),
    # ⚠️ RETARGETED after its first run SURVIVED: `reach --check` does NOT call
    # `unaccounted_modules()` — `test_staged_reach.py:61` does, and `reach.py`'s
    # own comment claiming otherwise is a false claim in prose, now corrected
    # at its site. The arm was right and its DETECTOR was wrong.
    ("unregister_from_reach", REACH,
     '    "brakes.py",\n})',
     "})",
     "reach_tests"),
]


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def dirty() -> str:
    return run(["git", "status", "--porcelain"]).stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="run against a dirty tree (you accept the risk)")
    args = ap.parse_args()

    if SENTINEL.exists():
        print("REFUSING: an interrupted battery left a sentinel.")
        print(SENTINEL.read_text())
        print("Restore each file to the hash above, then delete the sentinel.")
        return 2

    d = dirty()
    if d and not args.force:
        print("REFUSING: the tree is dirty. A battery must leave the tree as "
              "it FOUND it, and it cannot tell your edit from its own.\n")
        print(d)
        return 2

    files = sorted({a[1] for a in ARMS if a[1] is not None})
    snapshot_dir = pathlib.Path(tempfile.mkdtemp(prefix="brake-battery-"))
    before = {}
    for f in files:
        before[str(f)] = sha(f)
        shutil.copy2(f, snapshot_dir / f.name)
    SENTINEL.write_text(json.dumps(
        {"snapshot_dir": str(snapshot_dir), "sha256": before}, indent=2))

    def restore():
        for f in files:
            shutil.copy2(snapshot_dir / f.name, f)
        for f in files:
            if sha(f) != before[str(f)]:
                raise SystemExit(f"RESTORE FAILED for {f}")

    results = []
    try:
        for name, path, anchor, repl, detect in ARMS:
            if path is None:
                r = run([sys.executable, "-m", "pytest",
                         "tools/omr/tests/test_brakes.py", "-q"])
                ok = r.returncode == 0
                results.append((name, "GREEN" if ok else "RED",
                                "positive control: the suite must PASS "
                                "unmutated"))
                if not ok:
                    print(r.stdout[-2000:])
                continue

            src = path.read_text()
            n = src.count(anchor)
            if n != 1:
                results.append((name, "BAD ANCHOR",
                                f"anchor occurs {n} times in {path.name}"))
                continue
            path.write_text(src.replace(anchor, repl))
            try:
                if detect == "check":
                    r = run([sys.executable, "-m", "tools.omr.staged.brakes",
                             "--check"])
                elif detect == "reach_tests":
                    r = run([sys.executable, "-m", "pytest", "-q",
                             "tools/omr/tests/test_staged_reach.py",
                             "tools/omr/tests/test_brakes.py"])
                else:
                    r = run([sys.executable, "-m", "pytest",
                             "tools/omr/tests/test_brakes.py", "-q"])
                results.append((name, "RED" if r.returncode != 0 else "SURVIVED",
                                f"{detect} exit={r.returncode}"))
            finally:
                path.write_text(src)
                if sha(path) != before[str(path)]:
                    raise SystemExit(f"inline restore failed for {path}")
    finally:
        restore()
        SENTINEL.unlink(missing_ok=True)
        shutil.rmtree(snapshot_dir, ignore_errors=True)

    print(f"{'arm':<42} {'result':<12} note")
    print("-" * 92)
    for name, result, note in results:
        print(f"{name:<42} {result:<12} {note}")

    survivors = [r for r in results if r[1] in ("SURVIVED", "BAD ANCHOR")]
    control = [r for r in results if r[0].startswith("positive_control")]
    bad_control = [r for r in control if r[1] != "GREEN"]
    print()
    print(f"arms: {len(results)}   survivors/bad anchors: {len(survivors)}")
    if bad_control:
        print("⚠️ POSITIVE CONTROL FAILED — the battery measured its own scope")
    print("tree restored and verified; sentinel removed")
    return 1 if (survivors or bad_control) else 0


if __name__ == "__main__":
    sys.exit(main())
