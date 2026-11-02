"""How much of the verdicts' `basis` is the SAME list repeated (ROADMAP 2.249; reads only).

usage: basis_share.py RECORD

Per quantity: verdicts, basis entries, distinct basis lists, entries in the distinct lists -- what interning identical
basis tuples in memory would keep.
"""
import sys, hashlib, collections
import ijson

per_q = collections.defaultdict(lambda: [0, 0, set(), 0])
allh = {}
with open(sys.argv[1], "rb") as fh:
    for v in ijson.items(fh, "record.verdicts.item", use_float=True):
        b = v.get("basis") or []
        h = hashlib.blake2b("\x00".join(b).encode(), digest_size=16).digest()
        r = per_q[v.get("quantity")]
        r[0] += 1; r[1] += len(b)
        if h not in r[2]:
            r[2].add(h); r[3] += len(b)
        allh.setdefault(h, len(b))
tot = sum(r[1] for r in per_q.values())
print(f"all: {sum(r[0] for r in per_q.values())} verdicts, {tot} basis entries, distinct lists {len(allh)} "
      f"holding {sum(allh.values())} entries ({sum(allh.values()) / max(tot, 1):.1%})")
for q, r in sorted(per_q.items(), key=lambda kv: -kv[1][1])[:20]:
    print(f"  {q}: {r[0]} verdicts, {r[1]} entries, {len(r[2])} distinct lists, {r[3]} entries distinct ({r[3] / max(r[1], 1):.1%})")
