"""ROADMAP 2.158 -- fold a `replay_2_158.py` result: notes and bars changed (by off->on kind and reason), and, for Litolff,
the 35 crop bars of out/print/litolff-unread-35 (which come back, with what values).
usage: sum_2_158.py REPLAY.json [INDEX35.json]"""
import collections
import json
import sys

R = json.load(open(sys.argv[1]))
ch = R["changed"]
print("control (off vs stored):", R["control"], "| glyphs", R["glyphs"], "| changed", len(ch))
kinds = collections.Counter()
for g, d in ch.items():
    o, n = d["off"] or {}, d["on"] or {}
    kinds[(o.get("outcome"), o.get("reason"), "->", n.get("outcome"), n.get("reason"), n.get("written"))] += 1
for k, c in kinds.most_common():
    print("  %4d  %s" % (c, k))
cells = collections.Counter("/".join(g.split("/")[1:5]) for g in ch)
print("bars changed:", len(cells))
if len(sys.argv) > 2:
    idx = json.load(open(sys.argv[2]))
    back = 0
    for t in idx:
        c = "%d/%d/%d/%d" % (t["page"], t["system"], t["staff"], t["cell"])
        here = {g: d for g, d in ch.items() if "/".join(g.split("/")[1:5]) == c}
        vals = sorted("%s:%s" % (g.split("/")[-1], (d["on"] or {}).get("written")) for g, d in here.items())
        back += bool(here)
        print("  %2d %-12s was %-12s %s" % (t["n"], c, t["written_1014"], ("BACK " + " ".join(vals)) if here else "-"))
    print("35-bar crops back:", back)
