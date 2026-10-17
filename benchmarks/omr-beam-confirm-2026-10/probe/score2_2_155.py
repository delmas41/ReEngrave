"""ROADMAP 2.155 tighten -- Sean's 20 answered tiles, base vs the first arm vs the tightened arm, in two conditions.

All `--through adjudicate`. Records (out/2.155/):
  defaults (2.153 rule OFF): base  tiles_{doc}_base   (0d1da8a9; main's merge changed only EVALUATE/INFER, so ADJUDICATE is identical)
                             first tiles_{doc}_edge   (the first rule, 721adf7c)
                             tight t2_{doc}_tight_def (merged tree 205d007c + both guards)
  2.153 rule ON:             base  t2_{doc}_base_r153, tight t2_{doc}_tight_r153 (merged tree + guards); first = Litolff p1/2/10
                             only (litolff_p1_2_10_edge, 721adf7c)
Reads out/print/2.155-review/answers.json (never writes it). Writes out/2.155/score2.json and prints a table + counts.
usage: score2_2_155.py"""
import json
import os
import sys

sys.path.insert(0, "benchmarks/omr-beam-confirm-2026-10/probe")
from score_2_155 import load, reading, verdict  # noqa: E402

D = "out/2.155/"
COND = {
    "defaults": {"base": "tiles_{d}_base", "first": "tiles_{d}_edge", "tight": "t2_{d}_tight_def"},
    "rule_2153_on": {"base": "t2_{d}_base_r153", "first": None, "tight": "t2_{d}_tight_r153"},
}
cache = {}


def rec(name):
    p = D + name + ".record.json"
    if p not in cache:
        cache[p] = load(p) if os.path.exists(p) else None
    return cache[p]


def has(r, g):
    return r is not None and any(o["subject"] == g for o in r["observations"] if o["quantity"] == "glyph_box")


ans = json.load(open("out/print/2.155-review/answers.json"))
out, counts = [], {}
for t in ans["tiles"]:
    row = dict(n=t["n"], doc=t["doc"], role=t["role"], glyph=t["glyph"], sean=t["sean"])
    for c, arms in COND.items():
        for arm, pat in arms.items():
            r = None
            if pat:
                r = rec(pat.format(d=t["doc"]))
            elif c == "rule_2153_on" and arm == "first" and t["doc"] == "litolff":
                r = rec("litolff_p1_2_10_edge")
            if not has(r, t["glyph"]):
                continue
            rd = reading(r, t["glyph"])
            v = verdict(t["sean"], rd)
            row["%s/%s" % (c, arm)] = dict(reading=rd, verdict=v)
            counts.setdefault(c, {}).setdefault(arm, {}).setdefault(v, 0)
            counts[c][arm][v] += 1
    out.append(row)
    cells = []
    for c in COND:
        for arm in ("base", "first", "tight"):
            x = row.get("%s/%s" % (c, arm))
            cells.append("-" if x is None else "%s:%s" % (x["reading"].get("written") if x["reading"]["outcome"] == "decided"
                                                         else x["reading"]["outcome"][:4], x["verdict"][:9]))
    print("%2d %-7s %-16s %-16s | def b/f/t %-22s %-22s %-22s | r153 b/f/t %-22s %-22s %-22s" % (
        (t["n"], t["doc"], t["role"], t["sean"]) + tuple(cells)))
json.dump(dict(rows=out, counts=counts), open(D + "score2.json", "w"), indent=1, default=str)
print(json.dumps(counts, indent=1))
