"""ROADMAP 2.304: per candidate (matched by page box), where the accepted reading differs between two `owned_probe.py` outputs, with every text each run's OCR gave.

    python3 benchmarks/text-reader-owned-ink-2026-11/readings_diff.py OFF.probe.json ON.probe.json [PAGE]
"""
import json
import sys
from collections import defaultdict


def per_box(log, only=None):
    out = {}
    for pg in log:
        if only is not None and pg["page"] != only:
            continue
        by = defaultdict(list)
        for r in pg["readings"]:
            by[r["candidate"]].append(r)
        for cd in pg["candidates"]:
            rs = by.get(cd["i"], [])
            out[(pg["page"], cd["staff"], tuple(int(v) for v in cd["box"]))] = dict(
                texts=[r["text"] for r in rs], accepted=sorted({r["accepted"] for r in rs if r["accepted"]}), through=cd.get("through_line"))
    return out


only = int(sys.argv[3]) if len(sys.argv) > 3 else None
a, b = per_box(json.load(open(sys.argv[1])), only), per_box(json.load(open(sys.argv[2])), only)
for k in sorted(set(a) | set(b)):
    x, y = a.get(k), b.get(k)
    if x is None or y is None:
        print("ONLY IN %s: p%s staff %s box %s  accepted %s" % ("OFF" if y is None else "ON", k[0], k[1], k[2], (x or y)["accepted"]))
        continue
    if x["accepted"] != y["accepted"]:
        print("p%s staff %s box %s" % (k[0], k[1], k[2]))
        print("   OFF accepted %s  texts %s" % (x["accepted"], x["texts"][:8]))
        print("   ON  accepted %s  texts %s" % (y["accepted"], y["texts"][:8]))
