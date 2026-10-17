"""ROADMAP 2.153b -- record Sean's 25 tile answers (2026-10-17) and score each tile OFF vs ON against the hidden key.
Writes out/print/2.153b-review/answers.json (judged-index format, as 2.153's) and names each tile's glyph in manifest.json.
usage: score_2_153b.py"""
import collections
import json
import sys

sys.path.insert(0, ".")
from tools.omr.staged import judged  # noqa: E402

VERBATIM = ("Set F - 1.8 2.8 3.dot 4 4.8 5.dot 8 6.8 7.8  8-10.8 11.16 12-15.8 16.dot 8 17.8 18.dot 4 19-20.8 21.4 "
            "22-23.8 24.4 25.dot 4")
ANS = {1: "8", 2: "8", 3: "dot 4", 4: "8", 5: "dot 8", 6: "8", 7: "8", 8: "8", 9: "8", 10: "8", 11: "16", 12: "8",
       13: "8", 14: "8", 15: "8", 16: "dot 8", 17: "8", 18: "dot 4", 19: "8", 20: "8", 21: "4", 22: "8", 23: "8",
       24: "4", 25: "dot 4"}
KEY = json.load(open("out/2.153b/tiles-key.json"))
assert sorted(ANS) == [r["n"] for r in KEY]


def vs(b, want):
    if b["outcome"] == "decided":
        return "right" if abs(b["beats"] - want) < 1e-6 else "wrong"
    if b["outcome"] == "narrowed":
        return "narrowed-holding" if any(abs(c - want) < 1e-6 for c in b["cands"] or ()) else "narrowed-not"
    return "abstained"


def kind(r):
    o, n = r["off"], r["on"]
    if r["role"] != "changed":
        return "control"
    if o["outcome"] == "decided" and n["outcome"] != "decided":
        return "decided -> narrowed"
    if o["outcome"] == "decided":
        return "value moved"
    return "narrowed -> decided"


tiles, tab = [], collections.Counter()
for r in KEY:
    k, want = judged.parse_answer(ANS[r["n"]])
    assert k == "duration", (r["n"], ANS[r["n"]])
    t = dict(n=r["n"], doc=r["doc"], glyph=r["glyph"], role=r["role"], kind=kind(r), sean=ANS[r["n"]], value=want,
             off=r["off"], on=r["on"], off_verdict=vs(r["off"], want), on_verdict=vs(r["on"], want))
    tiles.append(t)
    tab[(t["doc"], t["kind"], "%s -> %s" % (t["off_verdict"], t["on_verdict"]))] += 1
json.dump(dict(answered="2026-10-17", verbatim=VERBATIM,
               question="What is the written value of the note in the blue box (4, dotted 4, 8 ...)?", tiles=tiles),
          open("out/print/2.153b-review/answers.json", "w"), indent=1)
m = json.load(open("out/print/2.153b-review/manifest.json"))
m["tiles"] = [dict(n=r["n"], doc=r["doc"], glyph=r["glyph"]) for r in KEY]
json.dump(m, open("out/print/2.153b-review/manifest.json", "w"), indent=1)
for k, n in sorted(tab.items()):
    print("%-8s %-22s %-40s %d" % (k[0], k[1], k[2], n))
for t in tiles:
    f = lambda b: ("%g" % b["beats"]) if b["outcome"] == "decided" else "nar%s" % b["cands"]
    print(t["n"], t["doc"], t["kind"], "sean", t["value"], "off", f(t["off"]), t["off_verdict"], "| on", f(t["on"]),
          t["on_verdict"], t["on"]["reason"])
