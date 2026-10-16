"""ROADMAP 2.153 -- the judged VALUE errors (2.152's tile_rows.json status value_error, plus 2.151 tiles 10/21/28 that Sean
reads as a value the arm narrowed away from) grouped by document -> out/2.153/targets.json; prints the (page,system) sets."""
import json

r = json.load(open("benchmarks/gather-zoom-layers-2026-10/probe/out/tile_rows.json"))
v = [x for x in r if x["status"] == "value_error" or (x["item"] == "2.151" and x["n"] in (10, 21, 28))]
t = {}
for x in v:
    t.setdefault(x["doc"], []).append(dict(item=x["item"], n=x["n"], glyph=x["glyph"], sean=x["sean"]))
json.dump(t, open("out/2.153/targets.json", "w"), indent=0)
print(len(v))
for d, l in t.items():
    print(d, len(l), ";".join(sorted({",".join(g["glyph"].split("/")[1:3]) for g in l})))
