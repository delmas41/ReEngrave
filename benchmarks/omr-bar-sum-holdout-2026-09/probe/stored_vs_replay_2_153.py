"""ROADMAP 2.153 -- for Sean's judged NOTE tiles: the value the record STORED (20261014-night / the p0-p3 ink record) against
the value the CURRENT code replays, each scored against Sean's answer. Counts tiles that main's defaults already fixed,
already broke, or left alone. usage: stored_vs_replay_2_153.py SLICE.json TAGS.json DOC"""
import collections
import json
import sys

SL, TG, DOC = sys.argv[1:4]
rec = json.load(open(SL))
tags = json.load(open(TG))["base"]
tiles = {t["glyph"]: t for t in json.load(open("out/2.153/notes.json"))[DOC]}
by = collections.defaultdict(list)
for v in rec["verdicts"]:
    if v["quantity"] == "duration" and v["subject"] in tiles:
        by[v["subject"]].append(v)


def live(ch):
    sup = {v.get("supersedes") for v in ch if v.get("supersedes")}
    l = [v for v in ch if v["id"] not in sup]
    return (l or ch)[-1]


def score(v, beats):
    val = v["value"] if isinstance(v["value"], dict) else {}
    if v["outcome"] == "decided":
        w = val.get("written")
        return "right" if (w is not None and not val.get("is_rest") and abs(w - beats) < 1e-6) else "WRONG"
    if v["outcome"] == "narrowed":
        c = [x.get("value", {}).get("written") for x in (v.get("candidates") or [])]
        return "narrowed_holding" if any(x is not None and abs(x - beats) < 1e-6 for x in c) else "narrowed_NOT"
    return v["outcome"]


tab = collections.Counter()
rows = []
for g, t in tiles.items():
    if g not in by or tags.get(g, {}).get("missing"):
        tab[("no_stored_or_replay", "")] += 1
        continue
    s = score(live(by[g]), t["beats"])
    r = tags[g]
    rr = ("right" if r["right"] else "WRONG") if r["outcome"] == "decided" else (
        ("narrowed_holding" if r["right"] else "narrowed_NOT") if r["outcome"] == "narrowed" else r["outcome"])
    tab[(s, rr)] += 1
    if s != rr:
        rows.append((t["item"], t["n"], t["sean"], s, rr, live(by[g]).get("reason"), r["reason"]))
for k, n in sorted(tab.items(), key=lambda kv: -kv[1]):
    print("%3d stored=%-17s replay=%s" % (n, k[0], k[1]))
for x in rows:
    print("   ", x)
