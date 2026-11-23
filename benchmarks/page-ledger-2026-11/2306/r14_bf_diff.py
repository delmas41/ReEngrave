"""2.306 r14: written notes whose flag/beam differs between two facts files (same glyph key). Usage: r14_bf_diff.py A.facts B.facts"""
import json
import sys


def bf(h):
    s = h.get("sub") or {}
    return "beam" if s.get("beam") else ("flag" if s.get("flag") else "none")


A, B = (json.load(open(p)) for p in sys.argv[1:3])
a = {h["rg"]: bf(h) for h in A["written"] if h["kind"] == "note"}
b = {h["rg"]: bf(h) for h in B["written"] if h["kind"] == "note"}
d = [(k, a[k], b.get(k)) for k in a if a[k] != b.get(k)]
print(len(d), d)
