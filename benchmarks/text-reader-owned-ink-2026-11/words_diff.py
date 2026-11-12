"""ROADMAP 2.304: READ words (direction text the lexicon accepted) OFF vs ON, from two `owned_probe.py` outputs: gained, lost, text changed (each text change is a risk).

    python3 benchmarks/text-reader-owned-ink-2026-11/words_diff.py OFF.probe.json ON.probe.json
"""
import json
import sys
from collections import Counter

off, on = (json.load(open(p)) for p in sys.argv[1:3])


def words(log):
    out = {}
    for pg in log:
        for w in pg["found"]:
            out.setdefault((pg["page"], w["staff"], w["measure"]), []).append(w["text"])
    return out


a, b = words(off), words(on)
n = Counter()
for k in sorted(set(a) | set(b)):
    x, y = sorted(a.get(k, [])), sorted(b.get(k, []))
    if x == y:
        n["same"] += 1
        continue
    kind = "GAINED" if not x else ("LOST" if not y else "TEXT CHANGED")
    n[kind] += 1
    print("%-12s p%s staff %s m%s   OFF %s   ON %s" % (kind, k[0], k[1], k[2], x, y))
print("READ words OFF %d  ON %d | %s" % (sum(len(v) for v in a.values()), sum(len(v) for v in b.values()), dict(n)))
