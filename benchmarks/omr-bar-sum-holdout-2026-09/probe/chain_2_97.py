"""For the single-head unique-landing bars: each note's verdict CHAIN, so the
EVALUATE/INFER history of the bar reads off.
   python3 chain_2_97.py LOG.pickle SHAPE.json [N]"""
import collections
import json
import pickle
import sys

sys.path.insert(0, ".")
from tools.omr.staged import consequences as C  # noqa: E402
from tools.omr.staged import record as R  # noqa: E402
from tools.omr.staged.record import Outcome, Q  # noqa: E402

log = pickle.load(open(sys.argv[1], "rb"))
shape = json.load(open(sys.argv[2]))
N = int(sys.argv[3]) if len(sys.argv) > 3 else 12
kinds = collections.Counter()
shown = 0
for k, s in shape.items():
    if s.get("shape") != "1 head" or s.get("landings") != 1:
        continue
    cell = R.cell(*[int(x) for x in k.split("/")])
    hist = []
    narrowed_chain = None
    changed_before = []
    for v in C._standing(log, cell, Q.DURATION):
        chain = []
        cur = v
        while cur is not None:
            chain.append(cur)
            cur = log._vrd.get(cur.supersedes) if cur.supersedes else None
        chain.reverse()
        desc = [(c.decider.split(":")[-1][:18], c.outcome.value[:3],
                 (c.value or {}).get("beats") if c.value else
                 [x.value.get("beats") for x in c.candidates if isinstance(x.value, dict)])
                for c in chain]
        hist.append((v.subject.glyph, desc))
        if v.outcome is Outcome.NARROWED:
            narrowed_chain = desc
        elif len(chain) > 1 and any(c.decider in ("reconcile_duration",) or c.decider.startswith("infer") for c in chain[1:]):
            changed_before.append(chain[-1].decider)
    kinds[(tuple(sorted(set(changed_before))), s["reasons"][0] if s["reasons"] else None)] += 1
    if shown < N:
        shown += 1
        print(k, "expected", s["expected"])
        for g, d in hist:
            print("    g%d" % g, d)
for kk, v in kinds.most_common():
    print(v, kk)
