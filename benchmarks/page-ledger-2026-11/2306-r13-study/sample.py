"""2.306 r13 study: the seeded random samples (seed 2306013), drawn from the trace of ONE gather per plate.
  A   OLD stems, NEW refuses (two-voice heads apart)            30 per plate   (Q2)
  B   NEW stems, OLD names no stem                              20 per plate   (Q4)
  C   both stem, directions differ (or OLD has no direction)    16 per plate   (Q4)
  O   OLD-stemmed head BOXES, from ALL boxes (real or not)      30 per plate   (Q3c)
  V   NEW says two voices                                       10 per plate
Usage: sample.py lit|bra -> scratch r13/<plate>.samples.json"""
import sys, json, random, collections
from common import *
plate = sys.argv[1]
D = load(plate)
T = json.load(open("%s/r13/%s.trace.json" % (S, plate)))
rng = random.Random(2306013)
A = sorted(r["g"] for r in T if r["old_stem"] and r["new_read"] is False and r["new_how"] != "two_voices")
B = sorted(r["g"] for r in T if not r["old_stem"] and r["new_read"])
C = sorted(r["g"] for r in T if r["old_stem"] and r["new_read"] and r["old_dir"] != r["new_dir"])
V = sorted(r["g"] for r in T if r["new_how"] == "two_voices")
allold = sorted(g for g in D["heads"] if ((D["V_off"].get(g) or {}).get("head_stem") or {}).get("o") == "decided")
out = dict(A=rng.sample(A, min(30, len(A))), B=rng.sample(B, min(20, len(B))), C=rng.sample(C, min(16, len(C))), O=rng.sample(allold, 30),
           V=rng.sample(V, min(10, len(V))), sizes=dict(A=len(A), B=len(B), C=len(C), O=len(allold), V=len(V)))
json.dump(out, open("%s/r13/%s.samples.json" % (S, plate), "w"), indent=0)
print(plate, out["sizes"])
