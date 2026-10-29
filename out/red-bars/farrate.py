"""farrate.py RECORD PLATE PAGES: of cells that hold a head with |staff position| >= 8, what share are red? vs other cells with heads."""
import json, sys, collections
from tools.omr.staged import lane_report as L
from tools.omr.staged.record_io import load_record
rec, plate, pages = sys.argv[1], sys.argv[2], {int(x) for x in sys.argv[3].split(",")}
res = load_record(rec)
r = res["record"] if "record" in res else res
red = {c["key"]: c for c in json.load(open("out/red-bars/work/%s.cls.json" % plate))}
heads = collections.defaultdict(list)
for o in r["observations"]:
    if o["quantity"] == "notehead_staff_position":
        p = o["subject"].split("/")
        pg = int(p[1])
        if pg in pages:
            heads["/".join(p[1:5])].append(o["value"])
far = {k for k, v in heads.items() if any(abs(x) >= 8.0 for x in v)}
near = set(heads) - far
rf = sum(1 for k in far if k in red); rn = sum(1 for k in near if k in red)
print(plate, "cells with heads", len(heads), "far cells", len(far), "red among far", rf, "(%.1f%%)" % (100.0 * rf / max(1, len(far))), "| near cells", len(near), "red among near", rn, "(%.1f%%)" % (100.0 * rn / max(1, len(near))))
ro = sum(1 for k in far if k in red and red[k]["over"]); print("   far cells that are red-over", ro, "of", len(far))
