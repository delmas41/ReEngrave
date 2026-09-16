"""Mutation battery for the contest join and its test.

⚠️⚠️ IT RESTORES FROM ITS OWN SNAPSHOT, NEVER FROM GIT.  CLAUDE.md records a
battery that `git checkout`ed the files it mutates, found HEAD did not carry
the new function, and **destroyed the change it had just certified**.  The
governing form there: *a mutation battery must leave the tree as it FOUND it —
which is not the same as leaving it as GIT has it.*  So every file is read into
memory before the first arm, written back after each one, and the restore is
VERIFIED byte for byte before the next arm starts.

⚠️ ARMS ARE ANCHORED ON TEXT THAT OCCURS EXACTLY ONCE.  Two sessions have now
lost a battery to an anchor that matched twice and mutated a different
function, so an anchor with a count other than 1 is reported as a BAD ANCHOR
and never as a silent pass.

⚠️ A BATTERY OF "THE JOIN SAYS UNREACHABLE" TESTS CAN PASS BY SAYING
UNREACHABLE TO EVERYTHING, so there is a POSITIVE control in the same class:
an arm that makes the probe's own positive control (the hand-named `ffff`
cells) go dark must be caught, and an arm that changes nothing must be reported
as SURVIVED rather than quietly counted as red.
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PROBE = ROOT / "benchmarks/omr-phantom-notes-2026-09/probe/contest_join.py"
TEST = ROOT / "tools/omr/tests/test_contest_join.py"

#: (name, file, old, new, how it is meant to be caught)
ARMS = [
    # ⚠️ ANCHORED ON THE NEWLINE, because the bare assignment text also
    # appears inside the module docstring -- the first run reported it as a
    # BAD ANCHOR, which is the report doing its job.
    ("contest_iou_drifts", PROBE,
     "\nCONTEST_IOU = 0.5\n", "\nCONTEST_IOU = 0.9\n",
     "test_contest_join: the restated constant no longer equals gather's"),
    ("contest_iou_drifts_down", PROBE,
     "\nCONTEST_IOU = 0.5\n", "\nCONTEST_IOU = 0.1\n",
     "test_contest_join: same, the other direction"),
    ("join_ignores_the_staff_index", PROBE,
     'return (int(k[1]), int(k[2]), int(k[3]), int(k[4]))',
     'return (int(k[1]), int(k[2]), 0, int(k[4]))',
     "the probe: every bar becomes reachable and the answer inverts"),
    ("join_ignores_the_cell_index", PROBE,
     'return (int(k[1]), int(k[2]), int(k[3]), int(k[4]))',
     'return (int(k[1]), int(k[2]), int(k[3]), 0)',
     "the probe: the cell-agreement control and the answer both move"),
    ("scope_filter_dropped", PROBE,
     'if p["scope"] == "same_system_other_staff":',
     'if True:',
     "the probe: same-cell pairs leak into the cross-staff index"),
    # ⚠️ EQUIVALENT ON THIS DOCUMENT AND NOT ON THE MECHANISM: not one of the
    # eighteen print-silent bars carries a suffix-only pair, so the probe's
    # ANSWER cannot move.  It is caught by the unit tests instead
    # (`TestTheSplitTheJoinDependsOn`), which is why the arm stays in the list.
    ("same_class_gate_dropped", PROBE,
     '            if p["same_class"]:',
     '            if True:',
     "test_contest_join: a suffix-only pair must not become a contest"),
    ("rest_slot_window_widened", PROBE,
     "    if 5 <= step <= 6:", "    if 4 <= step <= 7:",
     "the probe: the cross-tab stops reproducing FINDINGS §4's 8/14/3"),
    ("staff_span_widened", PROBE,
     "    if step < 0 or step > 8:", "    if step < -4 or step > 12:",
     "the probe: outside_the_staff collapses and 8/14/3 breaks"),
    ("the_test_stops_reading_the_source", TEST,
     'return ast.literal_eval(node.value)', 'return 0.5',
     "POSITIVE CONTROL: the test must still fail when the probe drifts"),
]


def run(cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def probe_signature():
    """What the probe says, reduced to the three lines an arm could move."""
    r = run([sys.executable, str(PROBE), "--check"])
    keep = []
    for line in r.stdout.splitlines():
        s = line.strip()
        if (s.startswith("POSITIVE CONTROL")
                or "UNREACHABLE by the repair" == s[-24:] and "bars" in s
                or s.startswith(("at_the_rest_slot", "outside_the_staff",
                                 "inside_elsewhere", "TOTAL",
                                 "cross-staff pairs sharing"))):
            keep.append(s)
    return r.returncode, "\n".join(keep)


def suite():
    r = run([sys.executable, "-m", "pytest", "-q",
             "tools/omr/tests/test_contest_join.py"])
    return r.returncode


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    args = ap.parse_args(argv)

    files = sorted({a[1] for a in ARMS})
    snapshot = {f: f.read_text() for f in files}

    base_rc, base_sig = probe_signature()
    base_suite = suite()
    print(f"BASELINE  probe rc={base_rc}  suite rc={base_suite}")
    if base_rc != 0 or base_suite != 0:
        print("DEAD: the baseline is not green; a red arm would mean nothing.")
        return 2
    print(base_sig)
    print()

    red = surv = bad = 0
    try:
        for name, path, old, new, how in ARMS:
            if args.only and args.only != name:
                continue
            src = snapshot[path]
            n = src.count(old)
            if n != 1:
                print(f"  BAD ANCHOR  {name}: anchor occurs {n} times in "
                      f"{path.name}")
                bad += 1
                continue
            path.write_text(src.replace(old, new))
            rc, sig = probe_signature()
            src_rc = suite()
            caught = (src_rc != 0) or (rc != 0) or (sig != base_sig)
            tag = "RED " if caught else "SURVIVED"
            print(f"  {tag}  {name}")
            if caught:
                red += 1
                why = []
                if src_rc != 0:
                    why.append("suite fails")
                if rc != 0:
                    why.append("probe --check non-zero")
                if sig != base_sig:
                    why.append("probe answer moved")
                print(f"          caught by: {', '.join(why)}   ({how})")
            else:
                surv += 1
                print(f"          expected: {how}")
            path.write_text(src)
            assert path.read_text() == snapshot[path], "restore failed"
    finally:
        for f, src in snapshot.items():
            f.write_text(src)
        for f, src in snapshot.items():
            assert f.read_text() == src, f"RESTORE FAILED for {f}"
        print("\nrestored every mutated file from the in-memory snapshot, "
              "verified byte for byte")

    rc2, sig2 = probe_signature()
    print(f"post-battery probe rc={rc2}, answer unchanged: {sig2 == base_sig}")
    print(f"\nARMS: {red} red, {surv} survived, {bad} bad anchors")
    return 0 if surv == 0 and bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
