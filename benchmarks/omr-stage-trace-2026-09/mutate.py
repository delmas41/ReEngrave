#!/usr/bin/env python3
"""Mutation battery for `tools/omr/staged/trace.py`.

⚠️ ONE RED ARM IS NOT A BATTERY. Running a single mutation, seeing red and
stopping is the reassurance that hides the rest — measured in this repo at
five of six surviving behind one that did not.

⚠️ A BATTERY OF REFUSAL TESTS CAN PASS BY REFUSING EVERYTHING, so arm
`everything_is_unattributed` is a POSITIVE CONTROL in the same class: it makes
the stage map answer UNATTRIBUTED for every decider, and the arms that assert
a decider RESOLVES must go red on it.

⚠️⚠️ THE MUTATION-BATTERY RULE, ALL THREE CLAUSES, EACH PAID FOR:

    A mutation battery must leave the tree as it FOUND it — which is not the
    same as leaving it as GIT has it, AND AN INTERRUPTED BATTERY OBEYS
    NEITHER.

1. It restores from a BYTE SNAPSHOT taken before the first arm and VERIFIES
   the restore, because `git checkout` restores HEAD and HEAD may not have the
   function under test — a battery once annihilated the change it had just
   certified that way.
2. It writes an IN-FLIGHT SENTINEL before the first arm and deletes it on a
   clean exit. A killed battery leaves the mutation on disk looking exactly
   like a legitimate edit; a later run finds the sentinel, refuses to start,
   and names each file at risk with the hash it should have.
3. It refuses a DIRTY tree without `--force`, because run over an uncommitted
   change it restores from the index and the change vanishes.

⚠️ AND A FOURTH CLAUSE, PAID FOR ON 2026-09-17: `PYTHONDONTWRITEBYTECODE=1`
in every arm. `shutil.copy2` PRESERVES MTIME, so a `.pyc` written by one arm
satisfies Python's `(mtime, size)` staleness check in a later one, which then
imports UNMUTATED code and reports NOT RED — indistinguishable from a test
gap. It took one battery from 10 RED / 2 survived to 12 / 0.

    python3 benchmarks/omr-stage-trace-2026-09/mutate.py
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "tools/omr/staged/trace.py"
TESTS = ROOT / "tools/omr/tests/test_staged_trace.py"
SENTINEL = Path(__file__).resolve().parent / ".mutation-in-flight"

#: `(name, find, replace, the test that MUST go red)`.
#:
#: ⚠️ EVERY ANCHOR IS CHECKED FOR UNIQUENESS BEFORE THE ARM RUNS. The fermata
#: battery silently mutated a DIFFERENT function because its anchor occurred
#: twice, and the part-join battery repeated it; a non-unique anchor is
#: reported as a BAD ANCHOR error rather than as a pass.
ARMS = [
    (
        "stage_map_claims_ADJUDICATE_for_everything",
        "    return \"UNATTRIBUTED\"",
        "    return \"ADJUDICATE\"",
        "test_a_decider_NOBODY_registered_is_UNATTRIBUTED",
    ),
    (
        "infer_is_matched_by_equality_not_by_PREFIX",
        "if decider and str(decider).startswith(INF.DECIDER_PREFIX):",
        "if decider and str(decider) == INF.DECIDER_PREFIX:",
        "test_an_infer_decider_resolves_by_PREFIX",
    ),
    (
        "EXPORT_is_treated_as_a_row_writing_stage",
        '_NOT_ROW_WRITING = frozenset({"EXPORT", "HARNESS"})',
        '_NOT_ROW_WRITING = frozenset({"HARNESS"})',
        "test_the_stages_come_from_reach_and_exclude_the_non_writers",
    ),
    (
        "ablation_claims_every_stage_is_switchable",
        '    out: Dict[str, str] = {\n        "INFER":',
        '    out: Dict[str, str] = {\n        "GATHER": "no", "ADJUDICATE": '
        '"no", "EVALUATE": "no",\n        "INFER":',
        "test_INFER_is_ablatable_and_the_other_stages_are_not",
    ),
    (
        "a_changed_value_is_reported_as_a_restatement",
        '    return "changed_the_value"',
        '    return "restated_same_value"',
        "test_the_five_classes",
    ),
    (
        "a_missing_prior_row_is_GUESSED_instead_of_named",
        '        return "prior_row_absent"',
        '        return "restated_same_value"',
        "test_a_missing_prior_row_is_NAMED_not_guessed",
    ),
    (
        "the_population_drops_the_DETECTOR_route",
        "    if meta[\"detector_prefixes\"]:\n        for o in rec.obs_of(Q.GLYPH_BOX):",
        "    if False:\n        for o in rec.obs_of(Q.GLYPH_BOX):",
        "test_the_population_comes_from_the_DETECTOR_route_for_notes",
    ),
    (
        "an_unknown_family_returns_empty_instead_of_RAISING",
        "        raise KeyError(\n            f\"{family!r} is not a family.",
        "        return {\"family\": family}  # noqa\n        raise KeyError(\n"
        "            f\"{family!r} is not a family.",
        "test_an_unknown_family_RAISES_rather_than_returning_empty",
    ),
    (
        "n_standing_counts_ROWS_so_a_superseded_stage_looks_decisive",
        '        "n_standing": len({r["subject"] for r in standing}),',
        '        "n_standing": len({r["subject"] for r in rows}),',
        "test_n_in_counts_ROWS_and_n_standing_counts_FINAL_answers",
    ),
    (
        "balanced_absorbs_unaccounted_so_it_can_never_fail",
        '    row["balanced"] = (row["decided"] + row["narrowed"] + row["abstained"]\n'
        '                       == row["n_in"])',
        '    row["balanced"] = (row["decided"] + row["narrowed"] + row["abstained"]\n'
        '                       + len(unaccounted) == row["n_in"])',
        "test_an_UNKNOWN_outcome_lands_in_unaccounted_and_UNBALANCES",
    ),
    (
        "no_mask_is_admitted_as_an_ink_claim",
        '    return frozenset(r for r in ABSTAIN.all() if "ink" in r.split("_"))',
        '    return frozenset(r for r in ABSTAIN.all() if "ink" in r or "mask" in r)',
        "test_the_ink_claiming_reason_set_is_DERIVED_and_non_empty",
    ),
    (
        "the_ink_readers_OWN_no_ink_is_counted_against_it",
        "        if quantity == Q.INK:\n            honest_ink_rows += 1",
        "        if False:\n            honest_ink_rows += 1",
        "test_the_INK_READERS_OWN_no_ink_is_EXCLUDED",
    ),
    (
        "a_no_ink_claim_with_NO_witness_is_counted_anyway",
        "        if not wit:\n            continue",
        "        if not wit:\n            wit = [\"assumed\"]",
        "test_a_no_ink_claim_with_NO_witness_is_not_counted",
    ),
    (
        "an_HONEST_no_detections_is_counted_as_a_contradiction",
        "        if reason in _HONEST_EMPTY:",
        "        if False:",
        "test_an_HONEST_empty_claim_is_reported_apart_not_as_a_fault",
    ),
    (
        "the_EXPORT_step_INVENTS_an_answer_instead_of_abstaining",
        '        return {"state": "declined",\n                "reason": "no export report; pass --export',
        '        return {"state": "not_written",\n                "reason": "no export report; pass --export',
        "test_the_EXPORT_step_ABSTAINS_rather_than_re_deriving",
    ),
    (
        "a_record_with_no_record_key_is_read_as_EMPTY",
        '        raise KeyError(\n            f"{path} has no \'record\' key.',
        '        return X.Record({"record": {"observations": [], "verdicts": [],\n'
        '                                    "abstentions": []}})\n'
        '        raise KeyError(\n            f"{path} has no \'record\' key.',
        "test_a_record_with_no_record_key_RAISES",
    ),
    (
        "check_reports_a_finding_BEFORE_testing_its_controls",
        "        zero = [k for k, v in rep[\"controls\"].items() if not v]",
        "        zero = []",
        "test_check_exits_2_when_a_CONTROL_is_at_zero",
    ),
    (
        "the_ancestor_CONTEXT_is_dropped",
        "    for anc in sub.ancestors():",
        "    for anc in ():",
        "test_a_GATHER_abstention_on_an_ANCESTOR_is_not_lost",
    ),
    (
        "a_scoreless_ruler_reading_is_defaulted_to_zero",
        '            "frame": o["frame"], "score": o.get("score"),',
        '            "frame": o["frame"], "score": o.get("score") or 0.0,',
        "test_a_scoreless_ruler_reading_shows_its_absence_not_a_zero",
    ),
    # ⚠️ POSITIVE CONTROL, in the same class as the refusal arms: a battery of
    # "it refuses X" tests can pass by refusing everything.
    (
        "POSITIVE_CONTROL_everything_is_unattributed",
        "    by = deciders_by_stage()\n    for stage, names in by.items():",
        "    by = {}\n    for stage, names in by.items():",
        "test_every_registered_decider_resolves_to_its_own_stage",
    ),
]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _dirty() -> bool:
    out = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain",
                          "--", str(TARGET), str(TESTS)],
                         capture_output=True, text=True)
    return bool(out.stdout.strip())


def _run(test: str) -> bool:
    """True when the named test is RED."""
    env = dict(os.environ)
    # ⚠️ CLAUSE 4. Without this a stale `.pyc` makes an arm import UNMUTATED
    # code and report NOT RED.
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(ROOT)
    r = subprocess.run(
        [sys.executable, "-m", "pytest", str(TESTS), "-q", "-k", test,
         "--no-header", "-p", "no:cacheprovider"],
        capture_output=True, text=True, cwd=str(ROOT), env=env)
    if "no tests ran" in r.stdout or "collected 0 items" in r.stdout:
        raise SystemExit(f"BAD TEST SELECTOR: {test!r} matched nothing")
    return r.returncode != 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="run over a dirty tree (clause 3)")
    args = ap.parse_args()

    if SENTINEL.exists():
        print("⚠️⚠️ AN EARLIER BATTERY WAS INTERRUPTED (clause 2). The tree "
              "may still carry a mutation and `git status` cannot tell it "
              "from a legitimate edit.")
        print(SENTINEL.read_text())
        return 2
    if _dirty() and not args.force:
        print("⚠️ REFUSING: the tree is dirty for one of the files this "
              "battery mutates, and a restore would take the index's copy "
              "(clause 3). Commit a checkpoint, or pass --force.")
        return 2

    snap = Path(tempfile.mkdtemp(prefix="trace-mutate-")) / "trace.py"
    shutil.copy2(TARGET, snap)
    want = _sha(TARGET)
    SENTINEL.write_text(
        f"in flight\n{TARGET} sha256={want}\nsnapshot={snap}\n")
    original = TARGET.read_text()

    print("── the POSITIVE CONTROL first: the suite is GREEN unmutated ──")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(ROOT))
    base = subprocess.run(
        [sys.executable, "-m", "pytest", str(TESTS), "-q", "--no-header",
         "-p", "no:cacheprovider"],
        capture_output=True, text=True, cwd=str(ROOT), env=env)
    if base.returncode != 0:
        SENTINEL.unlink()
        print("⚠️ the suite is ALREADY RED — every arm below would read as a "
              "pass. Fix that first.")
        print(base.stdout[-3000:])
        return 2
    print("   green.\n")

    red, survived, bad = [], [], []
    try:
        for name, find, repl, test in ARMS:
            n = original.count(find)
            if n != 1:
                bad.append((name, f"anchor occurs {n} times, not once"))
                print(f"  BAD ANCHOR  {name}: occurs {n} times")
                continue
            TARGET.write_text(original.replace(find, repl, 1))
            try:
                is_red = _run(test)
            finally:
                TARGET.write_text(original)
            (red if is_red else survived).append((name, test))
            print(f"  {'RED ' if is_red else '⚠️ SURVIVED'}  {name}"
                  f"  -> {test}")
    finally:
        # ⚠️ CLAUSE 1: restore from the BYTE SNAPSHOT and VERIFY it.
        shutil.copy2(snap, TARGET)
        got = _sha(TARGET)
        if got != want:
            print(f"⚠️⚠️ RESTORE FAILED: {got} != {want}. The snapshot is at "
                  f"{snap} — do not commit until this is resolved.")
            return 3
        SENTINEL.unlink(missing_ok=True)

    print(f"\n{len(red)} RED, {len(survived)} survived, {len(bad)} bad anchors"
          f"  (restore verified: {want[:12]})")
    if survived:
        print("\n⚠️ SURVIVORS — each is a real test gap, an EQUIVALENT mutant "
              "to be named and held OUT of the arms, or a mis-aimed arm:")
        for name, test in survived:
            print(f"   {name}  ({test})")
    for name, why in bad:
        print(f"   BAD ANCHOR {name}: {why}")
    return 0 if not survived and not bad else 1


if __name__ == "__main__":
    sys.exit(main())
