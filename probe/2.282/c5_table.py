"""2.282 step 1: the contested pieces per page and kind, from c1_<plate>.json (strokes with an accidental box among their claimants, re-adjudicated base).
KIND (a) accidental vs STEM  = a vertical stroke an accidental box covers that is NOT the accidental's at the end (left to the consumers, or a head's), or contested.
KIND (b) accidental vs HEAD  = a stroke that a head (or ledger) box and an accidental box both cover, however it ended.
(third, reported beside) accidental vs REST ink.
usage: c5_table.py PLATE C1.json PAGES"""
import collections
import json
import re
import sys

plate, path, pages = sys.argv[1], sys.argv[2], {int(x) for x in sys.argv[3].split(",")}
rows = [r for r in json.load(open(path)) if r["page"] in pages]
skip = {"key_signature", "clef", "meter", "leading_column", "barline", "word", "bracket"}
tab = collections.defaultdict(collections.Counter)
boxes_b = collections.defaultdict(set)
ex = collections.defaultdict(list)
for r in rows:
    fams = set(r["fams"])
    if fams & skip:
        continue
    kinds = {re.search(r"kind=(\w+)", c[4] or "") and re.search(r"kind=(\w+)", c[4]).group(1) for c in r["cands"] if c[1] == "accidental"}
    vertical = "vertical" in kinds or any("acc_stem" in (c[4] or "") or "longer_than_an_acc_stem" in (c[4] or "") for c in r["cands"])
    end = "%s/%s" % (r["state"], r["owner"])
    if fams & {"head", "ledger"}:
        tab["(b) accidental vs HEAD"][end] += 1
        boxes_b[r["page"]].add(r["cell"])
        ex["b"].append(r)
    if vertical and (r["state"] in ("refused_claims", "contested") or (r["state"] in ("decided", "merged") and r["owner"] not in ("accidental", None))):
        tab["(a) accidental vs STEM (vertical)"][end] += 1
        ex["a"].append(r)
    if "rest" in fams:
        tab["(rest) accidental vs REST ink"][end] += 1
pp = collections.defaultdict(collections.Counter)
for k, c in tab.items():
    pass
for r in rows:
    pass
for k, c in sorted(tab.items()):
    print(plate, k, "total", sum(c.values()), dict(c.most_common(8)))
for kind in ("a", "b"):
    pc = collections.Counter(r["page"] for r in ex[kind])
    print(plate, "kind", kind, "strokes per page", dict(sorted(pc.items())))
    cc = collections.defaultdict(set)
    for r in ex[kind]:
        cc[r["page"]].add(r["cell"])
    print(plate, "kind", kind, "cells per page", {p: len(v) for p, v in sorted(cc.items())})
