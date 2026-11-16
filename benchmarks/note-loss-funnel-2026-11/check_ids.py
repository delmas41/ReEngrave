"""2.311 print-check: crops of Sean's boxes (by id) on Brahms p0 for OUR look; random 5 (seed) from a judge json bucket.

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/note-loss-funnel-2026-11/check_ids.py JUDGE.json KIND 'what|why' OUT.png [--n 5]
"""
import argparse
import json
import random
from pathlib import Path

from tools.omr.hand_truth import store

from checksheet import sheet

ap = argparse.ArgumentParser()
ap.add_argument("judge")
ap.add_argument("kind")
ap.add_argument("bucket")
ap.add_argument("out")
ap.add_argument("--n", type=int, default=5)
ap.add_argument("--facts")
a = ap.parse_args()
d = json.load(open(a.judge))
pool = [(i, k) for k, v in d[a.kind]["ex"].items() if k == a.bucket or (a.bucket.endswith("*") and k.startswith(a.bucket[:-1]))
        for i in v]
pick = random.Random(2311).sample(pool, min(a.n, len(pool)))
ids = [i for i, _k in pick]
why = {i: k for i, k in pick}
page = store.load(Path("data/hand-truth/pages/imslp317803/0.json"))
by = {b.id: b for b in page.boxes}
facts = json.load(open(a.facts)) if a.facts else None
items = []
try:
    from judge import ARCS
    pp = {x["id"]: x for x in json.load(open(ARCS))["labels"]}
except OSError:
    pp = {}
for i in ids:
    if i in pp:
        items.append(dict(plate="brahms", page=0, box=pp[i]["shape"]["rect"], label="%s %s %s" % (i, pp[i].get("sub"), why[i])))
    elif i in by:
        items.append(dict(plate="brahms", page=0, box=list(by[i].rect), label="%s %s %s" % (i, by[i].cls, why[i])))
    elif facts and "->" in str(i):          # a written arc: the box spans its two notes
        bs = [facts["glyphs"][k]["box"] for k in str(i).split("->") if k in facts["glyphs"]]
        box = [min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs)]
        items.append(dict(plate="brahms", page=0, box=box, label="%s %s" % (i[-18:], why[i])))
    elif facts and i in facts["glyphs"]:
        g = facts["glyphs"][i]
        items.append(dict(plate="brahms", page=g["page"], box=g["box"], label="%s %s" % (i, why[i])))
sheet(items, a.out, width=420, cols=3, pad_units=(4, 5))
print([(i, why[i]) for i in ids])
