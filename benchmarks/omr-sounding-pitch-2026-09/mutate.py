"""Mutation battery: does a test actually go RED for each line of the change?

⚠️⚠️ THE JUDGE MUST BE ABLE TO FAIL, AND TWO BATTERIES IN THIS REPO WERE NOT.
The obvious judge -- compare pytest's summary line -- ends `" in 0.57s"`, which
differs between two runs of an UNMUTATED tree, so every arm reads red for free.
This judge is pytest's EXIT CODE plus the set of failing test ids, and it is
checked against an unmutated control run FIRST: if the control is not green the
battery refuses to start, because a battery whose baseline is red cannot
attribute anything.

⚠️⚠️ IT MUST LEAVE THE TREE AS IT FOUND IT -- WHICH IS NOT THE SAME AS LEAVING
IT AS GIT HAS IT. A `git checkout` restore destroyed a change this repo had
just certified, and an INTERRUPTED battery obeys neither: its in-memory
snapshot dies with the process and the mutation stays on disk looking exactly
like a legitimate edit. So: a BYTE snapshot on disk before arm 1, a restore
verified by hash, and an in-flight SENTINEL a later run refuses to start over.

⚠️ `PYTHONDONTWRITEBYTECODE=1` on every child. A stale `.pyc` makes an arm
import UNMUTATED code and read as NOT RED.

⚠️ A BAD ANCHOR IS REPORTED AS AN ERROR, NEVER AS A PASS. An arm whose `old`
string is absent, or present more than once, has mutated nothing (or the wrong
one of two identical lines -- the fault that silently mutated a different
function in the fermata battery). Both are loud.

    python3 benchmarks/omr-sounding-pitch-2026-09/mutate.py
    python3 benchmarks/omr-sounding-pitch-2026-09/mutate.py --only 3
"""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SNAP = HERE / ".battery-snapshot"
SENTINEL = HERE / ".battery-in-flight"

EXPORT = ROOT / "tools" / "omr" / "staged" / "export.py"

TESTS = ["tools/omr/tests/test_sounding_pitch.py",
         "tools/omr/tests/test_staged_export.py",
         "tools/omr/tests/test_staged_duration.py"]

#: (name, file, old, new, the test id that MUST go red)
ARMS = [
    ("alteration-never-applied", EXPORT,
     "            if sounding != pitch:",
     "            if False:",
     "test_the_alteration_becomes_alter_and_NOT_accidental"),

    ("alteration-read-as-None", EXPORT,
     "        alteration = None if is_rest else rec.value(Q.ACCIDENTAL, sub)",
     "        alteration = None",
     "test_the_alteration_becomes_alter_and_NOT_accidental"),

    ("sharp-spelled-as-flat", EXPORT,
     '_ALTERATION_SPELLING: Dict[str, str] = {"#": "#", "b": "b"}',
     '_ALTERATION_SPELLING: Dict[str, str] = {"#": "b", "b": "b"}',
     "test_a_sharp_key_alters_the_other_way"),

    ("stacking-guard-removed", EXPORT,
     "    if existing:\n        # Already altered -- an inline accidental "
     "would have to come from a\n        # reader that does not exist yet. "
     "Leave it alone rather than stack.\n        return pitch",
     "    if False:\n        return pitch",
     "test_it_REFUSES_rather_than_stacking_on_an_altered_pitch"),

    ("unknown-alteration-appended-anyway", EXPORT,
     "    spelled = _ALTERATION_SPELLING.get(alteration)\n"
     "    if spelled is None:\n        return pitch",
     "    spelled = _ALTERATION_SPELLING.get(alteration, alteration)\n"
     "    if spelled is None:\n        return pitch",
     "test_an_unknown_alteration_leaves_the_pitch_alone"),

    ("unparseable-pitch-not-guarded", EXPORT,
     "    parsed = _legacy._parse_pitch(pitch)\n    if parsed is None:\n"
     "        return pitch",
     "    parsed = _legacy._parse_pitch(pitch)\n    if parsed is None:\n"
     "        return pitch + (spelled or '')",
     "test_an_unparseable_pitch_is_returned_unchanged"),

    ("drawn-accidental-emitted-again", EXPORT,
     "                fermata=(ev_fermata if n == 0 else False),",
     "                fermata=(ev_fermata if n == 0 else False),\n"
     "                accidental=head.get('key_alteration'),",
     "test_the_alteration_becomes_alter_and_NOT_accidental"),

    ("counter-keeps-the-old-name", EXPORT,
     '                counters["pitches_altered_by_the_key"] += 1',
     '                counters["accidentals"] += 1',
     "test_the_counter_names_what_the_file_HOLDS"),

    ("abstention-figure-hardcoded-zero", EXPORT,
     '            "printed_glyphs_read_into_a_verdict": sum(\n'
     '                1 for v in rec.verdicts_of(Q.ACCIDENTAL)\n'
     '                if v.get("decider") != "respell_accidental"),',
     '            "printed_glyphs_read_into_a_verdict": 0,',
     "test_that_abstention_figure_is_DERIVED_not_a_literal_zero"),

    ("abstention-block-dropped", EXPORT,
     '        "accidental_reading": {',
     '        "accidental_reading_DISABLED": {',
     "test_the_UNREAD_printed_glyph_is_reported_as_an_abstention"),

    ("natural-counted-as-an-alteration", EXPORT,
     "                pitch, applied = sounding, alteration",
     "                pitch, applied = sounding, alteration\n"
     "            else:\n                applied = alteration",
     "test_a_natural_is_not_COUNTED_as_an_alteration"),

    # ⚠️ MUTATES ONE FRAGMENT OF THE CONTINUED STRING, NOT THE WHOLE ENTRY.
    # The first draft replaced the entry's opening line and left the
    # continuation lines dangling -- a SyntaxError, which collects as an
    # error rather than a failure, so the arm read "red, wrong test, got []".
    # A mutation that cannot import is not a mutation of the behaviour.
    ("false-doc-claim-restored", EXPORT,
     '    "accidental": "NOT consumed: the key-derived alteration reaches '
     '`pitch` "',
     '    "accidental": "consumed into `pitch` and `accidental`. "',
     "test_NOT_NOTATION_no_longer_claims_the_glyph_is_consumed"),
]

