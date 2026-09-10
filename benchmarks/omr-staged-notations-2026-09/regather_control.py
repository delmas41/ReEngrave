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
