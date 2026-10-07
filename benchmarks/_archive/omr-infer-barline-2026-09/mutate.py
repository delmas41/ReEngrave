"""MUTATION BATTERY — `collapse_duration_to_barline` and its meter guard.

⚠️⚠️ ONE RED ARM IS NOT A BATTERY. Every arm is run and reported, and the
POSITIVE CONTROL IN THE SAME CLASS is here for the reason CLAUDE.md records:
a battery made only of REFUSAL arms can pass by refusing everything, which
proves the guards are reachable and never that anything is admitted.

⚠️⚠️ IT REFUSES A DIRTY TREE, AND IT LEAVES AN IN-FLIGHT SENTINEL. Both are
paid-for disciplines in this repository, not caution:

  * *"A mutation battery must leave the tree as it FOUND it — which is not the
    same as leaving it as GIT has it, AND AN INTERRUPTED BATTERY OBEYS
    NEITHER."* A battery killed mid-arm left its mutation on disk with the
    byte snapshot dying in the dead process, and `git status` showed one
    modified file — indistinguishable from the legitimate edit made minutes
    earlier. What found it was a later probe reporting an impossible zero.
  * A battery run over an uncommitted change restored the file from the index
    and the change under test VANISHED.

So: a sentinel is written before the first arm and removed on a clean exit; a
run that finds one refuses to start and names each file at risk with the hash
it should have. The restore is VERIFIED by hash, not assumed.

    python3 benchmarks/omr-infer-barline-2026-09/mutate.py
    python3 benchmarks/omr-infer-barline-2026-09/mutate.py --force   # dirty tree
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
INF = ROOT / "tools/omr/staged/inferences.py"
SENTINEL = Path(__file__).resolve().parent / ".mutation-in-flight.json"

TESTS = ["tools/omr/tests/test_infer_barline_rule.py"]

#: (name, file, anchor, replacement, the test that MUST go red)
ARMS = [
    # ── the guard that lets the rule exist without reading Q.METER ──────────
    ("the_meter_guard_never_fires", INF,
     "    return any(Q.METER in log.quantities_in_closure(vid) "
     "for vid in verdict_ids)",
     "    return False",
     "TestTheMeterGuard"),

    ("the_guard_reads_the_direct_basis_not_the_closure", INF,
     "    return any(Q.METER in log.quantities_in_closure(vid) "
     "for vid in verdict_ids)",
     "    return any(\n"
     "        any(log.row(b) is not None and log.row(b).quantity == Q.METER\n"
     "            for b in (log.row(vid).basis if log.row(vid) else ()))\n"
     "        for vid in verdict_ids)",
     "test_the_guard_is_provenance_and_not_a_decider_name"),

    ("the_guard_is_not_applied_to_witnesses", INF,
     "        if meter_free_witnesses and _witness_is_meter_derived(log, ids):",
     "        if False:",
     "TestTheMeterGuard"),

    ("the_refusal_counter_is_not_written", INF,
     '            "witnesses_refused_meter_derived": refused_meter_derived,',
     "",
     "test_the_counter_is_written_even_when_it_is_zero"),

    ("the_guard_flag_is_not_reported", INF,
     '            "refuses_meter_derived_witnesses": meter_free_witnesses,',
     '            "refuses_meter_derived_witnesses": True,',
     "test_the_guard_flag_says_whether_it_checked"),

    # ── the three-state endpoint ────────────────────────────────────────────
    ("the_barline_is_derived_from_columns_not_from_events", INF,
     "                endpoints[(st2, ci)] = (follow, not later)",
     "                endpoints[(st2, ci)] = (follow, follow is None)",
     "TestTheEndpointIsAPairAndNotAColumn"),

    ("an_unknown_endpoint_is_treated_as_the_barline", INF,
     "        if not span.runs_to_barline:",
     "        if span.end is not None:",
     # ⚠️ RETARGETED AFTER THE FIRST RUN. Aimed at
     # `test_an_event_in_no_column...` this arm SURVIVED, and it was
     # mis-aimed rather than a gap: there the witnesses run to the barline
     # while the subject's endpoint is unknown, so the WITNESS comparison
     # refuses them and the subject filter never gets a chance to. The
     # fixture that isolates this filter is the one where every staff shares
     # the unknown endpoint, so the witness comparison lets them through.
     "test_two_unknown_endpoints_infer_nothing"),

    ("the_witness_endpoint_is_compared_on_the_column_alone", INF,
     "        if span.endpoints.get((st2, span.k)) != span.endpoint:",
     "        if (span.endpoints.get((st2, span.k)) or (None, None))[0] "
     "!= span.end:",
     # ⚠️ RETARGETED AFTER THE FIRST RUN, and this one was a REAL TEST GAP.
     # `test_a_witness_that_ends_elsewhere...` cannot see it: there the
     # rejected witness ends at a COLUMN, so the column half already differs
     # and comparing on it alone is enough. The discriminating case is a
     # witness whose endpoint is UNKNOWN -- it shares the `None` column with
     # a barline-bound subject and only the pair separates them.
     "test_a_witness_whose_endpoint_is_unknown_is_not_a_witness"),

    # ── the partition between the two rules ─────────────────────────────────
    ("the_column_rule_also_claims_the_barline_population", INF,
     "        if span.end is None:",
     "        if False:",
     "test_the_column_rule_does_not_touch_this_population"),

    # ── the guards both rules share ─────────────────────────────────────────
    ("a_dissenting_witness_no_longer_refuses", INF,
     "    if len(votes) > 1:",
     "    if False:",
     "test_one_dissenter_refuses_the_whole_inference"),

    ("one_witness_is_enough", INF,
     "    if len(groups) < COLUMN_MIN_INDEPENDENT_WITNESSES:",
     "    if False:",
     "test_one_witness_is_not_enough"),

    ("a_length_the_reader_never_admitted_is_taken", INF,
     "    if len(matching) != 1:",
     "    if len(matching) > 1:",
     "test_a_length_the_reader_never_admitted_is_refused"),

    ("the_endpoint_is_not_recorded", INF,
     '            "runs_to_barline": span.runs_to_barline,',
     '            "runs_to_barline": False,',
     "test_it_takes_the_neighbours_length"),

    # ── POSITIVE CONTROL, in the same class as the refusal arms ─────────────
    ("refuse_everything", INF,
     "    if not votes:\n        return None",
     "    return None\n    if not votes:\n        return None",
     "test_it_fires"),
]


def _hash(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def run(target: str) -> bool:
    """True when the named test PASSES."""
    out = subprocess.run(
        [sys.executable, "-m", "pytest", *TESTS, "-k", target.split("::")[-1],
         "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=ROOT, capture_output=True, text=True)
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
        print("Restore the files to the hashes above, delete the sentinel, "
              "then re-run.", file=sys.stderr)
        return 2

    dirty = subprocess.run(["git", "status", "--porcelain", "--", "tools/"],
                           cwd=ROOT, capture_output=True, text=True).stdout
    if dirty.strip() and not args.force:
        print("⚠️ tools/ is dirty. A battery restores from its OWN snapshot, "
              "but an interrupted one leaves you unable to tell its mutation "
              "from your edit. Commit first, or pass --force.", file=sys.stderr)
        print(dirty, file=sys.stderr)
        return 2

    files = {INF}
    before = {f: _hash(f) for f in files}
    snap = Path(tempfile.mkdtemp(prefix="infer-barline-mutate-"))
    for f in files:
        shutil.copy2(f, snap / f.name)
    SENTINEL.write_text(json.dumps(
        {str(f.relative_to(ROOT)): h for f, h in before.items()}, indent=2))

    print("── BASELINE ──────────────────────────────────────────────────")
    base_ok = run("TestItReachesTheBarlinePopulation or TestTheMeterGuard "
                  "or TestTheColumnRuleStillWorks")
    print(f"  unmutated tree: {'GREEN' if base_ok else '⚠️ RED'}")
    if not base_ok:
        for f in files:
            shutil.copy2(snap / f.name, f)
        SENTINEL.unlink(missing_ok=True)
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
            results.append((name, target, "survived ⚠️" if passed else "red"))
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
        print(f"  {'':24} -> {target}")

    bad = [r for r in results if r[2] != "red"]
    print(f"\n{len(results) - len(bad)} of {len(results)} arms red.")
    print(f"restore verified by hash: {'YES' if restored else '⚠️ NO'}")
    if bad:
        print("⚠️ A SURVIVOR IS EITHER A TEST GAP OR A MIS-AIMED ARM. Check "
              "the anchor before believing the gap.", file=sys.stderr)
    return 1 if (bad or not restored) else 0


if __name__ == "__main__":
    raise SystemExit(main())
