"""print the x spacing of a run's points and its sp: python3 pts.py SLICEDIR PLATE PAGE ORD"""
import json
import sys

sl, plate, page, ordv = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
for line in open("%s/%s/observations.jsonl" % (sl, plate)):
    if '"page_arc"' not in line:
        continue
    o = json.loads(line)
    if o["subject"] != "page/%d" % page or o["value"] != "run" or o["detail"]["ordinal"] != ordv:
        continue
    d = o["detail"]
    pts = d["points"]
    sp = d["space_page_px"]
    print("sp", sp, "n", len(pts), "ends", d["ends"], "core", d["core_ends"], "src", d.get("src"))
    for a, b in zip(pts, pts[1:]):
        gx = b[0] - a[0]
        if gx > 0.5 * sp:
            print("  gap x %.0f..%.0f  (%.2f sp)  y %.0f -> %.0f" % (a[0], b[0], gx / sp, a[1], b[1]))
    print(" last pts", pts[-6:])
