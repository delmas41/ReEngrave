"""Mutation battery for the staged C-clef wiring.

⚠️ THE JUDGE MUST BE ABLE TO FAIL, and this repo has twice shipped a battery
that could not. Comparing pytest's SUMMARY LINE is the trap: it ends
`" in 0.57s"`, so two runs of an UNMUTATED tree differ and every arm reads
red for free. This judge runs the arm's NAMED test node and reads its EXIT
CODE -- unambiguous, and an arm whose mutation does not reach that test exits
0 and is reported as a SURVIVOR.

⚠️ A SYNTAX ERROR IS A FAKE RED. A mutation that breaks parsing makes every
test error and the exit code says "red" for the wrong reason, so each mutated
file is `ast.parse`d before the test runs and a parse failure is an ERROR,
never a pass.

⚠️ A BAD ANCHOR IS AN ERROR, NOT A PASS. An anchor that does not appear
EXACTLY once means the arm mutated nothing (or mutated two places); this repo
has lost whole battery runs to an anchor matching a second, unrelated
function. Counted, and reported as BAD ANCHOR.

⚠️ A BATTERY OF REFUSAL TESTS CAN PASS BY REFUSING EVERYTHING, so arm
`refuse_everything` exists specifically to be caught by an ADMISSION test,
and the positive control runs the whole file green on the unmutated tree
BEFORE any arm.

⚠️ IT MUST LEAVE THE TREE AS IT FOUND IT -- which is not the same as leaving
it as GIT has it, and an INTERRUPTED battery obeys neither. A byte snapshot
is taken before arm 1, an in-flight SENTINEL is written beside it, the
restore is VERIFIED by hash, and a run that finds a stale sentinel refuses to
start and names each file at risk.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SENTINEL = HERE / ".battery-in-flight.json"

GATHER = ROOT / "tools/omr/staged/gather.py"
CLEF = ROOT / "tools/omr/staged/adjudicators/clef.py"
TESTS = "tools/omr/tests/test_staged_c_clef.py"

TOUCHED = [GATHER, CLEF]

#: (name, file, anchor, replacement, the test that MUST go red)
ARMS = [
    # ---- the gather-side admission rule ----
    ("drop_the_category_test", GATHER,
     '    if category != "clef":\n        return False\n',
     '    if False:\n        return False\n',
     "TestTheCategoryTestIsLoadBearing::test_a_flag_is_not_a_bass_clef"),

    ("revert_to_the_incumbent_set", GATHER,
     '    if category != "clef":\n        return False\n'
     '    from ..clef_geometry import clef_family\n'
     '    if clef_family(name) is not None:\n        return True\n',
     '    return name in _CLEF_CLASSES_INCUMBENT\n'
     '    from ..clef_geometry import clef_family\n'
     '    if clef_family(name) is not None:\n        return True\n',
     "TestTheGathererAdmitsTheFineCClefs::test_clefCAlto_is_GATHERED"),

    ("admit_octave_marks_by_prefix", GATHER,
     '    if clef_family(name) is not None:\n        return True\n',
     '    if str(name or "").startswith("clef"):\n        return True\n',
     "TestAnOctaveMarkIsNotAClef::test_clef8_is_NOT_gathered"),

    ("admit_everything", GATHER,
     '    if category != "clef":\n        return False\n',
     '    if category != "clef":\n        return True\n',
     "TestTheCategoryTestIsLoadBearing::test_a_flag_is_not_a_bass_clef"),

    ("refuse_everything", GATHER,
     '    if category != "clef":\n        return False\n',
     '    if True:\n        return False\n',
     "TestTheGathererAdmitsTheFineCClefs::test_clefCAlto_is_GATHERED"),

    ("drop_the_percussion_clause", GATHER,
     '    return "percussion" in (name or "").lower()\n',
     '    return False\n',
     "TestTheIncumbentSetAdmittedASpellingThatNeverFires::"
     "test_the_repaired_rule_admits_every_pitched_clef_of_the_vocabulary"),

    # ---- the call site: the category must actually be PASSED ----
    ("call_site_passes_no_category", GATHER,
     '        clefs = [d for d in dets\n'
     '                 if _is_clef_class(d.smufl_name, d.category)]',
     '        clefs = [d for d in dets\n'
     '                 if _is_clef_class(d.smufl_name, "clef")]',
     "TestTheCategoryTestIsLoadBearing::test_a_flag_is_not_a_bass_clef"),

    # ---- the consumer: C-family support ----
    ("family_support_back_to_the_literal_clefC", CLEF,
     '        if clef_family(str(row.value)) == "C":\n',
     '        if str(row.value) == "clefC":\n',
     "TestTheFineCClefsSUPPORTTheClefTheLocatorNamed::"
     "test_clefCAlto_supports_the_locators_C_clef"),

    ("family_support_accepts_every_row", CLEF,
     '        if clef_family(str(row.value)) == "C":\n',
     '        if True:\n',
     "TestTheFineCClefsSUPPORTTheClefTheLocatorNamed::"
     "test_a_G_clef_is_NOT_C_family_support"),

    ("family_support_matches_G_instead", CLEF,
     '        if clef_family(str(row.value)) == "C":\n',
     '        if clef_family(str(row.value)) == "G":\n',
     "TestTheFineCClefsSUPPORTTheClefTheLocatorNamed::"
     "test_clefCAlto_supports_the_locators_C_clef"),

    # ---- the refusal that must SURVIVE the wiring ----
    ("let_the_class_name_name_the_C_clef", CLEF,
     '_GLYPH_TO_CLEF = {\n    "clefG": "treble",\n',
     '_GLYPH_TO_CLEF = {\n    "clefCAlto": "alto",\n    "clefCTenor": "tenor",\n'
     '    "clefG": "treble",\n',
     # ⚠️ THIS ARM SURVIVED ITS FIRST AIMING AND THE SURVIVAL WAS THE
     # FINDING, not a test gap to paper over. It was aimed at
     # `..._CANNOT_overturn_the_locator...`, which asserts the VALUE -- and
     # the value does not change, because two locator crops outweigh a named
     # tenor 5.5 to 4.5. The claim in the docstring was wrong and was
     # corrected. What the mutation really does is erode the MARGIN to
     # exactly the floor, so that is what the arm is judged by now.
     "TestAClassNameStillCannotNameWhichCClef::"
     "test_naming_the_clef_would_erode_the_margin_to_the_FLOOR"),

    ("let_the_class_name_name_the_C_clef__one_crop", CLEF,
     '_GLYPH_TO_CLEF = {\n    "clefG": "treble",\n',
     '_GLYPH_TO_CLEF = {\n    "clefCAlto": "alto",\n    "clefCTenor": "tenor",\n'
     '    "clefG": "treble",\n',
     "TestAClassNameStillCannotNameWhichCClef::"
     "test_with_ONE_crop_naming_the_clef_DOES_flip_the_staff"),
]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _pytest(node: str) -> int:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run(
        [sys.executable, "-m", "pytest", f"{TESTS}::{node}", "-q", "--tb=no",
         "-p", "no:cacheprovider"],
        cwd=ROOT, capture_output=True, text=True, env=env)
    return r.returncode


def main() -> int:
    if SENTINEL.exists():
        stale = json.loads(SENTINEL.read_text())
        print("REFUSING TO START: a previous battery was interrupted and the "
              "tree may still hold a mutation.\nFiles at risk, with the hash "
              "each should have:")
        for f, h in stale["snapshot"].items():
            cur = _sha(Path(f)) if Path(f).exists() else "MISSING"
            flag = "OK" if cur == h else "*** DIFFERS ***"
            print(f"  {f}\n    expected {h}\n    actual   {cur}  {flag}")
        print(f"\nRestore them, then delete {SENTINEL}")
        return 2

    snapshot = {str(p): p.read_bytes() for p in TOUCHED}
    hashes = {str(p): _sha(p) for p in TOUCHED}

    # ⚠️ POSITIVE CONTROL FIRST. An arm is only evidence if the unmutated tree
    # is green on the very file the arms are judged by.
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    base = subprocess.run(
        [sys.executable, "-m", "pytest", TESTS, "-q", "--tb=no",
         "-p", "no:cacheprovider"],
        cwd=ROOT, capture_output=True, text=True, env=env)
    if base.returncode != 0:
        print("POSITIVE CONTROL FAILED: the unmutated tree is not green.")
        print(base.stdout[-3000:])
        return 2
    print(f"positive control: unmutated tree GREEN on {TESTS}\n")

    SENTINEL.write_text(json.dumps({"snapshot": hashes}, indent=2))
    results = []
    try:
        for name, path, anchor, repl, node in ARMS:
            src = path.read_text()
            n = src.count(anchor)
            if n != 1:
                results.append((name, f"BAD ANCHOR (appears {n}x)"))
                print(f"  {name:42s} BAD ANCHOR (appears {n}x)")
                continue
            path.write_text(src.replace(anchor, repl, 1))
            try:
                # a syntax error is a FAKE RED
                try:
                    ast.parse(path.read_text())
                except SyntaxError as e:
                    results.append((name, f"ERROR: mutation does not parse ({e})"))
                    print(f"  {name:42s} ERROR (does not parse)")
                    continue
                rc = _pytest(node)
                verdict = "RED" if rc != 0 else "SURVIVED"
                results.append((name, verdict))
                print(f"  {name:42s} {verdict:9s} <- {node.split('::')[-1]}")
            finally:
                path.write_bytes(snapshot[str(path)])
    finally:
        for p in TOUCHED:
            p.write_bytes(snapshot[str(p)])
        after = {str(p): _sha(p) for p in TOUCHED}
        ok = after == hashes
        print(f"\nrestore verified: {'OK' if ok else '*** TREE NOT RESTORED ***'}")
        if ok:
            SENTINEL.unlink(missing_ok=True)

    red = sum(1 for _, v in results if v == "RED")
    surv = [n for n, v in results if v == "SURVIVED"]
    errs = [(n, v) for n, v in results if v not in ("RED", "SURVIVED")]
    print(f"\n{red} RED / {len(ARMS)} arms, {len(surv)} survivors, "
          f"{len(errs)} errors")
    for n in surv:
        print(f"  SURVIVOR: {n}")
    for n, v in errs:
        print(f"  {v}: {n}")
    return 0 if (not surv and not errs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
