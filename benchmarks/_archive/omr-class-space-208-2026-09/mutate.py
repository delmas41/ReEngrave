#!/usr/bin/env python3
"""Mutation battery for the class-space repair.

Run from the repo root:
    PYTHONDONTWRITEBYTECODE=1 python3 benchmarks/omr-class-space-208-2026-09/mutate.py

⚠️ THE JUDGE MUST BE ABLE TO FAIL, AND THE OBVIOUS JUDGE CANNOT. Comparing
pytest's summary line verbatim is not a judge: it ends `" in 0.57s"` and
differs between two runs of an UNMUTATED tree, so every arm reads as red and
the battery measures nothing. Two batteries in this repo were doing exactly
that. This one judges on (a) a non-zero exit AND (b) the arm's own NAMED test
appearing in the FAILED set. An arm whose mutation applies but whose named
test stays green is reported SURVIVED; an arm whose anchor does not apply
exactly once is reported MIS-ANCHORED and is an error, never a pass.

⚠️ A BATTERY MUST LEAVE THE TREE AS IT FOUND IT -- WHICH IS NOT THE SAME AS
LEAVING IT AS GIT HAS IT. The restore is from a BYTE snapshot taken before arm
1, and it is VERIFIED by hash afterwards. `git checkout` would restore HEAD,
which is not necessarily what was on disk.

⚠️ AN INTERRUPTED BATTERY OBEYS NEITHER. A sentinel is written before arm 1
and removed on a clean exit; a run that finds one refuses to start and names
each file at risk with the hash it should have.

⚠️ PYTHONDONTWRITEBYTECODE, because a stale `.pyc` makes an arm import
UNMUTATED code and read as NOT RED.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GC = ROOT / "tools" / "omr" / "staged" / "gather_coverage.py"
SENTINEL = Path(__file__).resolve().parent / ".battery-in-flight"

TESTS = ["tools/omr/tests/test_gather_coverage_class_space.py",
         "tools/omr/tests/test_staged_gather_coverage.py"]

#: (name, file, old, new, test expected to go RED)
#: `None` as the expected test marks the POSITIVE CONTROL: no mutation, and
#: the suite must be GREEN. A battery of red arms proves nothing if the
#: unmutated tree is also red.
ARMS = [
    ("POSITIVE CONTROL (no mutation)", GC, None, None, None),

    ("revert to the 146-name training snapshot", GC,
     "    return tuple(dict.fromkeys(canonical(n) for n in vocabulary()))",
     "    import tools.omr.training.deepscores_classes as _d\n"
     "    return tuple(_d.DEEPSCORES_V2_CLASSES)",
     "test_the_audited_space_is_the_canonical_shipped_vocabulary"),

    ("audit the RAW 208 instead of the canonical space", GC,
     "    return tuple(dict.fromkeys(canonical(n) for n in vocabulary()))",
     "    return tuple(dict.fromkeys(vocabulary()))",
     "test_a_coarse_name_is_audited_under_the_spelling_that_arrives"),

    ("drop the dedupe, so duplicate ids leak into the space", GC,
     "    return tuple(dict.fromkeys(canonical(n) for n in vocabulary()))",
     "    return tuple(canonical(n) for n in vocabulary())",
     "test_the_audited_space_is_the_canonical_shipped_vocabulary"),

    ("canonicalize nothing (identity alias)", GC,
     "from ..class_aliases import canonical, vocabulary",
     "from ..class_aliases import vocabulary\ncanonical = lambda n: n",
     "test_a_coarse_name_is_audited_under_the_spelling_that_arrives"),

    ("map the coarse articulations to no quantity", GC,
     '    "articulation": "ARTICULATION_MARK",',
     '    "articulation": None,',
     "test_the_coarse_articulations_are_mapped_where_gather_files_them"),

    ("map the coarse articulations to the WRONG quantity", GC,
     '    "articulation": "ARTICULATION_MARK",',
     '    "articulation": "REST",',
     "test_the_coarse_articulations_are_mapped_where_gather_files_them"),

    ("drop `articulation` from FAMILY_TO_Q entirely", GC,
     '    "articulation": "ARTICULATION_MARK",',
     "",
     "test_every_detector_family_is_mapped"),

    ("drop `numeral` from FAMILY_TO_Q", GC,
     '    "numeral": None,',
     "",
     "test_every_detector_family_is_mapped"),

    ("drop `tuple` from FAMILY_TO_Q", GC,
     '    "tuple": None,',
     "",
     "test_every_detector_family_is_mapped"),

    ("restore the phantom family `g` the snapshot invented", GC,
     '    "clef": "CLEF_GLYPH",',
     '    "clef": "CLEF_GLYPH",\n    "g": "CLEF_GLYPH",',
     "test_no_family_in_the_table_is_dead"),

    ("restore all four phantom families", GC,
     '    "clef": "CLEF_GLYPH",',
     '    "clef": "CLEF_GLYPH",\n    "c": "CLEF_GLYPH",\n'
     '    "f": "CLEF_GLYPH",\n    "g": "CLEF_GLYPH",\n    "unpitched": None,',
     "test_no_family_in_the_table_is_dead"),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def failed_tests(out: str) -> set:
    """The NAMED tests pytest reported as failed. Never the summary line."""
    names = set()
    for line in out.splitlines():
        if line.startswith("FAILED "):
            rest = line.split(" ", 1)[1]
            if "::" in rest:
                names.add(rest.split("::")[-1].split(" ")[0])
    return names


def run_tests() -> tuple:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-m", "pytest", *TESTS,
                        "-q", "-p", "no:randomly", "--no-header"],
                       capture_output=True, text=True, cwd=str(ROOT), env=env)
    return r.returncode, r.stdout + r.stderr


def judge_self_test(snapshot: bytes, before: str) -> bool:
    """Prove the judge can FAIL before trusting a single red arm.

    A WHITESPACE-ONLY MUTANT CANNOT CHANGE BEHAVIOUR, so a judge that reports
    it RED is measuring run-to-run noise and every red arm below is worthless.
    That is the failure two batteries in this repo actually had -- they
    compared pytest's summary line, which ends `" in 0.57s"`.

    Run as a SELF-TEST and deliberately NOT as an arm: an arm that can never
    go red trains the next reader to skim the list.
    """
    anchor = "FAMILY_TO_Q: Dict[str, Optional[str]] = {"
    src = GC.read_text()
    if src.count(anchor) != 1:
        print("  [ERR] judge self-test anchor is not unique")
        return False
    GC.write_text(src.replace(anchor, anchor.replace(":", ": ", 1)))
    code, _ = run_tests()
    GC.write_bytes(snapshot)
    assert sha(GC) == before, "restore failed during judge self-test"
    survived = code == 0
    print(f"  [{'ok ' if survived else 'BAD'}] JUDGE SELF-TEST "
          f"(whitespace-only mutant): "
          f"{'SURVIVED as required' if survived else 'RED -- the judge is noise'}")
    return survived


def main() -> int:
    if SENTINEL.exists():
        print("REFUSING TO START: a previous battery did not finish.")
        print(SENTINEL.read_text())
        return 2

    dirty = subprocess.run(["git", "status", "--porcelain", "--", str(GC)],
                           capture_output=True, text=True, cwd=str(ROOT)).stdout
    if dirty.strip() and "--force" not in sys.argv:
        print(f"REFUSING: {GC.name} is dirty. Commit first, or pass --force.")
        print("  (a battery over an uncommitted change can destroy it)")
        return 2

    snapshot = GC.read_bytes()
    before = sha(GC)
    SENTINEL.write_text(f"AT RISK: {GC}\n  restore to sha256[:16] = {before}\n")

    results = []
    judge_ok = False
    try:
        judge_ok = judge_self_test(snapshot, before)
        for name, path, old, new, expect in ARMS:
            if old is None:                                   # positive control
                code, out = run_tests()
                ok = code == 0
                results.append((name, "GREEN" if ok else "RED", ok,
                                "" if ok else "the UNMUTATED tree is red"))
                print(f"  [{'ok ' if ok else 'BAD'}] {name}: "
                      f"{'green as required' if ok else 'RED -- battery invalid'}")
                continue

            src = path.read_text()
            n = src.count(old)
            if n != 1:
                results.append((name, "MIS-ANCHORED", False,
                                f"anchor occurs {n} times, expected 1"))
                print(f"  [ERR] {name}: anchor occurs {n} times, expected 1")
                continue

            path.write_text(src.replace(old, new))
            code, out = run_tests()
            failed = failed_tests(out)
            red = code != 0 and expect in failed
            path.write_bytes(snapshot)
            assert sha(path) == before, "restore failed mid-battery"

            if red:
                note = ""
            elif code == 0:
                note = "suite stayed GREEN"
            else:
                note = f"failed, but not `{expect}` -- failed: {sorted(failed)[:3]}"
            results.append((name, "RED" if red else "SURVIVED", red, note))
            print(f"  [{'red' if red else 'SURVIVED'}] {name}"
                  f"{'' if red else '  -- ' + note}")
    finally:
        GC.write_bytes(snapshot)
        after = sha(GC)
        if after == before:
            SENTINEL.unlink(missing_ok=True)
        else:                                                 # pragma: no cover
            print(f"⚠️ RESTORE FAILED: {after} != {before}; sentinel KEPT")

    arms = [r for r in results if r[0] != "POSITIVE CONTROL (no mutation)"]
    red = sum(1 for r in arms if r[2])
    control_ok = all(r[2] for r in results if r[0].startswith("POSITIVE"))
    print("\n" + "=" * 70)
    print(f"  {red} of {len(arms)} arms RED; positive control "
          f"{'GREEN' if control_ok else 'FAILED'}")
    print(f"  restore verified: {sha(GC)} == {before}")
    print("=" * 70)
    print(f"  judge self-test: {'PASSED' if judge_ok else 'FAILED'}")
    print("=" * 70)
    return 0 if (red == len(arms) and control_ok and judge_ok
                 and sha(GC) == before) else 1


if __name__ == "__main__":
    raise SystemExit(main())
