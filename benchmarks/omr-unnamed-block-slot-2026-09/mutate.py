#!/usr/bin/env python3
"""Mutation battery for the unnamed-block slot rule and its INFER rule.

⚠️⚠️ THE FOUR RECORDED HAZARDS, ALL PAID FOR BY THIS REPO AND ALL OBEYED HERE:
leave the tree as you FOUND it (not as GIT has it); an INTERRUPTED battery
obeys neither, so the snapshot is on DISK behind a sentinel; refuse a dirty
tree without `--force`; and expect the first run's survivors to be the
battery's OWN faults, a BAD ANCHOR being the commonest.

⚠️ THE POSITIVE CONTROL IS IN THE SAME CLASS AS THE ARMS. Most of what this
rule does is REFUSE -- an interior staff, a block too long, a deficit too
large, a contradicting clef -- and a battery of refusal arms passes by
refusing everything. `positive_control_untouched` and the two arms that break
the rule's ability to PLACE anything are what stop that.

Run:  python3 benchmarks/omr-unnamed-block-slot-2026-09/mutate.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
SENTINEL = pathlib.Path(__file__).resolve().parent / ".mutation-in-flight.json"

IDENT = ROOT / "tools" / "omr" / "staged" / "adjudicators" / "identity.py"
INFS = ROOT / "tools" / "omr" / "staged" / "inferences.py"
TESTS = "tools/omr/tests/test_staged_unnamed_block.py"

#: (name, file, anchor, replacement, detect)
#: `detect` is "tests" (the unit tests must go RED) or "green" (control).
ARMS = [
    ("positive_control_untouched", None, None, None, "green"),

    # ── the ADJUDICATE branch ────────────────────────────────────────────────
    ("the_branch_never_fires", IDENT,
     "        placed = _place_in_family_block(",
     "        placed = None and _place_in_family_block(  # MUTANT",
     "tests"),
    ("the_row_is_not_padded_to_the_staff_count", IDENT,
     "    mine = list(mine[:n]) + [None] * max(0, n - len(mine))",
     "    mine = list(mine)  # MUTANT",
     "tests"),
    ("an_interior_unnamed_staff_is_placed_too", IDENT,
     "    if here < b0:\n        # \u26a0\ufe0f AN INTERIOR UNNAMED STAFF",
     "    if False:  # MUTANT\n        # \u26a0\ufe0f AN INTERIOR UNNAMED STAFF",
     "tests"),
    ("the_deficit_cap_is_removed", IDENT,
     "    if deficit > FAMILY_BLOCK_MAX_DEFICIT:\n        return None",
     "    if False:  # MUTANT\n        return None",
     "tests"),
    ("a_short_block_is_DECIDED_instead_of_narrowed", IDENT,
     "    if deficit == 0:\n        return Ruling(value=int(run[i]), reason=\"family_block\",",
     "    if True:  # MUTANT\n        return Ruling(value=int(run[i]), reason=\"family_block\",",
     "tests"),
    ("the_run_is_not_trimmed_by_the_named_staves", IDENT,
     "    floor = max(taken) if taken else -1",
     "    floor = -1  # MUTANT",
     "tests"),
    ("the_trailing_run_ignores_the_family", IDENT,
     "            (fam is None or families[i - 1] == fam):",
     "            True:  # MUTANT",
     "tests"),
    ("the_block_may_be_longer_than_the_run", IDENT,
     "    if not run or k > len(run):",
     "    if not run:  # MUTANT",
     "tests"),
    ("the_candidates_are_not_bounded_by_the_run", IDENT,
     "    cands = [Candidate(value=int(run[i + j]), support=1.0)",
     "    cands = [Candidate(value=int(run[0] + j), support=1.0)  # MUTANT",
     "tests"),

    # ── the INFER rule ───────────────────────────────────────────────────────
    ("the_last_member_is_collapsed_too", INFS,
     "        for i, m in enumerate(members[:-1]):",
     "        for i, m in enumerate(members):  # MUTANT",
     "tests"),
    ("a_contradicting_clef_is_ignored", INFS,
     "        if conflict is not None:\n            continue",
     "        if False:  # MUTANT\n            continue",
     "tests"),
    ("the_refusal_is_per_member_not_whole_block", INFS,
     "                break\n            witnesses.extend(ids)",
     "                continue  # MUTANT\n            witnesses.extend(ids)",
     "tests"),
    ("a_silent_clef_counts_as_a_contradiction", INFS,
     "            if name is None:\n                continue",
     "            if name is None:\n                conflict = {\"block_index\": i}  # MUTANT\n                break",
     "tests"),
    ("the_rule_reads_a_deficit_it_does_not_claim", INFS,
     "        if len(run) != len(members) + 1:",
     "        if False:  # MUTANT",
     "tests"),
    ("a_staff_disagreeing_with_itself_is_a_witness", INFS,
     "    if len(named) != 1:\n        return None, ()",
     "    if not named:  # MUTANT\n        return None, ()",
     "tests"),
]


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def dirty() -> str:
    return run(["git", "status", "--porcelain"]).stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="run against a dirty tree (you accept the risk)")
    args = ap.parse_args()

    if SENTINEL.exists():
        print("REFUSING: an interrupted battery left a sentinel.")
        print(SENTINEL.read_text())
        print("Restore each file to the hash above, then delete the sentinel.")
        return 2

    d = dirty()
    if d and not args.force:
        print("REFUSING: the tree is dirty. A battery must leave the tree as "
              "it FOUND it, and it cannot tell your edit from its own.\n")
        print(d)
        return 2

    files = sorted({a[1] for a in ARMS if a[1] is not None})
    snapshot_dir = pathlib.Path(tempfile.mkdtemp(prefix="block-battery-"))
    before = {}
    for f in files:
        before[str(f)] = sha(f)
        shutil.copy2(f, snapshot_dir / f.name)
    SENTINEL.write_text(json.dumps(
        {"snapshot_dir": str(snapshot_dir), "sha256": before}, indent=2))

    def restore():
        for f in files:
            shutil.copy2(snapshot_dir / f.name, f)
        for f in files:
            if sha(f) != before[str(f)]:
                raise SystemExit(f"RESTORE FAILED for {f}")

    results = []
    try:
        for name, path, anchor, repl, detect in ARMS:
            if path is None:
                r = run([sys.executable, "-m", "pytest", TESTS, "-q"])
                ok = r.returncode == 0
                results.append((name, "GREEN" if ok else "RED",
                                "positive control: the suite must PASS "
                                "unmutated"))
                if not ok:
                    print(r.stdout[-2000:])
                continue

            src = path.read_text()
            n = src.count(anchor)
            if n != 1:
                results.append((name, "BAD ANCHOR",
                                f"anchor occurs {n} times in {path.name}"))
                continue
            path.write_text(src.replace(anchor, repl))
            try:
                r = run([sys.executable, "-m", "pytest", TESTS, "-q"])
                results.append((name, "RED" if r.returncode != 0 else "SURVIVED",
                                f"{detect} exit={r.returncode}"))
            finally:
                path.write_text(src)
                if sha(path) != before[str(path)]:
                    raise SystemExit(f"inline restore failed for {path}")
    finally:
        restore()
        SENTINEL.unlink(missing_ok=True)
        shutil.rmtree(snapshot_dir, ignore_errors=True)

    print(f"{'arm':<42} {'result':<12} note")
    print("-" * 92)
    for name, result, note in results:
        print(f"{name:<42} {result:<12} {note}")

    survivors = [r for r in results if r[1] in ("SURVIVED", "BAD ANCHOR")]
    control = [r for r in results if r[0].startswith("positive_control")]
    bad_control = [r for r in control if r[1] != "GREEN"]
    print()
    print(f"arms: {len(results)}   survivors/bad anchors: {len(survivors)}")
    if bad_control:
        print("⚠️ POSITIVE CONTROL FAILED — the battery measured its own scope")
    print("tree restored and verified; sentinel removed")
    return 1 if (survivors or bad_control) else 0


if __name__ == "__main__":
    sys.exit(main())
