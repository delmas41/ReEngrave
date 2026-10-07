"""MUTATION BATTERY — does each guard's test actually reach the guard?

⚠️⚠️ ONE RED ARM IS NOT A BATTERY. This repository shipped a change with five
of six mutations SURVIVING behind one that did not, and the reassurance of the
one red arm is what stopped the search. Every arm below is run and reported.

⚠️ A BATTERY OF REFUSAL TESTS CAN PASS BY REFUSING EVERYTHING, so arm
`refuse_everything` is here as the POSITIVE CONTROL IN THE SAME CLASS: it
makes `_admit` reject every proposal, and the test that must go red for it is
the ACCEPT test, not a refusal test. Without it, a battery of eight refusal
arms proves only that the guards are reachable, never that anything is ever
admitted.

⚠️ IT SNAPSHOTS AND RESTORES FILES ITSELF — it does NOT `git checkout`.
CLAUDE.md records a battery's `git checkout` destroying a concurrently running
A/B arm's working tree and costing that session its first three-arm run. A
copy/restore touches nothing git knows about.

⚠️ AN ANCHOR THAT DOES NOT OCCUR EXACTLY ONCE IS AN ERROR, NOT A SKIP. Two
batteries in this repo have silently mutated the WRONG occurrence of a
repeated line (`Ruling.abstain(` appears twice in `ownership.py`; `for h in
heads` three times in `rhythm.py`) and reported a survivor that was really a
mis-aimed arm.

    python3 benchmarks/omr-infer-stage-2026-09/mutate.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INFER = ROOT / "tools/omr/staged/infer.py"
PIPE = ROOT / "tools/omr/staged/pipeline.py"

TESTS = ["tools/omr/tests/test_infer_stage.py",
         "tools/omr/tests/test_infer_bypass.py"]

#: (name, file, anchor, replacement, the test that MUST go red)
ARMS = [
    ("infer_may_overturn_a_reading", INFER,
     "INFERABLE: Tuple[Outcome, ...] = (Outcome.NARROWED, Outcome.ABSTAINED)",
     "INFERABLE: Tuple[Outcome, ...] = (Outcome.NARROWED, Outcome.ABSTAINED, "
     "Outcome.DECIDED)",
     "TestRule3ItMayNotOverturnAReading"),

    ("infer_may_invent_a_value", INFER,
     "        if not any(_same_value(p.value, v) for v in admitted):",
     "        if False:",
     "TestRule4ItMayNotInventAValue"),

    ("the_label_is_not_stamped", INFER,
     '        "inferred": True,',
     '        "inferred": False,',
     "TestRule5ItSupersedesVisibly"),

    ("is_inferred_always_false", INFER,
     "    return bool(decider) and str(decider).startswith(DECIDER_PREFIX)",
     "    return False",
     "TestRule5ItSupersedesVisibly"),

    ("it_does_not_name_what_it_superseded", INFER,
     "        supersedes=prior.id,",
     "        supersedes=None,",
     "TestRule5ItSupersedesVisibly"),

    ("it_may_run_before_evaluate", INFER,
     "    if evaluated is None:\n        raise NotEvaluated(",
     "    if False:\n        raise NotEvaluated(",
     "TestRule1ItMayNotRunBeforeEvaluate"),

    ("it_may_run_on_an_open_log", INFER,
     "    if not log.frozen:\n        raise LogNotFrozen(",
     "    if False:\n        raise LogNotFrozen(",
     "TestRule2ItMayNotLoosenGather"),

    ("witnesses_are_never_correlated", INFER,
     "        hit = [i for i, g in enumerate(groups) if g & cl]",
     "        hit = []",
     "TestIndependence"),

    ("bypass_writes_a_null_key", PIPE,
     '        **({} if inference_report is None\n'
     '           else {"inference": inference_report.to_json()}),',
     '        "inference": (None if inference_report is None\n'
     '                      else inference_report.to_json()),',
     "TestOffMeansAbsentNotQuiet"),

    # ⚠️ THE POSITIVE CONTROL, IN THE SAME CLASS. Every arm above makes a
    # guard STOP refusing; this one makes it refuse EVERYTHING. The test that
    # must go red is the ACCEPT test -- so a suite that passed by refusing
    # everything would be caught here and nowhere else.
    ("refuse_everything", INFER,
     "    groups = independent_groups(log, p.witnesses) if p.witnesses else ()",
     "    return None\n"
     "    groups = independent_groups(log, p.witnesses) if p.witnesses else ()",
     "test_an_admitted_candidate_lands"),
]


def run(target: str) -> bool:
    """True when the named test PASSES."""
    out = subprocess.run(
        [sys.executable, "-m", "pytest", *TESTS, "-k", target, "-q",
         "--no-header", "-p", "no:cacheprovider"],
        cwd=ROOT, capture_output=True, text=True)
    return out.returncode == 0 and " passed" in out.stdout


def main() -> int:
    snap = Path(tempfile.mkdtemp(prefix="infer-mutate-"))
    for f in {INFER, PIPE}:
        shutil.copy2(f, snap / f.name)

    print("── BASELINE ──────────────────────────────────────────────────")
    base_ok = run("TestRule or TestOffMeansAbsent or TestIndependence "
                  "or test_an_admitted_candidate_lands")
    print(f"  unmutated tree: {'GREEN' if base_ok else '⚠️ RED'}")
    if not base_ok:
        print("⚠️ the baseline is red; every arm below would be unreadable.",
              file=sys.stderr)
        return 2

    results = []
    try:
        for name, path, anchor, repl, target in ARMS:
            src = path.read_text()
            n = src.count(anchor)
            if n != 1:
                results.append((name, target, f"⚠️ BAD ANCHOR ({n} matches)"))
                continue
            path.write_text(src.replace(anchor, repl))
            passed = run(target)
            path.write_text(src)
            results.append((name, target,
                            "survived ⚠️" if passed else "red"))
    finally:
        for f in {INFER, PIPE}:
            shutil.copy2(snap / f.name, f)
        shutil.rmtree(snap, ignore_errors=True)

    print("\n── ARMS ──────────────────────────────────────────────────────")
    for name, target, verdict in results:
        print(f"  {verdict:<24} {name}  ->  {target}")

    bad = [r for r in results if r[2] != "red"]
    print(f"\n{len(results) - len(bad)} of {len(results)} arms red.")
    if bad:
        print("⚠️ A SURVIVOR IS EITHER A TEST GAP OR A MIS-AIMED ARM. Check "
              "the anchor before believing the gap.", file=sys.stderr)
    print("\n(restored; `git status` should show no change to tools/)")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
