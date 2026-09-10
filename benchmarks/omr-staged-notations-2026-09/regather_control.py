"""Did a GATHER change move anything downstream? Two FULL runs, compared.

⚠️ THIS EXISTS BECAUSE THE TWO CHEAPER INSTRUMENTS ARE BOTH BLIND TO IT, and
the duration-reader session established the gap by catching itself about to
report a vacuous pass:

  * `readjudicate.py` rebuilds a `Log` from a SAVED record's observations and
    re-runs ADJUDICATE. It isolates an adjudicator change over a FIXED gather
    -- and is **blind by construction to any gather change**, because new
    rows, new fields and changed frames never enter the rebuild. Run against a
    gather change it passes BY CONSTRUCTION and proves nothing.
  * `reexport_arm.py` re-exports one saved record under two trees. It isolates
    an EXPORT change -- and has the mirror-image blind spot.

The uncovered middle is exactly *"did GATHER change what ADJUDICATE sees"*,
and the only instrument for it is two full re-gathers of the same page. That
is expensive (~80 s/page here) and it is the only thing that can go red.

⚠️ It doubles as a DETERMINISM control: detection confidences have been
measured moving between runs on byte-identical code, so a quantity that comes
back identical across two full runs is evidence the delta is attributable.

⚠️⚠️ **AND THE BOUNDARY OF THAT CLAIM IS NARROWER THAN IT READS. DO NOT QUOTE
THIS AS "THE PIPELINE IS DETERMINISTIC".** What two identical runs show is that
the STAGED path is reproducible run-to-run ON THE PAGE MEASURED. It does NOT
contradict, and says nothing about, two measured facts at other layers:

  * DETECTOR confidences move between runs on byte-identical code -- the
    hairpin work measured 0.83 -> 0.69 on one box (`omr-hairpins-2026-09`
    FINDINGS §6), which is why a from-scratch rebuild there reproduced the
    categorical result and NOT the pooled edit count;
  * the legacy scan gate has a **±6 edit** noise floor on the 20-row era
    (`omr-merge-verification-2026-09`), so a per-row delta smaller than that
    is not evidence.

Both are about layers this instrument does not touch. A verdict can be stable
while the confidence underneath it moves, because most decisions read a
confidence as a TIER or an argmax rather than a value -- so identical verdicts
are the weaker claim, and the right one to make.

⚠️ Two independent observations of the staged path's run-to-run stability
exist, on different documents and run for different reasons: this one (24
quantities, Beethoven 5 / Litolff p3, across the page-box fields), and the
duration-reader session's engraved Beethoven 5 iv fixture, whose bar sums came
back identical bar-for-bar and count-for-count (14 assessable, 10 correct,
same staff tallies) across an `origin/main` merge. Theirs is quoted here, not
reproduced here.

    python3 regather_control.py BEFORE.json AFTER.json
"""
import json
import sys


def verdicts(doc):
    return {(v["quantity"], v["subject"]):
            (v["outcome"], json.dumps(v["value"], sort_keys=True))
            for v in doc["record"]["verdicts"]}


def check_provenance(before, after, allow_unstamped=False):
    """⚠️ REFUSE AN UNPROVENANCED A/B — exit non-zero rather than report one.

    "MOVED: nothing" reads as *my change is inert*. It is equally consistent
    with having compared two runs of the SAME tree, or a file with itself, and
    NOTHING in the output would say so. That is the cached-arm trap the
    meter session found in its own `run_arms.py`; this is the same shape one
    layer down, and it was live here until the records carried a stamp.

    ⚠️ A DIRTY TREE IS NEVER EQUAL TO ITSELF: a SHA cannot tell two sets of
    uncommitted edits apart, so two dirty stamps prove neither sameness nor
    difference and are refused. Rule adopted from the meter session.
    """
    pa = before.get("provenance") or {}
    pb = after.get("provenance") or {}
    print(f"BEFORE tree: {pa.get('commit') or '(unstamped)'}"
          f"{'  ⚠️ DIRTY' if pa.get('dirty') else ''}")
    print(f"AFTER  tree: {pb.get('commit') or '(unstamped)'}"
          f"{'  ⚠️ DIRTY' if pb.get('dirty') else ''}")
    problems = []
    if not pa.get("commit") or not pb.get("commit"):
        problems.append(
            "one or both records carry no provenance -- they predate the "
            "stamp, or were written by something that does not set it")
    elif pa["commit"] == pb["commit"] and not (pa.get("dirty") or pb.get("dirty")):
        problems.append(
            f"both records were built from the SAME clean tree "
            f"({pa['commit'][:12]}): this comparison cannot show a code "
            f"change and 'MOVED: nothing' would mean nothing")
    if pa.get("dirty") or pb.get("dirty"):
        problems.append(
            "a DIRTY tree is never equal to itself -- a SHA cannot tell two "
            "sets of uncommitted edits apart, so this pair proves neither "
            "sameness nor difference")
    if not problems:
        return
    for p in problems:
        print(f"⚠️ REFUSED: {p}", file=sys.stderr)
    if allow_unstamped:
        print("⚠️ --allow-unstamped: continuing anyway. The result below is "
              "NOT evidence about a code change.", file=sys.stderr)
        return
    print("Re-run with distinct committed trees, or pass --allow-unstamped "
          "if you know what this pair is and why.", file=sys.stderr)
    raise SystemExit(2)


def main(before_path, after_path, allow_unstamped=False):
    before = json.load(open(before_path))
    after = json.load(open(after_path))
    check_provenance(before, after, allow_unstamped)
    a, b = verdicts(before), verdicts(after)
    qs = {q for q, _ in a} | {q for q, _ in b}
    print("%-24s %7s %7s %8s" % ("quantity", "before", "after", "changed"))
    moved = []
    for q in sorted(qs):
        ka = {k: v for k, v in a.items() if k[0] == q}
        kb = {k: v for k, v in b.items() if k[0] == q}
        n = sum(1 for k in set(ka) | set(kb) if ka.get(k) != kb.get(k))
        if n:
            moved.append(q)
        print("%-24s %7d %7d %8d%s"
              % (q, len(ka), len(kb), n, "  <-- MOVED" if n else ""))
    print()
    print("MOVED:", ", ".join(moved) if moved else "nothing")
    print("⚠️ Every quantity but the one under test must read 0. A quantity "
          "that moves is a finding, not noise.")


if __name__ == "__main__":
    # ⚠️ No pipe in the usage line, deliberately: `| tail` EATS THE EXIT CODE,
    # which this project has been bitten by before and which would make the
    # refusal above look like it worked while returning 0.
    args = [a for a in sys.argv[1:] if a != "--allow-unstamped"]
    main(args[0], args[1], "--allow-unstamped" in sys.argv)
