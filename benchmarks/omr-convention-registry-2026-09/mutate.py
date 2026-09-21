"""MUTATION BATTERY — `tools/omr/conventions.py`.

⚠️⚠️ ONE RED ARM IS NOT A BATTERY. Every arm runs and is reported, and the
POSITIVE CONTROLS are in the same class as the refusal arms, because a
battery made only of refusal arms passes by refusing everything.

⚠️⚠️ IT REFUSES A DIRTY TREE AND LEAVES AN IN-FLIGHT SENTINEL, for the two
reasons this repository has paid for: an interrupted battery leaves its
mutation on disk with the snapshot dead in the killed process, and
`git status` cannot tell it from a real edit; and a battery run over an
uncommitted change restores from the index and the change under test
vanishes. The restore is VERIFIED BY HASH, not assumed.

    python3 benchmarks/omr-convention-registry-2026-09/mutate.py
    python3 benchmarks/omr-convention-registry-2026-09/mutate.py --force
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "tools/omr/conventions.py"
SENTINEL = Path(__file__).resolve().parent / ".mutation-in-flight.json"

TESTS = ["tools/omr/tests/test_conventions.py"]

#: (name, anchor, replacement, the test that MUST go red)
ARMS = [
    # ── the two accessors that REFUSE — the design constraint itself ───────
    ("a_refuted_entry_can_be_read_as_a_rule",
     "        if self.is_refuted:\n            raise RefutedConvention(\n"
     '                f"{self.id} is REFUTED HERE and is not a rule: "',
     "        if False:\n            raise RefutedConvention(\n"
     '                f"{self.id} is REFUTED HERE and is not a rule: "',
     "test_rule_text_refuses_a_refuted_entry"),

    ("refutation_is_read_off_the_FAILED_table_alone_and_status_ignored",
     "        if ident in failed_set or any(s in failed_set for s in sources) \\\n"
     "                or status is Status.REFUTED_HERE:",
     "        if False:",
     "TestARefutedEntryCannotBeReadAsARule"),

    ("a_literature_default_passes_as_a_measurement",
     "        if self.status in (Status.LITERATURE_ONLY, Status.ASSERTED):",
     "        if False:",
     "test_measured_figure_refuses_a_literature_only_entry"),

    ("an_ASSERTED_entry_passes_as_a_measurement",
     "        if self.status in (Status.LITERATURE_ONLY, Status.ASSERTED):",
     "        if self.status in (Status.LITERATURE_ONLY,):",
     "test_measured_figure_refuses_an_asserted_entry"),

    ("a_refuted_entry_is_graded_testable",
     "        if status is Status.UNREADABLE:\n"
     "            grade = Testability.UNGRADED\n"
     "        elif refutation is Refutation.WHOLE_ENTRY:\n"
     "            grade = Testability.REFUTED",
     "        if status is Status.UNREADABLE:\n"
     "            grade = Testability.UNGRADED\n"
     "        elif False:\n"
     "            grade = Testability.REFUTED",
     "test_refuted_entries_are_never_graded_testable"),

    # ── the fallback that must never convert "cannot tell" ────────────────
    ("an_unreadable_status_silently_defaults",
     "            status, note = Status.UNREADABLE, status_raw.strip()",
     "            status, note = Status.ASSERTED, \"\"",
     "test_an_unreadable_status_is_a_finding_and_not_a_default"),

    ("the_status_qualifier_is_discarded",
     "            return Status(word), plain[len(word):].strip(\" —-–.\")",
     "            return Status(word), \"\"",
     "test_a_status_qualifier_is_kept_not_discarded"),

    # ── each finding kind, switched off one at a time ──────────────────────
    ("missing_fields_are_never_reported",
     "            for name in entry.missing_fields:",
     "            for name in ():",
     "test_a_missing_field_is_a_finding"),

    ("a_vanished_source_entry_is_never_reported",
     "            missing = [n for n in range(1, max(nums) + 1) "
     "if n not in set(nums)]",
     "            missing = []",
     "test_a_vanished_source_entry_is_a_finding"),

    # ⚠️ RETARGETED AFTER THE FIRST RUN, and the original was an EQUIVALENT
    # MUTANT rather than a gap: an entry's id IS its first source token, so
    # two entries can only share an id by sharing a source token, and
    # SOURCE CLAIMED TWICE fires on exactly that. The unreachable
    # DUPLICATE ID branch was DELETED rather than tested around — a branch
    # that cannot be reached cannot be wrong, and cannot be right either.
    ("a_source_claimed_by_two_entries_is_never_reported",
     "            if len(ids) > 1:",
     "            if False:",
     "test_a_duplicated_source_tag_is_a_finding"),

    ("a_duplicate_slug_is_never_reported",
     "            if entry.slug in seen_slug:",
     "            if False:",
     "test_a_duplicate_slug_is_a_finding"),

    ("a_drifted_status_count_is_never_reported",
     "        for name, claimed in sorted(self.claimed_status_counts.items()):",
     "        for name, claimed in []:",
     "test_a_drifted_count_is_a_finding"),

    ("a_drifted_category_count_is_never_reported",
     "        for name, claimed in sorted(self.claimed_category_counts.items()):",
     "        for name, claimed in []:",
     "test_a_drifted_category_count_is_a_finding"),

    ("a_half_stated_refutation_is_never_reported",
     "        for ident in sorted(table - status_refuted):",
     "        for ident in ():",
     "test_a_half_stated_refutation_is_a_finding"),

    ("a_broken_anchor_is_never_reported",
     "        for anchor in self.anchors_referenced:",
     "        for anchor in ():",
     "test_a_broken_anchor_is_a_finding"),

    ("a_dangling_citation_is_never_reported",
     "                if ident not in known:",
     "                if False:",
     "test_a_dangling_citation_is_a_finding"),

    ("a_lost_conservation_row_is_never_reported",
     "            if self.conservation_rows and token not in self.conservation_rows:",
     "            if False:",
     "test_a_conservation_row_going_missing_is_a_finding"),

    ("a_misaddressed_refutation_row_is_never_reported",
     "            if by_anchor != by_tag:",
     "            if False:",
     "test_a_misaddressed_refutation_row_is_a_finding"),

    ("a_drifted_contents_count_is_never_reported",
     "        for name, claimed in sorted(self.claimed_contents_counts.items()):",
     "        for name, claimed in []:",
     "test_a_drifted_contents_count_is_a_finding"),

    # ── the DEAD control: a parse that reaches nothing ─────────────────────
    ("a_dead_parse_reports_itself_healthy",
     "        dead = [name for name, value in reg.reach().items() if value == 0]",
     "        dead = []",
     "test_an_empty_document_exits_two"),

    ("the_entry_discriminator_admits_every_H3",
     "        if line.startswith(\"### \") and i + 1 < len(lines) \\\n"
     "                and _ENTRY_TAG.match(lines[i + 1].strip()):",
     "        if line.startswith(\"### \"):",
     "test_the_document_agrees_with_itself"),

    ("the_slug_drops_its_hyphens",
     "    return \"\".join(out).replace(\" \", \"-\")",
     "    return \"\".join(out).replace(\" \", \"\")",
     "test_the_document_agrees_with_itself"),

    # ── POSITIVE CONTROLS, in the same class as the refusal arms ──────────
    ("rule_text_refuses_EVERYTHING",
     "        if self.is_refuted:\n            raise RefutedConvention(\n"
     '                f"{self.id} is REFUTED HERE and is not a rule: "',
     "        if True:\n            raise RefutedConvention(\n"
     '                f"{self.id} is REFUTED HERE and is not a rule: "',
     "test_rule_text_answers_for_a_live_entry"),

    ("problems_reports_NOTHING_ever",
     "    def problems(self) -> List[Problem]:",
     "    def problems(self) -> List[Problem]:\n        return []",
     "test_a_mutated_document_exits_one"),
]


def _hash(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def _purge_bytecode() -> None:
    """⚠️⚠️ WITHOUT THIS THE BATTERY REPORTS A FALSE SURVIVOR, and it did.

    CPython invalidates a `__pycache__` entry on the source's **mtime and
    SIZE**. Two arms of this battery replace a 78-character line with a
    21-character one and a 74-character line with a 17-character one —
    **both deltas are exactly 57**, so the two mutated files are the same
    SIZE, and written inside one mtime tick the second arm imported the
    FIRST arm's bytecode. It ran the wrong mutation, the target test
    passed, and the arm was reported as a SURVIVOR — i.e. as a gap in the
    test suite that does not exist.

    Found because the arm went RED when run by hand and survived inside
    the battery. **A mutation battery must not trust the import system to
    notice that it edited a file.**
    """
    for cache in ROOT.joinpath("tools").rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def run(target: str) -> bool:
    """True when the named test PASSES."""
    _purge_bytecode()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    out = subprocess.run(
        [sys.executable, "-m", "pytest", *TESTS, "-k", target.split("::")[-1],
         "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=ROOT, capture_output=True, text=True, env=env)
    return out.returncode == 0 and " passed" in out.stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="run over a dirty tools/ tree (see the docstring)")
    args = ap.parse_args()

    if SENTINEL.exists():
        print("⚠️⚠️ AN EARLIER BATTERY DID NOT FINISH. Its mutation may still "
              "be on disk and `git status` cannot tell it from a real edit.",
              file=sys.stderr)
        print(SENTINEL.read_text(), file=sys.stderr)
        return 2

    dirty = subprocess.run(["git", "status", "--porcelain", "--", "tools/"],
                           cwd=ROOT, capture_output=True, text=True).stdout
    if dirty.strip() and not args.force:
        print("⚠️ tools/ is dirty. Commit first, or pass --force.",
              file=sys.stderr)
        print(dirty, file=sys.stderr)
        return 2

    before = {MOD: _hash(MOD)}
    snap = Path(tempfile.mkdtemp(prefix="conventions-mutate-"))
    shutil.copy2(MOD, snap / MOD.name)
    SENTINEL.write_text(json.dumps(
        {str(MOD.relative_to(ROOT)): before[MOD]}, indent=2))

    print("── BASELINE ──────────────────────────────────────────────────")
    base_ok = run("TestTheParseReachesTheDocument or "
                  "TestARefutedEntryCannotBeReadAsARule or TestTheCheckGoesRed")
    print(f"  unmutated tree: {'GREEN' if base_ok else '⚠️ RED'}")
    if not base_ok:
        shutil.copy2(snap / MOD.name, MOD)
        SENTINEL.unlink(missing_ok=True)
        print("⚠️ the baseline is red; every arm below would be unreadable.",
              file=sys.stderr)
        return 2

    results = []
    try:
        for name, anchor, repl, target in ARMS:
            src = MOD.read_text()
            n = src.count(anchor)
            if n != 1:
                results.append((name, target, f"⚠️ BAD ANCHOR ({n} matches)"))
                continue
            MOD.write_text(src.replace(anchor, repl))
            passed = run(target)
            MOD.write_text(src)
            results.append((name, target, "survived ⚠️" if passed else "red"))
    finally:
        shutil.copy2(snap / MOD.name, MOD)
        shutil.rmtree(snap, ignore_errors=True)

    restored = {MOD: _hash(MOD)} == before
    SENTINEL.unlink(missing_ok=True)

    print("\n── ARMS ──────────────────────────────────────────────────────")
    for name, target, verdict in results:
        print(f"  {verdict:<24} {name}")
        print(f"  {'':24} -> {target}")

    bad = [r for r in results if r[2] != "red"]
    print(f"\n{len(results) - len(bad)} of {len(results)} arms red.")
    print(f"restore verified by hash: {'YES' if restored else '⚠️ NO'}")
    if bad:
        print("⚠️ A SURVIVOR IS EITHER A TEST GAP OR A MIS-AIMED ARM. Check "
              "the anchor before believing the gap.", file=sys.stderr)
        return 1
    if not restored:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