#: ⚠️ THE POSITIVE CONTROL, and it is in the same class as the arms rather
#: than a different kind of check: a battery of arms that all go red proves
#: the tests react to SOMETHING, not that they react to the right thing. This
#: one must go red on a DIFFERENT test from every arm above -- if it fails the
#: same test they do, the suite is reacting to "the file changed".
#: ⚠️ ITS FIRST ANCHOR WAS IN THE *LEGACY* `tools/omr/export.py`, not the
#: staged one, so it mutated nothing and reported a bad anchor -- the
#: "an anchor that occurs twice / zero times" fault this battery exists to
#: make loud, arriving in the control itself. `counters["notes"] += 1` is
#: unique to the staged exporter and is read by the staged suite's own
#: accounting assertions, which no accidental test touches.
CONTROL = ("positive-control-unrelated-break", EXPORT,
           '            counters["notes"] += 1',
           '            pass',
           None)


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def run_tests() -> tuple[int, set[str]]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, "-m", "pytest", *TESTS, "-q",
                        "--no-header", "-p", "no:cacheprovider"],
                       cwd=str(ROOT), env=env, capture_output=True, text=True)
    failing = {ln.split("::")[-1].split()[0]
               for ln in p.stdout.splitlines() if ln.startswith("FAILED")}
    return p.returncode, failing


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int)
    a = ap.parse_args()

    if SENTINEL.exists():
        raise SystemExit(
            f"REFUSING TO START: {SENTINEL} exists, so a battery was "
            f"interrupted and the tree may still hold a mutation. The files "
            f"should hash as in {SNAP}; compare before deleting it.")

    originals = {EXPORT: EXPORT.read_bytes()}
    SNAP.write_text("\n".join(f"{p}  {md5(b)}" for p, b in originals.items()))

    print("CONTROL: the unmutated tree must be GREEN, or nothing below means "
          "anything.")
    rc, failing = run_tests()
    if rc != 0:
        raise SystemExit(f"  baseline is RED ({failing}) -- battery refuses "
                         f"to start.")
    print("  baseline green.\n")

    arms = list(enumerate(ARMS + [CONTROL], 1))
    if a.only:
        arms = [x for x in arms if x[0] == a.only]

    red = survived = errors = 0
    SENTINEL.write_text("in flight\n")
    try:
        for i, (name, path, old, new, want) in arms:
            src = originals[path].decode()
            n = src.count(old)
            if n != 1:
                print(f"  [{i:2}] ERROR  {name}: anchor occurs {n} times "
                      f"(want exactly 1) -- this arm mutated nothing or the "
                      f"wrong line.")
                errors += 1
                continue
            path.write_bytes(src.replace(old, new, 1).encode())
            try:
                rc, failing = run_tests()
            finally:
                path.write_bytes(originals[path])
            if rc == 0:
                print(f"  [{i:2}] SURVIVED  {name}  <-- a real test gap")
                survived += 1
            elif want and want not in failing:
                print(f"  [{i:2}] red, WRONG TEST  {name}: wanted {want}, "
                      f"got {sorted(failing)[:3]}")
                survived += 1
            else:
                tag = f" (via {want})" if want else f" (via {sorted(failing)[:2]})"
                print(f"  [{i:2}] red      {name}{tag}")
                red += 1
    finally:
        for p, b in originals.items():
            p.write_bytes(b)
            got = md5(p.read_bytes())
            if got != md5(b):
                raise SystemExit(f"RESTORE FAILED for {p}: {got}")
        SENTINEL.unlink()
        print("\n  restored every file and VERIFIED the hashes.")

    print(f"\n  {red} red, {survived} survived, {errors} bad anchors")
    return 1 if (survived or errors) else 0


if __name__ == "__main__":
    sys.exit(main())
