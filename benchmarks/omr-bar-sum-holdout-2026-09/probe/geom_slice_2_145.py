"""ROADMAP 2.145 -- stream (ijson) the cell boxes and staff lines of named systems out of a record, for the blind tiles.
usage: geom_slice_2_145.py RECORD OUT.json "p,s;p,s"      STAGED GATHER rows only; decides nothing."""
import json
import sys

import ijson

P, OUT = sys.argv[1], sys.argv[2]
keep = {tuple(int(x) for x in t.split(",")) for t in sys.argv[3].split(";") if t}
out = {"cell_box": {}, "staff_lines": {}}
with open(P, "rb") as f:
    for it in ijson.items(f, "record.observations.item", use_float=True):
        q = it["quantity"]
        if q not in ("cell_box", "staff_lines"):
            continue
        p = it["subject"].split("/")
        if len(p) > 3 and p[1].lstrip("-").isdigit() and p[2].lstrip("-").isdigit() and (int(p[1]), int(p[2])) in keep:
            if q == "cell_box" and p[0] == "cell":
                out["cell_box"]["/".join(p[1:5])] = it["value"]
            elif q == "staff_lines" and p[0] == "staff":
                out["staff_lines"]["/".join(p[1:4])] = it["value"]
print(len(out["cell_box"]), len(out["staff_lines"]))
json.dump(out, open(OUT, "w"))
