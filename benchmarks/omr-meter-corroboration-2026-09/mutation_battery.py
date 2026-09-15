"""Mutation battery for A-METER-6 and the two default flips.

⚠️⚠️ **IT RESTORES FROM ITS OWN BYTE SNAPSHOT AND VERIFIES THE RESTORE — NOT
FROM GIT.** Two days before this was written a battery took ten arms red,
restored `export.py` from HEAD, and HEAD did not have the function under test:
`git diff --stat` afterwards listed only the benchmark script, and the tests
that had just passed were testing code no longer on disk. The governing form:

    A mutation battery must leave the tree as it FOUND it — which is not the
    same as leaving it as GIT has it.

⚠️ **DO NOT RUN THIS BESIDE ANOTHER ARM OR A TEST RUN.** It edits files in the
working tree, so anything else reading that tree is not isolated from it — a
session already lost its first three-arm run to exactly this collision.

⚠️ **ONE RED ARM IS NOT A BATTERY**, and a battery of REFUSAL tests can pass by
refusing everything, so `everything_refuses` is an arm here: it makes the guard
confine every change and must go RED on the test that asserts a CORROBORATED
change is carried. An arm whose anchor is not found, or is found more than
once, is reported as an ERROR rather than as a silent pass — the `for h in
heads` fault, which occurs three times in one module.
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RHYTHM = ROOT / "tools" / "omr" / "staged" / "adjudicators" / "rhythm.py"
TESTS = ["tools/omr/tests/test_staged_header_rhythm.py",
         "tools/omr/tests/test_flag_default_direction.py"]

#: (name, file, anchor, replacement, what it should break)
ARMS = [
    ("confine_nothing", RHYTHM,
     'kept = [s for s in segments if s.get("corroborated", True)]',
     'kept = list(segments)',
     "the rule itself: an uncorroborated change is carried again"),
    ("everything_refuses", RHYTHM,
     'kept = [s for s in segments if s.get("corroborated", True)]',
     'kept = []',
     "THE POSITIVE CONTROL: a corroborated change must still be carried"),
    ("absent_flag_means_uncorroborated", RHYTHM,
     'kept = [s for s in segments if s.get("corroborated", True)]',
     'kept = [s for s in segments if s.get("corroborated", False)]',
     "an OLD record, or an opening, refusing to carry"),
    ("return_the_unfiltered_value", RHYTHM,
     '''        if not kept:
            return None''',
     '''        if not kept:
            kept = list(segments)''',
     "the `None` branch: cannot-tell converted into a definite answer"),
    ("never_none", RHYTHM,
     '''    if not value:
        return None
    segments = value.get("segments")''',
     '''    if not value:
        return {}
    segments = value.get("segments")''',
     "an empty value carrying instead of abstaining"),
    ("carry_a_skipped_source_anyway", RHYTHM,
     '''        if carried is None:''',
     '''        if False:''',
     "the walk past a source with nothing corroborated"),
    ("skip_silently", RHYTHM,
     '''            skipped_uncorroborated.append(src.to_key())''',
     '''            pass''',
     "the record of WHICH source was walked past"),
    ("no_abstention_when_the_walk_runs_out", RHYTHM,
     '''    if skipped_uncorroborated:''',
     '''    if False:''',
     "`carry_source_uncorroborated`: a page that walked past a source "
     "reading like one that found none"),
    ("min_staves_one", RHYTHM,
     'METER_CHANGE_MIN_STAVES = 2',
     'METER_CHANGE_MIN_STAVES = 1',
     "the constant, and its equality with the key-sig guard"),
    ("corroborated_always_true", RHYTHM,
     '"corroborated": len(staves) >= METER_CHANGE_MIN_STAVES,',
     '"corroborated": True,',
     "the predicate that computes the flag"),
    ("carry_flag_back_to_allow_list", RHYTHM,
     '''    return os.environ.get(METER_CARRY_ENV, "1").strip().lower() not in (
        "0", "", "false", "no", "off")''',
     '''    return os.environ.get(METER_CARRY_ENV, "0").strip() == "1"''',
     "the carry default flip AND its deny-list direction"),
    ("bars_flag_back_to_allow_list", RHYTHM,
     '''    return os.environ.get(METER_FROM_BARS_ENV, "1").strip().lower() not in (
        "0", "", "false", "no", "off")''',
     '''    return os.environ.get(METER_FROM_BARS_ENV, "0").strip() == "1"''',
     "the bars default flip AND its deny-list direction"),
    ("carry_deny_list_becomes_allow_list", RHYTHM,
     '''    return os.environ.get(METER_CARRY_ENV, "1").strip().lower() not in (
        "0", "", "false", "no", "off")''',
     '''    return os.environ.get(METER_CARRY_ENV, "1").strip().lower() in (
        "1", "true", "yes", "on")''',
     "⚠️ the DIRECTION only: still default-ON for an unset var, but a TYPO "
     "now turns it off — the exact hazard the flip creates"),
    ("one_projection_two_lists", RHYTHM,
     '''    segments = [_segment_from_change(c) for c in changes]''',
     '''    segments = [{"from_cell": c["from_cell"], "numerator": c["numerator"],
                 "denominator": c["denominator"], "raw": c["raw"],
                 "support": c["support"],
                 "staves_reading_it": c["staves_reading_it"],
                 "bars_fit": c["bars_fit"],
                 "bars_contradict": c["bars_contradict"]} for c in changes]''',
     "the shared projection: `_change_only` losing the flag again, which is "
     "the defect this change actually shipped and had to repair"),
]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    a = ap.parse_args()

    # ⚠️ THE SNAPSHOT IS BYTES AND IS TAKEN BEFORE THE FIRST ARM.
    files = sorted({arm[1] for arm in ARMS})
    snapshot = {f: f.read_bytes() for f in files}
    before = {f: _digest(f) for f in files}

    def restore():
        for f, data in snapshot.items():
            f.write_bytes(data)
        bad = [str(f) for f in files if _digest(f) != before[f]]
        if bad:
            raise SystemExit("RESTORE FAILED for %s — the tree is NOT as this "
                             "battery found it. Fix by hand before doing "
                             "anything else." % ", ".join(bad))

    def run_tests() -> tuple[bool, str]:
        p = subprocess.run([sys.executable, "-m", "pytest", *TESTS, "-q",
                            "-p", "no:randomly"],
                           cwd=ROOT, capture_output=True, text=True)
        return p.returncode == 0, (p.stdout or "").strip().splitlines()[-1:]

    print("=" * 76)
    print("MUTATION BATTERY — A-METER-6 and the two default flips")
    print("=" * 76)
    ok, line = run_tests()
    print("baseline (unmutated): %s   %s" % ("GREEN" if ok else "RED", line))
    if not ok:
        restore()
        raise SystemExit("the suite is RED before any mutation — nothing below "
                         "would mean anything")

    results = []
    try:
        for name, path, anchor, repl, breaks in ARMS:
            if a.only and a.only != name:
                continue
            src = snapshot[path].decode()
            n = src.count(anchor)
            if n != 1:
                # ⚠️ REPORTED AS AN ERROR, NOT AS A PASS. An anchor occurring
                # twice mutates the wrong function and the arm goes green for
                # the wrong reason — the fermata battery's own fault.
                results.append((name, "BAD ANCHOR (%d occurrences)" % n, breaks))
                print("  %-36s BAD ANCHOR (%d)" % (name, n))
                continue
            path.write_text(src.replace(anchor, repl))
            passed, line = run_tests()
            restore()
            results.append((name, "SURVIVED" if passed else "red", breaks))
            print("  %-36s %s   %s" % (name, "SURVIVED ⚠️" if passed else "red",
                                       line if passed else ""))
    finally:
        restore()

    print()
    survived = [r for r in results if r[1] != "red"]
    print("arms: %d   red: %d   NOT red: %d"
          % (len(results), len(results) - len(survived), len(survived)))
    for name, state, breaks in survived:
        print("  ⚠️ %s (%s) — should have broken: %s" % (name, state, breaks))
    print()
    print("tree restored and VERIFIED byte-for-byte against the pre-arm "
          "snapshot.")
    return 0 if not survived else 1


if __name__ == "__main__":
    sys.exit(main())
