"""ROADMAP 2.153 -- ALL of Sean's judged NOTE tiles (2.152 tile_rows.json, skind == note, a glyph that is a box), by document,
with the (page,system) sets to slice, written to out/2.153/notes.json: {doc: [{item,n,glyph,sean,beats,status}]}.
beats = Sean's written value in quarters (dotted included), parsed with 2.152's own BEATS table."""
import json

BEATS = {"1": 4.0, "2": 2.0, "4": 1.0, "8": 0.5, "16": 0.25, "32": 0.125, "dot 2": 3.0, "dot 4": 1.5, "dot 8": 0.75,
         "dot 16": 0.375, "dot 1": 6.0, "dotted 4": 1.5, "dot2": 3.0, "dot4": 1.5, "dot8": 0.75, "dotted quarter": 1.5}
r = json.load(open("benchmarks/gather-zoom-layers-2026-10/probe/out/tile_rows.json"))
out = {}
for x in r:
    if x.get("skind") != "note" or not x.get("glyph"):
        continue
    b = BEATS.get(str(x["sean"]).strip().lower())
    if b is None:
        continue
    out.setdefault(x["doc"], []).append(dict(item=x["item"], n=x["n"], glyph=x["glyph"], sean=x["sean"], beats=b,
                                              status=x["status"]))
json.dump(out, open("out/2.153/notes.json", "w"), indent=0)
for d, l in out.items():
    print(d, len(l), ";".join(sorted({",".join(g["glyph"].split("/")[1:3]) for g in l})))
