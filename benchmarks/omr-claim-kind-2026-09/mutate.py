"""MUTATION BATTERY — the claim kind, and the guarantees it makes.

⚠️⚠️ ONE RED ARM IS NOT A BATTERY. Every arm runs and is reported, and the
POSITIVE CONTROL IN THE SAME CLASS is here for the reason CLAUDE.md records: a
battery made only of refusal arms can pass by refusing everything.

⚠️⚠️ THIS SUBJECT IS UNUSUALLY EASY TO TEST VACUOUSLY. It is a check of
DECLARATIONS against DECLARATIONS, so an arm that breaks a rule nothing
exercises looks exactly like a rule that holds. Every arm below names the
GUARANTEE it breaks, not the line it edits.

⚠️⚠️ IT REFUSES A DIRTY TREE AND LEAVES AN IN-FLIGHT SENTINEL, both paid-for
disciplines here: a battery killed mid-arm left its mutation on disk with the
snapshot dying in the dead process, and one run over an uncommitted change
restored from the INDEX and the change under test vanished. The restore is
VERIFIED by hash, never assumed — "a mutation battery must leave the tree as it
FOUND it, which is not the same as leaving it as GIT has it."

    python3 benchmarks/omr-claim-kind-2026-09/mutate.py
    python3 benchmarks/omr-claim-kind-2026-09/mutate.py --force   # dirty tree
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / "tools/omr/staged/record.py"
CAPTURE = ROOT / "tools/omr/staged/capture.py"
STORE = ROOT / "tools/omr/positional_store.py"
SENTINEL = Path(__file__).resolve().parent / ".mutation-in-flight.json"

TESTS = ["tools/omr/tests/test_claim_kind.py",
         "tools/omr/tests/test_staged_capture.py"]

#: (name, file, anchor, replacement, the test that MUST go red)
ARMS = [
    # ── the HARD tier: a quantity cannot enter Q without declaring ─────────
    ("the_hard_tier_reports_nothing_however_broken", RECORD,
     '    out = [f"Q.{q} declares no claim kind" for q in sorted(qs - set(CLAIMS))]',
     '    out = []',
     "test_an_undeclared_quantity_is_CAUGHT"),

    ("a_declaration_naming_no_quantity_is_ignored", RECORD,
     '    out += [f"CLAIMS names {q!r}, which is not a member of Q"\n'
     '            for q in sorted(set(CLAIMS) - qs)]',
     '    out += []',
     "test_a_declaration_naming_no_quantity_is_CAUGHT"),

    ("a_misspelled_claim_word_is_accepted", RECORD,
     "        if c not in CLAIM.all():",
     "        if False:",
     "test_a_misspelled_claim_word_is_CAUGHT"),

    # ── the fallback rule: cannot-tell may not become a definite answer ────
    ("claim_of_DEFAULTS_instead_of_raising", RECORD,
     "    try:\n        return CLAIMS[_QNAME[quantity]]\n    except KeyError:",
     "    try:\n        return CLAIMS[_QNAME[quantity]]\n    except KeyError:\n"
     "        return CLAIM.MEASUREMENT\n    if False:",
     "test_an_unknown_quantity_RAISES_rather_than_defaulting"),

    # ── the claim is a property of the QUANTITY, not of the row type ───────
    ("a_verdicts_claim_is_keyed_on_its_being_a_verdict", RECORD,
     "        ⚠️ Derived and not serialised, for the reason `Observation.claim`\n"
     "        gives at length.\n"
     '        """\n'
     "        return claim_of(self.quantity)",
     "        ⚠️ Derived and not serialised, for the reason `Observation.claim`\n"
     "        gives at length.\n"
     '        """\n'
     "        return CLAIM.INTERPRETATION",
     "test_a_verdict_carries_its_quantitys_claim_not_its_row_types"),

    # ── the write site refuses an undeclared quantity ──────────────────────
    ("observe_does_not_ask_for_the_claim_at_the_write", RECORD,
     "        claim_of(quantity)\n        for rid in derived_from:",
     "        for rid in derived_from:",
     "test_observe_REFUSES_an_undeclared_quantity_at_the_write"),

    # ── DERIVED, NOT STORED: every committed record stays byte-identical ───
    ("the_claim_is_serialised_so_every_record_in_the_tree_changes", RECORD,
     '                "score": self.score, "detail": dict(self.detail),\n'
     '                "basis": list(self.basis)}\n'
     "\n"
     "\n"
     "@dataclass(frozen=True)\n"
     "class Abstention:",
     '                "score": self.score, "detail": dict(self.detail),\n'
     '                "claim": self.claim,\n'
     '                "basis": list(self.basis)}\n'
     "\n"
     "\n"
     "@dataclass(frozen=True)\n"
     "class Abstention:",
     "test_to_json_is_unchanged"),

    # ── the two axes are reconciled, never merged and never widened ────────
    ("the_cross_table_constraint_reports_nothing", CAPTURE,
     "        got = record_claim_of(q)\n        if got not in admits:",
     "        got = record_claim_of(q)\n        if False:",
     "test_a_planted_disagreement_is_CAUGHT"),

    ("an_UNSCORED_word_with_no_constraint_passes_silently", CAPTURE,
     "        if admits is None:",
     "        if admits is None and False:",
     "test_an_UNSCORED_word_with_no_constraint_is_CAUGHT"),

    ("the_constraint_is_WIDENED_until_the_disagreement_passes", RECORD,
     '    "relation": (CLAIM.MEASUREMENT, CLAIM.COVERAGE),',
     '    "relation": (CLAIM.MEASUREMENT, CLAIM.COVERAGE,\n'
     "                 CLAIM.IDENTIFICATION),",
     "test_the_disagreement_is_ACCOUNTED_and_not_widened_away"),

    ("the_two_axes_are_MERGED_so_not_a_mark_means_external", RECORD,
     '    "not_a_mark": (CLAIM.EXTERNAL, CLAIM.IDENTIFICATION),',
     '    "not_a_mark": (CLAIM.EXTERNAL,),',
     "test_neither_axis_determines_the_other"),

    ("the_claim_findings_never_reach_capture_check", CAPTURE,
     "    out += claim_consistency()",
     "    out += []",
     "test_the_disagreement_is_ACCOUNTED_and_not_widened_away"),

    ("the_hard_tier_never_reaches_capture_check", CAPTURE,
     '    out += [f"CLAIM-UNDECLARED {p}" for p in record_claims_unaccounted()]',
     "    out += []",
     "test_a_closed_gap_must_LEAVE_the_list"),

    # ── the positional store is a PROJECTION, not a second answer ──────────
    ("the_store_collapses_identity_and_coverage_into_one_word", STORE,
     '    KIND_OVERLAPS: "coverage",',
     '    KIND_OVERLAPS: "identification",',
     "test_the_distinction_that_cost_something_survives_the_mapping"),

    ("the_store_mapping_stops_covering_one_of_its_own_words", STORE,
     '    KIND_DRAWN_AS: "external",',
     "",
     "test_the_mapping_is_total_over_the_stores_own_constants"),

    ("the_store_maps_onto_a_word_that_is_not_in_the_vocabulary", STORE,
     '    KIND_DETECTOR_CLASS: "identification",',
     '    KIND_DETECTOR_CLASS: "detector_argmax",',
     "test_every_mapped_value_is_a_real_claim_word"),

    # ── A-INK-4: a claim kind must never DECIDE anything ───────────────────
    ("a_decision_starts_branching_on_the_claim_kind", ROOT / "tools/omr/staged/export.py",
     "def _place_notes(",
     'def _place_notes(  # noqa  "measurement"\n',
     "test_no_adjudicator_branches_on_a_claim_kind"),

    # ── ⚠️ THE POSITIVE CONTROL, in the same class as the arms above ───────
    #
    # Breaking something the tests SHOULD tolerate must NOT go red. Without
    # it, a battery of refusal arms passes by refusing everything.
    ("POSITIVE_CONTROL_a_comment_change_must_NOT_go_red", RECORD,
     "#: name -> value, so `claim_of` can take either and the two cannot drift."
     if False else
     "#: value -> NAME, so `claim_of` takes either spelling and the two cannot",
     "#: value -> NAME, and this comment has been reworded; nothing behaves",
     "test_hard_tier_is_at_zero"),
]


