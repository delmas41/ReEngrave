"""Break the instrument on purpose; assert the suite notices.

⚠️ A TEST THAT HAS NEVER FAILED IS NOT KNOWN TO BE ABLE TO FAIL. This repo has
caught vacuous tests more than once — the margin-label blob test asserted on
label LENGTH, and a single huge glyph is one character, so a block that should
have been rejected still produced a short string and the assertion passed
either way. It was rewritten to assert on staff ASSIGNMENT and run RED before
being believed.

This probe does that mechanically. Each mutation edits `tools/omr/
symbol_ledger.py` in a scratch copy of the tree, runs
`tools/omr/tests/test_symbol_ledger.py` against it, and requires the suite to
go RED. A mutation the suite survives is a hole in the suite, named here.

    python3 benchmarks/omr-symbol-ledger-2026-09/probe/mutate_ledger.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

PROBE = Path(__file__).resolve().parent
ROOT = PROBE.parents[2]
TARGET = Path("tools/omr/symbol_ledger.py")

#: (name, what it breaks, old, new) — and the test each is expected to fell.
MUTATIONS: list[tuple[str, str, str, str]] = [
    (
        "anti_circularity_off",
        "let every key report every attribute "
        "(fells test_an_attribute_is_only_reported_from_a_key_blind_to_it)",
        "    return any(attr in KEY_BLIND_TO.get(k, frozenset()) for k in basis)",
        "    return True",
    ),
    (
        "ord_guesses_across_unequal_counts",
        "positional pairing even when the counts differ "
        "(fells test_ord_abstains_rather_than_guessing)",
        '        out.append(KeyProposal("ord", {}, abstained=True,\n'
        '                               note=f"counts differ {len(truth)} vs {len(pred)}"))',
        '        out.append(KeyProposal("ord",\n'
        '                               {i: i for i in range(min(len(truth), len(pred)))}))',
    ),
    (
        "ambiguity_broken_silently",
        "break a key disagreement to the first proposal instead of recording it "
        "(fells test_disagreeing_keys_produce_an_ambiguity)",
        "        if len(named) > 1:\n            ambiguous.add(i)",
        "        if len(named) > 1:\n            named = {sorted(named)[0]: "
        "named[sorted(named)[0]]}\n        if False:\n            ambiguous.add(i)",
    ),
    (
        "cells_from_the_prediction_only",
        "visit only cells the PREDICTION has, so a vanished family reads as "
        "uncorresponded (fells test_a_family_absent_from_the_prediction_is_missing)",
        "    for pj in part_join:\n        if pj.status != \"resolved\":\n"
        "            continue\n        for tp in pj.truth_parts:\n"
        "            for (tpart, tmeas, fam) in truth_by:\n"
        "                if tpart == tp:\n"
        "                    cells.add((pj.pred_part, tmeas, fam))",
        "    pass",
    ),
    (
        "unresolved_join_charged_as_missing",
        "bill an unjoinable staff instead of declining "
        "(fells test_a_wholly_unread_staff_is_uncorresponded_not_charged)",
        '                _row(s, "uncorresponded", reason="part_unresolved",\n'
        '                     measure=tmeasure, measure_map="none")',
        '                _row(s, "spurious", measure=tmeasure, measure_map="none")',
    ),
    (
        "condensed_merge_disabled",
        "stop merging a condensed staff's reference parts "
        "(fells test_a_condensed_staff_merges_its_reference_parts)",
        "    if len(per_part) == 1:",
        "    if True:\n        return [s for x in per_part for s in x]\n    if len(per_part) == 1:",
    ),
    (
        "single_key_basis_not_flagged",
        "call every pairing corroborated "
        "(fells the basis_strength assertion in the second-quarter test)",
        '        strength = "corroborated" if len(basis) > 1 else "single_key"',
        '        strength = "corroborated"',
    ),
]


def run_suite(tree: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest",
         "tools/omr/tests/test_symbol_ledger.py", "-q", "--no-header"],
        cwd=tree, capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def main() -> int:
    # ⚠️ Mutates the file IN PLACE in this worktree and restores it in a
    # `finally`. A scratch copy of just these files does not import (the suite
    # resolves `tools.omr` through the repo's own conftest and package
    # `__init__`s), and a probe that silently tests a DIFFERENT tree than the
    # one shipping is the failure this project keeps meeting. The backup is
    # written beside the file so an interrupted run leaves it recoverable.
    tree = ROOT
    baseline_rc, baseline_out = run_suite(tree)
    print(f"baseline (unmutated): rc={baseline_rc}  "
          f"{baseline_out.strip().splitlines()[-1] if baseline_out.strip() else ''}")
    if baseline_rc != 0:
        print("⚠️ the suite is not green before mutation — nothing below means anything")
        return 2

    original = (tree / TARGET).read_text()
    backup = tree / (str(TARGET) + ".mutate-backup")
    backup.write_text(original)
    survivors: list[str] = []
    try:
      for name, what, old, new in MUTATIONS:
        if old not in original:
            print(f"  {name:<34} ⚠️ ANCHOR NOT FOUND — the probe has rotted "
                  f"against the module")
            survivors.append(f"{name} (anchor missing)")
            continue
        (tree / TARGET).write_text(original.replace(old, new, 1))
        rc, out = run_suite(tree)
        last = out.strip().splitlines()[-1] if out.strip() else ""
        verdict = "RED (good)" if rc != 0 else "SURVIVED — A HOLE IN THE SUITE"
        print(f"  {name:<34} {verdict:<32} {last}")
        print(f"       {what}")
        if rc == 0:
            survivors.append(name)
        (tree / TARGET).write_text(original)
    finally:
        (tree / TARGET).write_text(original)
        backup.unlink(missing_ok=True)
    if survivors:
        print(f"\n{len(survivors)} mutation(s) survived: {survivors}")
        return 1
    print(f"\nall {len(MUTATIONS)} mutations fell the suite.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
