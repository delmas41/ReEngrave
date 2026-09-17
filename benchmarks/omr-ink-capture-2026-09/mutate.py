#!/usr/bin/env python3
"""MUTATION BATTERY — `staged.capture` and the three questions it asks.

    python3 benchmarks/omr-ink-capture-2026-09/mutate.py
    python3 benchmarks/omr-ink-capture-2026-09/mutate.py --force   # dirty tree

⚠️⚠️ ONE RED ARM IS NOT A BATTERY. Every arm runs and is reported. Measured in
this repo once at five of six surviving behind one that did not, and it
shipped.

⚠️⚠️ A BATTERY OF REFUSAL TESTS CAN PASS BY REFUSING EVERYTHING, so the last
arm is a POSITIVE CONTROL IN THE SAME CLASS: a no-op edit must leave the suite
GREEN. Without it a broken test file reports every arm red and reads as a
perfect score.

⚠️⚠️ IT REFUSES A DIRTY TREE AND LEAVES AN IN-FLIGHT SENTINEL. Both are
paid-for disciplines here: a battery killed mid-arm left its mutation on disk
with the snapshot dying in the dead process, and one run over an uncommitted
change restored from the INDEX and the change under test vanished. The restore
is VERIFIED BY HASH, never assumed.

    A mutation battery must leave the tree as it FOUND it — which is not the
    same as leaving it as GIT has it, AND AN INTERRUPTED BATTERY OBEYS NEITHER.

⚠️ AN ANCHOR THAT OCCURS TWICE MUTATES THE WRONG FUNCTION — the fermata
battery did exactly that silently. Every anchor is checked for EXACTLY ONE
occurrence and an ambiguous one is reported as a BAD ANCHOR, never as a pass.

⚠️ NEVER RUN THIS BESIDE AN A/B ARM THAT READS THE WORKING TREE.
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
CAP = ROOT / "tools/omr/staged/capture.py"
SENTINEL = Path(__file__).resolve().parent / ".mutation-in-flight.json"
TESTS = ["tools/omr/tests/test_staged_capture.py"]

#: (name, file, anchor, replacement, the test that MUST go red)
ARMS = [
    # ── Q1 SHAPE: the `**common` resolution ─────────────────────────────────
    ("kwargs_unpack_is_ignored_so_five_families_lose_their_score", CAP,
     "            if kw.arg is None:\n"
     "                if isinstance(kw.value, ast.Name):",
     "            if kw.arg is None:\n"
     "                if False and isinstance(kw.value, ast.Name):",
     "TestTheShapeQuestion::test_a_kwargs_unpack_is_FOLLOWED"),

    ("dict_update_keys_are_dropped_from_the_detail", CAP,
     '                and node.func.attr == "update"',
     '                and node.func.attr == "__never__"',
     "TestTheShapeQuestion::test_dict_update_and_subscript_keys_reach_the_detail"),

    ("everything_reports_as_scored", CAP,
     '        return names, ("score" in names), reader',
     '        return names, True, reader',
     "TestTheShapeQuestion::test_a_scoreless_quantity_is_reported_scoreless"),

    ("loop_bound_quantities_are_not_resolved", CAP,
     "        if isinstance(node, ast.Name):\n"
     "            return list(self._bound[-1].get(node.id, ()))",
     "        if isinstance(node, ast.Name):\n"
     "            return []",
     "TestTheShapeQuestion::test_loop_bound_quantities_are_resolved"),

    # ── Q2 POSITION ─────────────────────────────────────────────────────────
    ("a_family_gets_credit_for_ANY_position_it_reads", CAP,
     "                    if UNSCORED.get(q, (\"\", \"\", None))[0] == STAFF_GRID_POSITION\n"
     "                    and UNSCORED[q][2] == family]",
     "                    if UNSCORED.get(q, (\"\", \"\", None))[0] == STAFF_GRID_POSITION]",
     "TestThePositionQuestion::test_a_family_gets_no_credit_for_ANOTHER_familys_position"),

    ("only_the_LAST_evaluate_rule_for_an_effect_is_read", CAP,
     "        effect_to_rules.setdefault(str(getattr(r, \"effect\", \"\")), []).append(name)",
     "        effect_to_rules[str(getattr(r, \"effect\", \"\"))] = [name]",
     "TestThePositionQuestion::test_both_evaluate_rules_with_one_effect_are_read"),

    ("the_universal_detector_rows_are_not_added", CAP,
     "        if prefixes:\n"
     "            reads += [q for q in UNIVERSAL_DETECTOR_ROWS",
     "        if False and prefixes:\n"
     "            reads += [q for q in UNIVERSAL_DETECTOR_ROWS",
     "TestThePositionQuestion::test_the_exemplar_is_found"),

    ("an_unclassified_scoreless_quantity_is_swallowed", CAP,
     '    rep["unclassified_scoreless"] = [q for q in scoreless if q not in UNSCORED]',
     '    rep["unclassified_scoreless"] = []',
     "TestThePositionQuestion::test_an_UNCLASSIFIED_quantity_IS_reported"),

    ("a_side_off_the_class_name_is_counted_as_a_position", CAP,
     '    rep["side_is_not_a_ruler"] = sorted(\n'
     '        {q for q, v in by_q.items() if set(v["detail"]) & set(_SIDE_KEYS)})',
     '    rep["side_is_not_a_ruler"] = []',
     "TestThePositionQuestion::test_a_side_read_off_the_class_name_is_NOT_a_position"),

    # ── Q3 IMAGE ────────────────────────────────────────────────────────────
    ("a_getattr_image_access_is_invisible", CAP,
     '    attrs |= {c.args[1].value for c in ast.walk(fn)',
     '    attrs |= {c.args[1].value for c in ()',
     "TestTheImageQuestion::test_a_getattr_access_is_seen"),

    ("own_erasure_is_folded_into_plain_intact", CAP,
     '        if "erase_staff_lines" in calls:\n'
     "            variant, why = OWN_ERASURE, \"reads `.image` and erases lines ITSELF\"",
     '        if False:\n'
     "            variant, why = OWN_ERASURE, \"reads `.image` and erases lines ITSELF\"",
     "TestTheImageQuestion::test_own_erasure_is_a_THIRD_raster"),

    ("a_silent_fallback_is_reported_as_plain_erased", CAP,
     "    if fallback:\n"
     '        variant, why = ERASED_ELSE_INTACT, "a silent `no_staff else image`"',
     "    if fallback:\n"
     '        variant, why = ERASED, "a silent `no_staff else image`"',
     "TestTheImageQuestion::test_a_silent_fallback_is_named_as_one"),

    ("the_second_entry_point_of_a_reader_is_dropped", CAP,
     "        found += [_raster_of(*e) for e in READER_RASTER_ALSO.get(m, ())]",
     "        found += []",
     "TestTheImageQuestion::test_one_reader_can_cover_two_rasters_and_both_are_reported"),

    ("an_unfound_function_defaults_to_a_real_variant", CAP,
     '        return {"variant": None, "why": f"{rel}::{fn_name} not found"}',
     '        return {"variant": INTACT, "why": "assumed"}',
     "TestTheImageQuestion::test_an_unfound_function_is_None_and_NEVER_defaulted"),

    # ── the refusals: "cannot tell" must never become an answer ─────────────
    ("an_unresolvable_quantity_is_silently_skipped", CAP,
     "        if not quantities:\n"
     "            self.unresolved.append({",
     "        if not quantities:\n"
     "            return\n"
     "        if False:\n"
     "            self.unresolved.append({",
     "TestTheWalkerOnSyntheticCode::test_an_unresolvable_quantity_is_NAMED_never_dropped"),

    ("a_stale_gap_entry_is_not_reported", CAP,
     "    return sorted(k for k in KNOWN_GAPS if k not in hit)",
     "    return []",
     "TestTheGapInventory::test_unaccounted_and_stale_are_inverse"),

    ("an_unaccounted_finding_is_swallowed", CAP,
     "    return [p for p in problems if _gap_key(p) is None]",
     "    return []",
     "TestTheGapInventory::test_unaccounted_and_stale_are_inverse"),

    ("check_returns_zero_on_a_dead_control", CAP,
     '    dead = [k for k, v in rep["controls"].items() if not v]',
     "    dead = []",
     "TestTheToolIsAliveAtAll::test_check_exits_TWO_on_a_dead_control"),

    # ── POSITIVE CONTROL ────────────────────────────────────────────────────
    ("POSITIVE_CONTROL_a_no_op_edit_must_stay_GREEN", CAP,
     "_HERE = pathlib.Path(__file__).resolve().parent",
     "_HERE = pathlib.Path(__file__).resolve().parent  # no-op",
     None),
]


def _hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(target: str | None) -> bool:
    """True when the suite PASSES (i.e. the arm SURVIVED)."""
    sel = [f"{TESTS[0]}::{target}"] if target else list(TESTS)
    r = subprocess.run([sys.executable, "-m", "pytest", *sel, "-q",
                        "--no-header", "-p", "no:cacheprovider"],
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

    files = {CAP}
    before = {f: _hash(f) for f in files}
    snap = Path(tempfile.mkdtemp(prefix="capture-mutate-"))
    for f in files:
        shutil.copy2(f, snap / f.name)
    SENTINEL.write_text(json.dumps(
        {str(f.relative_to(ROOT)): h for f, h in before.items()}, indent=2))

    print("── BASELINE ──────────────────────────────────────────────────")
    if not run(None):
        for f in files:
            shutil.copy2(snap / f.name, f)
        SENTINEL.unlink(missing_ok=True)
        shutil.rmtree(snap, ignore_errors=True)
        print("⚠️ the baseline is RED; every arm below would be unreadable.",
              file=sys.stderr)
        return 2
    print("   unmutated tree: GREEN\n")

    results = []
    try:
        for name, path, anchor, repl, target in ARMS:
            src = path.read_text()
            n = src.count(anchor)
            if n != 1:
                # ⚠️ AN ERROR, NEVER A PASS. An anchor occurring twice mutates
                # the wrong function and the arm then "survives" for a reason
                # that has nothing to do with the code under test.
                results.append((name, target, f"⚠️ BAD ANCHOR ({n} matches)"))
                continue
            path.write_text(src.replace(anchor, repl))
            try:
                passed = run(target)
            finally:
                path.write_text(src)
            if target is None:
                results.append((name, target,
                                "green (control)" if passed
                                else "⚠️ CONTROL WENT RED"))
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

    print("── ARMS ──────────────────────────────────────────────────────")
    for name, target, verdict in results:
        print(f"  {verdict:<22} {name}")
        print(f"  {'':22} -> {target or '(whole suite)'}")

    bad = [r for r in results if r[2] not in ("red", "green (control)")]
    ok = len(results) - len(bad)
    print(f"\n{ok} of {len(results)} arms as expected; "
          f"restore {'VERIFIED' if restored else '⚠️ FAILED'}")
    if bad:
        print("⚠️ arms that did not behave:", file=sys.stderr)
        for name, target, verdict in bad:
            print(f"   {verdict}  {name} -> {target}", file=sys.stderr)
    return 0 if (not bad and restored) else 1


if __name__ == "__main__":
    sys.exit(main())
