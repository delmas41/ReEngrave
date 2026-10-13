"""ROADMAP 2.102: which bare-stem settlements do the 2.102 guards remove?

INFER-only replay of `solve_bare_stem_bar` over one record, twice (the rule
before 2.102, then now), listing every subject settled before and not after
and WHICH guard removed it.

    python3 benchmarks/omr-held-out-2026-10/p102_diff.py REC OUT.json
"""
import json
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-held-out-2026-10")
import p102_solve as P  # noqa: E402
from tools.omr.staged import inferences  # noqa: E402

rec, log = P.load_log(sys.argv[1])
cells = P.cells_with_members(rec)

real = (inferences.bar_has_tuplet, inferences._simultaneous_heads,
        inferences._tuplet_world_lengths)


def run(guards):
    if guards:
        (inferences.bar_has_tuplet, inferences._simultaneous_heads,
         inferences._tuplet_world_lengths) = real
    else:
        inferences.bar_has_tuplet = lambda log, cell: ()
        inferences._simultaneous_heads = lambda log, cell, events: False
        inferences._tuplet_world_lengths = lambda seq, **kw: {}
    out = {}
    for c in cells:
        o = P.settle(log, c)
        out[c] = ({p.subject.to_key(): p.value.get("beats")
                   for p in (o.proposals or [])}, o.decline, o.tuplet_possible)
    return out


before = run(False)
after = run(True)
removed = []
for c in cells:
    b, a = before[c][0], after[c][0]
    for s, v in b.items():
        if s not in a:
            why = after[c][1] or ("tuplet_possible" if after[c][2] else "other")
            removed.append({"cell": c, "subject": s, "beats": v, "why": why})
    for s, v in a.items():
        if s not in b or b[s] != v:
            removed.append({"cell": c, "subject": s, "beats": v, "why": "CHANGED/NEW"})
by = {}
for r in removed:
    by[r["why"]] = by.get(r["why"], 0) + 1
import collections  # noqa: E402
print("   settled AFTER by beats:", dict(collections.Counter(
    v for a in after.values() for v in a[0].values())))
print(sys.argv[1].split("/")[-1], "settled before",
      sum(len(v[0]) for v in before.values()), "after",
      sum(len(v[0]) for v in after.values()), "removed by", by)
json.dump(removed, open(sys.argv[2], "w"), indent=0)
