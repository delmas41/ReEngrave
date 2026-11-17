"""ROADMAP 2.313 -- how arm B WROTE the heads arm A refused (type, blue = GUESSED) (reads only).

    python3 benchmarks/landing-check-2026-11/written_as.py PAGES A.facts.json B.facts.json
"""
import collections
import json
import sys

REF = ("duration_narrowed", "chord_value_undecided")
pages = {int(x) for x in sys.argv[1].split(",")}
fa, fb = json.load(open(sys.argv[2])), json.load(open(sys.argv[3]))


def refused(f):
    return {k for k, g in f["glyphs"].items() if len(k.split("/")) == 6 and g.get("head") and g.get("fate") in REF and int(k.split("/")[1]) in pages}


new = refused(fa) - refused(fb)
w = {h["rg"]: h for h in fb["written"] if h.get("rg")}
c = collections.Counter()
for k in new:
    h = w.get(k)
    c[("written", h["type"], "blue" if h["blue"] else "plain") if h else ("not written", fb["glyphs"][k].get("fate"))] += 1
print(len(new), "heads refused in A, not in B; how B wrote them:", c.most_common())
