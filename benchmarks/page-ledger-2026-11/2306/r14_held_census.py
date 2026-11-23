"""2.306 r14: which earlier claim holds a stem the page reader would otherwise take. For every page-stem abstention whose only fitting strokes are
HELD (`no_stroke` with `held` candidates), the owner of the held stroke, by plate; and a sample of glyph keys per owner for a crop look.
Usage: r14_held_census.py REC.json [N_SAMPLE]"""
import collections
import json
import random
import sys

from tools.omr.staged.record_io import load_record

rec = load_record(sys.argv[1])["record"]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 4
heads = {}
for a in rec.get("abstentions") or ():
    if a.get("quantity") != "page_stem":
        continue
    d = a.get("detail") or {}
    if d.get("how") == "no_stroke" and d.get("held"):
        heads.setdefault(d.get("head"), (a["subject"], tuple(sorted({h.get("owner") for h in d["held"]}))))
c = collections.Counter(v[1] for v in heads.values())
print("heads refused because every fitting stroke is held:", len(heads))
by = collections.defaultdict(list)
for hid, (sub, own) in heads.items():
    by[own].append(sub)
random.seed(2306014)
for own, k in c.most_common():
    print(k, own, random.sample(sorted(by[own]), min(n, len(by[own]))))
