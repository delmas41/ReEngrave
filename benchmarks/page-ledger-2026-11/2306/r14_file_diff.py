"""2.306 r14: what changed in the written file between two facts files of one gather, by kind, one line (notes by glyph key: gained / lost / value
changed / flag<->beam). Usage: r14_file_diff.py A.facts B.facts"""
import collections
import json
import sys


def bf(h):
    s = h.get("sub") or {}
    return "beam" if s.get("beam") else ("flag" if s.get("flag") else "none")


A, B = (json.load(open(p)) for p in sys.argv[1:3])
c = collections.Counter()
for kind in ("note", "rest"):
    a = {h["rg"]: h for h in A["written"] if h["kind"] == kind}
    b = {h["rg"]: h for h in B["written"] if h["kind"] == kind}
    c[kind + " +"] = len(set(b) - set(a))
    c[kind + " -"] = len(set(a) - set(b))
    for k in set(a) & set(b):
        if a[k].get("type") != b[k].get("type") or len((a[k].get("sub") or {}).get("dot") or []) != len((b[k].get("sub") or {}).get("dot") or []):
            c[kind + " value ~ %s->%s" % (a[k].get("type"), b[k].get("type"))] += 1
        if kind == "note" and bf(a[k]) != bf(b[k]):
            c["note %s->%s" % (bf(a[k]), bf(b[k]))] += 1
print("; ".join("%s %d" % kv for kv in sorted(c.items()) if kv[1]) or "NOTHING CHANGED",
      "| red bars %d -> %d" % (len(A["bars"]["red_not_add_up"]), len(B["bars"]["red_not_add_up"])))
