"""ROADMAP 2.179 -- which new boxes one round dropped / added against another (by page box). usage: n1_round_diff.py A.new_glyphs.json B.new_glyphs.json"""
import json
import sys

a, b = (json.load(open(p)) for p in sys.argv[1:3])


def k(x):
    return tuple(round(v) for v in x["detail"]["bbox_page_px"])


ka, kb = {k(x) for x in a}, {k(x) for x in b}
print("dropped (index in A, placed):", [(i, x["placed"]) for i, x in enumerate(a) if k(x) not in kb])
print("added (index in B, placed):", [(i, x["placed"]) for i, x in enumerate(b) if k(x) not in ka])
