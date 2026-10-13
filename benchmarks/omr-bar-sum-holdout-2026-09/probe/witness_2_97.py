"""For the single-head 'short' bars: what does the 2.80 missed-rest witness say?
   python3 witness_2_97.py LOG.pickle WHY.json SHAPE.json"""
import collections
import json
import pickle
import sys

sys.path.insert(0, ".")
from tools.omr.staged import consequences as C  # noqa: E402
from tools.omr.staged import record as R  # noqa: E402

log = pickle.load(open(sys.argv[1], "rb"))
why = json.load(open(sys.argv[2]))
shape = json.load(open(sys.argv[3]))
cnt = collections.Counter()
for k, s in shape.items():
    if s.get("landings") != 1:
        continue
    w = why.get("cell/" + k) or {}
    if w.get("why") != "landings" or w.get("fits_now"):
        continue
    p = [int(x) for x in k.split("/")]
    ans, left = C._missed_rest_witness(log, R.cell(*p))
    cnt[(s["shape"][:12], w["total"] < w["expected"], ans)] += 1
for k, v in sorted(cnt.items(), key=lambda kv: -kv[1]):
    print(v, k)
