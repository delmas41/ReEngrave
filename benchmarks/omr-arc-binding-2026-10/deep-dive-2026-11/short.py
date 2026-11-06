"""How far the page STROKE runs past the traced curve at each end (the 'arcs stop short' census), per fate (measure only). python3 short.py LEDGER.json"""
import collections
import json
import sys

led = json.load(open(sys.argv[1]))
tot = collections.Counter()
short = collections.Counter()
for r in led["rows"]:
    if r["fate"] == "not_an_arc" or r.get("x_left") is None:
        continue
    sp = r["sp"]
    sl, sr = r.get("stroke_left"), r.get("stroke_right")
    if not sl or not sr:
        tot[(r["fate"], "no_stroke")] += 1
        continue
    el = (r["x_left"] - sl[0]) / sp          # >0: the stroke runs left past the traced end
    er = (sr[0] - r["x_right"]) / sp
    tot[r["fate"]] += 1
    if max(el, er) > 0.5:
        short[(r["fate"], "stroke_runs_0.5sp_past")] += 1
    if max(el, er) > 1.6:
        short[(r["fate"], "stroke_runs_1.6sp_past")] += 1
print("curves with a page stroke:", dict(tot))
print("short:", dict(short))