def _hash(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def run(target: str) -> bool:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", *TESTS, "-q", "--no-header",
         "-p", "no:cacheprovider", "-k", target],
        cwd=ROOT, capture_output=True, text=True)
    return r.returncode == 0


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
        print("⚠️ tools/ is dirty. A battery restores from its OWN snapshot, "
              "but an interrupted one leaves you unable to tell its mutation "
              "from your edit. Commit first, or pass --force.", file=sys.stderr)
        print(dirty, file=sys.stderr)
        return 2

    files = sorted({a[1] for a in ARMS}, key=str)
    before = {f: _hash(f) for f in files}
    snap = Path(tempfile.mkdtemp(prefix="claim-kind-mutate-"))
    for f in files:
        shutil.copy2(f, snap / f.name)
    SENTINEL.write_text(json.dumps(
        {str(f.relative_to(ROOT)): h for f, h in before.items()}, indent=2))

    print("── BASELINE ──────────────────────────────────────────────────")
    base = subprocess.run(
        [sys.executable, "-m", "pytest", *TESTS, "-q", "--no-header",
         "-p", "no:cacheprovider"], cwd=ROOT, capture_output=True, text=True)
    base_ok = base.returncode == 0
    print(f"  unmutated tree: {'GREEN' if base_ok else '⚠️ RED'}  "
          f"{base.stdout.strip().splitlines()[-1] if base.stdout else ''}")
    if not base_ok:
        for f in files:
            shutil.copy2(snap / f.name, f)
        SENTINEL.unlink(missing_ok=True)
        shutil.rmtree(snap, ignore_errors=True)
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
            if name.startswith("POSITIVE_CONTROL"):
                results.append((name, target,
                                "green ✅" if passed else "⚠️ RED (control)"))
            else:
                results.append((name, target,
                                "survived ⚠️" if passed else "red"))
    finally:
        for f in files:
            shutil.copy2(snap / f.name, f)
        shutil.rmtree(snap, ignore_errors=True)

    after = {f: _hash(f) for f in files}
    restored = after == before
    SENTINEL.unlink(missing_ok=True)

    print("\n── ARMS ──────────────────────────────────────────────────────")
    for name, target, verdict in results:
        print(f"  {verdict:<24} {name}")

    bad = [r for r in results
           if (r[2].startswith("survived") or r[2].startswith("⚠️ BAD")
               or r[2].startswith("⚠️ RED"))]
    print(f"\n  {len(results) - len(bad)} of {len(results)} arms behaved")
    print(f"  restore verified: {'YES' if restored else '⚠️ NO'}")
    return 0 if (not bad and restored) else 1


if __name__ == "__main__":
    raise SystemExit(main())
