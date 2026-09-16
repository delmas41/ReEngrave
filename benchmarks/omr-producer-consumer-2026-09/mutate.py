#!/usr/bin/env python3
"""Mutation battery for `staged.wiring` and the roster repair.

    python3 benchmarks/omr-producer-consumer-2026-09/mutate.py

⚠️⚠️ **NEVER RUN THIS BESIDE AN A/B ARM THAT READS THE WORKING TREE.** It
`git checkout`s the files it mutates, and that collision has already cost a
session in this repo its first three-arm run. Run it alone.

⚠️ **ONE RED ARM IS NOT A BATTERY.** Running a single mutation, seeing red and
stopping is the reassurance that hides the rest — measured here once at five
of six surviving behind one that did not, and it shipped. Every arm below is
run.

⚠️ **A BATTERY OF REFUSAL TESTS CAN PASS BY REFUSING EVERYTHING**, so arm 15 is
a POSITIVE CONTROL in the same class: an edit that changes nothing must leave
the suite GREEN. Without it, a battery whose test file is broken reports every
arm red and reads as a perfect score.

⚠️ **AN ANCHOR THAT OCCURS TWICE MUTATES THE WRONG FUNCTION** — the fermata
battery silently mutated a different function that way, and the part-join one
picked the wrong of two `pdf_path` forwards differing by a space of
indentation. Every anchor here is checked for EXACTLY ONE occurrence, and an
arm whose anchor is missing or ambiguous is reported as an ERROR, never as a
silent pass.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
W = "tools/omr/staged/wiring.py"
I = "tools/omr/staged/adjudicators/identity.py"
G = "tools/omr/staged/gather.py"
M = "tools/omr/staged/__main__.py"
TESTS = "tools/omr/tests/test_staged_wiring.py"

#: `(name, file, anchor, replacement, the test that must go RED)`
ARMS = [
    # ── the FRAME question ───────────────────────────────────────────────────
    ("subject=/scope= reads are judged as EXACT", W,
     '                    (scoped if ("subject" in kws or "scope" in kws)\n'
     '                     else exact).add(q)',
     '                    exact.add(q)',
     "TestTheFrameQuestion::test_a_downward_read_with_its_own_reach_is_NOT_a_fault"),
    ("an unresolvable Kind defaults to a real one", W,
     "    if isinstance(node, ast.Name):\n"
     "        return bound.get(node.id)",
     "    if isinstance(node, ast.Name):\n"
     "        return bound.get(node.id) or 'staff'",
     "TestTheFrameQuestion::test_an_unresolvable_subject_is_NAMED_never_defaulted"),
    ("the gather walk skips its interprocedural round", W,
     '        if not grown:\n            break',
     '        break\n        if not grown:\n            break',
     "TestTheFrameQuestion::test_the_gather_walk_reaches_a_FIXPOINT_over_its_own_parameters"),

    # ── the DETAIL question ──────────────────────────────────────────────────
    ("a TEST naming a key counts as reading it", W,
     '            if _tree_of(path) == "test":\n                continue',
     '            if False:\n                continue',
     "TestTheDetailQuestion::test_it_finds_keys_written_and_named_nowhere_else"),
    ("this module's own gap list counts as reading", W,
     '            if path.resolve() == pathlib.Path(__file__).resolve():\n'
     '                continue',
     '            if False:\n                continue',
     "TestTheDetailQuestion::test_it_finds_keys_written_and_named_nowhere_else"),
    ("the row-kwarg list is hand-written", W,
     '        for p in inspect.signature(fn).parameters.values():',
     '        for p in []:',
     "TestTheDetailQuestion::test_the_row_kwarg_list_is_DERIVED_from_the_signature"),

    # ── the CONTROLS ─────────────────────────────────────────────────────────
    ("a dead question exits like an ordinary finding", W,
     '              f"NOTHING.", file=sys.stderr)\n        return 2',
     '              f"NOTHING.", file=sys.stderr)\n        return 1',
     "TestTheToolIsAliveAtAll::test_check_refuses_before_it_looks_at_findings_when_a_control_dies"),

    # ── the ROSTER repair ────────────────────────────────────────────────────
    ("⚠️ THE FRAME FAULT RESTORED: read the roster at EXACT", I,
     '    roster_rows = ev.rows(Q.ROSTER_ENTRY, scope=Scope.SELF_AND_ANCESTORS)',
     '    roster_rows = ev.rows(Q.ROSTER_ENTRY)',
     "TestTheRosterReachesTheDecision::test_a_singer_on_a_work_with_no_singers_is_VETOED"),
    ("the veto names nothing it looked at", I,
     '        return Ruling(value=None, reason="vetoed_by_the_work_roster",\n'
     '                      used=used,',
     '        return Ruling(value=None, reason="vetoed_by_the_work_roster",\n'
     '                      used=(),',
     "TestTheRosterReachesTheDecision::test_the_roster_row_is_in_the_verdict_BASIS"),
    ("a PAGE-sourced roster is admitted", I,
     '    if value.get("source_kind") != "catalog":\n        return None',
     '    if False:\n        return None',
     "TestTheRosterReachesTheDecision::test_a_PAGE_sourced_roster_is_REFUSED_at_the_point_of_use"),
    ("the record carries the object, not a dict", G,
     '        row = log.observe(R.DOCUMENT, Q.ROSTER_ENTRY, value,',
     '        row = log.observe(R.DOCUMENT, Q.ROSTER_ENTRY, roster,',
     "TestTheRosterReachesTheDecision::test_the_record_carries_a_DICT_a_consumer_can_parse"),
    ("the CLI has the flag and does not pass it", M,
     '        conf_threshold=args.conf, imgsz=args.imgsz, roster=roster,',
     '        conf_threshold=args.conf, imgsz=args.imgsz,',
     "TestTheCLIHasTheProducer::test_run_staged_actually_receives_it"),
    ("--no-roster is ignored", M,
     '    if not args.no_roster:',
     '    if True:',
     "TestTheCLIHasTheProducer::test_no_roster_turns_it_off"),

    # ── the ROUNDTRIP question ───────────────────────────────────────────────
    ("roundtrip compares KEY NAMES, so a rename reads as a drop", W,
     "                for n in ast.walk(to_json):\n"
     "                    if (isinstance(n, ast.Attribute)\n"
     "                            and isinstance(n.value, ast.Name)\n"
     "                            and n.value.id == \"self\"):\n"
     "                        emitted.add(n.attr)",
     "                for n in ast.walk(to_json):\n"
     "                    if (isinstance(n, ast.Constant)\n"
     "                            and isinstance(n.value, str)):\n"
     "                        emitted.add(n.value)",
     "TestTheRoundTripQuestion::test_a_RENAME_is_not_a_DROP"),
    ("roundtrip skips fields nothing reads, so the live one is lost", W,
     '                    if f in emitted:\n                        continue',
     '                    if f in emitted or True:\n                        continue',
     "TestTheRoundTripQuestion::test_it_finds_the_live_instance_WITHOUT_being_told"),
    ("a dropped field's READ flag is always False", W,
     '                        "read": n_uses > 1,',
     '                        "read": False,',
     "TestTheRoundTripQuestion::test_it_finds_the_live_instance_WITHOUT_being_told"),

    # ── the --run corroboration ─────────────────────────
    ("--run looks for the rows under the wrong key", W,
     '    record = data.get("record")',
     '    record = data.get("log")',
     "TestTheRunCorroboration::test_it_reads_the_rows_a_real_record_carries"),
    ("--run reports zero instead of refusing", W,
     '    if record is None:\n        raise KeyError(',
     '    if record is None and False:\n        raise KeyError(',
     "TestTheRunCorroboration::test_a_record_with_no_rows_key_RAISES_rather_than_reporting_zero"),

    # ── the POSITIVE CONTROL ─────────────────────────────────────────────────
    ("POSITIVE CONTROL: a no-op edit must stay GREEN", W,
     '_HERE = pathlib.Path(__file__).resolve().parent',
     '_HERE = pathlib.Path(__file__).resolve().parent  # no-op',
     None),
]


def run(test):
    target = f"{TESTS}::{test}" if test else TESTS
    r = subprocess.run([sys.executable, "-m", "pytest", target, "-q",
                        "--no-header", "-p", "no:cacheprovider"],
                       cwd=ROOT, capture_output=True, text=True)
    return r.returncode


def main() -> int:
    dirty = subprocess.run(["git", "status", "--porcelain", "--", W, I, G, M],
                           cwd=ROOT, capture_output=True, text=True).stdout
    if dirty.strip():
        print("⚠️ REFUSING: the files this mutates have uncommitted changes.\n"
              "   A battery that `git checkout`s a dirty file DESTROYS work,\n"
              "   and cannot tell its own mutation from yours.\n" + dirty)
        return 2

    print("── baseline ──")
    if run(None) != 0:
        print("⚠️ REFUSING: the suite is RED before any mutation. Every arm "
              "would 'pass'.")
        return 2
    print("   green\n")

    red, survived, errors = [], [], []
    for name, rel, anchor, repl, test in ARMS:
        path = ROOT / rel
        src = path.read_text()
        n = src.count(anchor)
        if n != 1:
            # ⚠️ REPORTED AS AN ERROR, NEVER AS A PASS. An anchor occurring
            # twice mutates the wrong function and the arm then "survives"
            # for a reason that has nothing to do with the code under test.
            errors.append(f"{name}: anchor occurs {n} times in {rel}")
            print(f"  ERROR   {name}  (anchor x{n})")
            continue
        path.write_text(src.replace(anchor, repl))
        try:
            rc = run(test)
        finally:
            subprocess.run(["git", "checkout", "--", rel], cwd=ROOT,
                           capture_output=True)
        if test is None:
            # ⚠️ THE POSITIVE CONTROL IS NOT A SURVIVOR AND MUST NOT BE
            # COUNTED AS ONE. Listing it beside the real survivors made the
            # summary read "2 survived" when there was one, which is exactly
            # the kind of miscount that gets a genuine gap waved through.
            ok = rc == 0
            print(f"  {'GREEN ' if ok else 'RED   '}  {name}")
            if not ok:
                errors.append(f"{name}: a no-op edit turned the suite RED")
            continue
        if rc != 0:
            red.append(name)
            print(f"  RED     {name}")
        else:
            survived.append(name)
            print(f"  SURVIVED {name}  ⚠️ the test does not reach this")

    print(f"\n── {len(red)} red, {len(survived)} survived, "
          f"{len(errors)} errors")
    for s in survived:
        print(f"   SURVIVED: {s}")
    for e in errors:
        print(f"   ERROR:    {e}")
    return 0 if (not errors and len(survived) <= 1) else 1


if __name__ == "__main__":
    raise SystemExit(main())
