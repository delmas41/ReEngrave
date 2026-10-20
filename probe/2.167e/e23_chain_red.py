"""2.167e probe 23: the duplicate-chain rest drops (e11) and the meter-digit rest drops, in red bars or not. usage: e23_chain_red.py"""
import json
import collections

d = "probe/2.167e/data/"
for pl in ("lit", "bra"):
    red = json.load(open(d + "%s_red_rows.json" % pl))
    redcells = {(b["page"], b["system"], b["staff"], b["cell"]) for b in red}
    ch = json.load(open(d + "%s_chain.json" % pl))
    A = json.load(open(d + "%s_all.json" % pl))
    c = collections.Counter()
    for r in ch:
        k = tuple(int(x) for x in r["sub"].split("/")[1:5])
        c[(r["cls"], k in redcells)] += 1
    print(pl, "chain drops (class, in red bar):", dict(c))
    md = collections.Counter()
    for s, g in A.items():
        v = g.get("V", {}).get("rest_is_not_a_rest")
        if v and v[1] == "rest_is_a_meter_digit" and v[2] is True:
            k = tuple(int(x) for x in s.split("/")[1:5])
            md[(g["cls"], k in redcells)] += 1
    print(pl, "refused rest_is_a_meter_digit (class, in red bar):", dict(md))
