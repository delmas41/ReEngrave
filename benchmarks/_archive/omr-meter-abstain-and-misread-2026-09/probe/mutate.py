#!/usr/bin/env python3
"""Mutation battery for find_fixture.py.

⚠️ A BYTE SNAPSHOT, AN IN-FLIGHT SENTINEL, AND A VERIFIED RESTORE. CLAUDE.md:
"A mutation battery must leave the tree as it FOUND it -- which is not the same
as leaving it as GIT has it, AND AN INTERRUPTED BATTERY OBEYS NEITHER." The
snapshot is written to DISK before the first arm, so it survives this process
being killed; a run that finds a stale sentinel refuses to start and names the
file with the hash it should have.
"""
import hashlib
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
TARGET = HERE / "find_fixture.py"
SNAP = HERE / ".mutate-snapshot"
SENTINEL = HERE / ".mutate-inflight"

#: (name, old, new, expectation) -- expectation is checked against stdout.
ARMS = [
    ("two_format_detection_removed",
     'quantified = any("quantity" in v for v in blob)',
     'quantified = True',
     "p012 must leave every bucket"),
    ("system_truth_exception_removed",
     'per_system = SYSTEM_TRUTH.get((fixture, r["subject"]))',
     'per_system = None',
     "brahms1eng must falsely qualify"),
    # ⚠️ `cut_common_is_two_quarters` WAS HERE AND IS DELETED, NOT FIXED.
    # It mutated `C|` -> 2.0 expecting brahms4eng to falsely misread; but that
    # fixture's OPENING truth is `C` and only openings are scored, so the arm
    # reached nothing and could never go red. Replaced by one that DOES reach
    # the length comparison this probe's whole finding rests on.
    ("six_eight_is_four_quarters",
     'return float(n) * 4.0 / float(d)',
     'return 4.0',
     "p0p3's C must stop being a misread"),
    # ⚠️ THIS ARM WAS A NO-OP AND THE REASON IS IN CLAUDE.md. It read
    # `OPENING_TRUTH = {} or {...}` -- and `{}` is FALSY, so `or` handed back
    # the full dict and nothing was mutated. Same shape as `_carry_meter`'s
    # `{}`-is-falsy-but-not-None hazard, in the instrument this time.
    ("truth_table_emptied",
     'scored = [f for f in fixtures if f in OPENING_TRUTH]',
     'scored = []',
     "must exit 3 DEAD"),
    ("only_the_boundary_dir",
     'OUT_DIRS = sorted({p.parent for p in ROOT.glob("benchmarks/*/out/*.meter.json")})',
     'OUT_DIRS = [ROOT / "benchmarks/omr-staged-meter-boundary-2026-09/out"]',
     "reach must fall from 105 records"),
]


def run():
    r = subprocess.run([sys.executable, str(TARGET)], capture_output=True, text=True)
    return r.returncode, r.stdout


def answer(out):
    """ALL FOUR BUCKETS, not just the headline.

    ⚠️ THE BATTERY'S OWN FIRST FAULT. This read only the `ABSTAINS *and*
    MISREADS` line, so `two_format_detection_removed` -- which drops Litolff
    `p012` out of every bucket -- read as a SURVIVOR: p012 is an
    abstains-only row, and the headline cannot see it. An arm that changes
    real behaviour looked like a test gap.
    """
    keep, out_lines = False, []
    for line in out.splitlines():
        if line.startswith("THE ANSWER"):
            keep = True
        if keep and (":" in line) and ("ABSTAIN" in line or "abstains" in line
                                        or "misreads" in line or "neither" in line):
            out_lines.append(line.strip())
    return " || ".join(out_lines) or "<no answer block>"


def reach(out):
    for line in out.splitlines():
        if line.strip().startswith("records"):
            return line.strip()
    return "<no reach line>"


def main():
    if SENTINEL.is_file():
        print("REFUSING TO START: a previous battery was interrupted.")
        print(SENTINEL.read_text())
        return 2

    original = TARGET.read_bytes()
    SNAP.write_bytes(original)
    SENTINEL.write_text(json.dumps({
        "file": str(TARGET), "sha256": hashlib.sha256(original).hexdigest(),
        "snapshot": str(SNAP)}, indent=1))

    try:
        print("=" * 70)
        print("POSITIVE CONTROL FIRST -- an unmutated run must pass")
        print("=" * 70)
        code, out = run()
        base_answer, base_reach = answer(out), reach(out)
        print("  exit=%d  %s" % (code, base_reach))
        print("  answer: %s" % base_answer)
        if code != 0:
            print("  DEAD: the subject does not pass unmutated.")
            return 1
        print()

        results = []
        for name, old, new, why in ARMS:
            src = original.decode()
            if old not in src:
                results.append((name, "BAD ANCHOR", why, ""))
                print("%-32s BAD ANCHOR -- arm did not run" % name)
                continue
            TARGET.write_text(src.replace(old, new, 1))
            code, out = run()
            a, r = answer(out), reach(out)
            changed = (code != 0) or (a != base_answer) or (r != base_reach)
            results.append((name, "RED" if changed else "SURVIVED", why,
                            "exit=%d answer=%s" % (code, a)))
            print("%-32s %-9s exit=%d  answer=%s" %
                  (name, "RED" if changed else "SURVIVED", code, a))
            TARGET.write_bytes(original)
    finally:
        TARGET.write_bytes(SNAP.read_bytes())
        restored = hashlib.sha256(TARGET.read_bytes()).hexdigest()
        want = hashlib.sha256(original).hexdigest()
        print()
        print("RESTORE VERIFIED: %s" % ("yes" if restored == want else "NO -- TREE IS DIRTY"))
        if restored == want:
            SENTINEL.unlink(missing_ok=True)
            SNAP.unlink(missing_ok=True)

    red = sum(1 for _, s, _, _ in results if s == "RED")
    bad = [n for n, s, _, _ in results if s != "RED"]
    print("ARMS: %d red of %d%s" % (red, len(results),
                                     ("  PROBLEMS: %s" % bad) if bad else ""))
    return 0 if red == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
