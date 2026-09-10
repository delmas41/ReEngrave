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


def verdicts(path):
    r = json.load(open(path))["record"]
    return {(v["quantity"], v["subject"]):
            (v["outcome"], json.dumps(v["value"], sort_keys=True))
            for v in r["verdicts"]}


def main(before, after):
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
    main(sys.argv[1], sys.argv[2])
