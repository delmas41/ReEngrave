"""Cost of a missed clef change: head boxes (detector score >= 0.5, padded-cell copies merged) on that staff
between the change's x and the next printed clef (or the system's end) -- all pitched under the wrong clef.

python3 work-2.251/cost.py PLATE "pg:sys:stafflocal:x0:x1" ...
"""
import json, sys

SL = "library/_shared-records/lane-report-slices-20261029-night"
plate = sys.argv[1]
segs = []
for a in sys.argv[2:]:
    pg, s, st, x0, x1 = (int(v) for v in a.split(":"))
    segs.append((pg, s, st, x0, x1, a))
found = {a: set() for *_, a in segs}
with open(f"{SL}/{plate}/observations.jsonl") as f:
    for line in f:
        if '"glyph_box"' not in line or '"notehead' not in line:
            continue
        r = json.loads(line)
        if r["quantity"] != "glyph_box" or not r["value"][0].startswith("notehead") or (r["score"] or 0) < 0.5:
            continue
        p = r["subject"].split("/")
        pg, s, st = int(p[1]), int(p[2]), int(p[3])
        bb = r["detail"]["bbox_page_px"]
        xc, yc = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
        for (P, S, T, x0, x1, a) in segs:
            if (P, S, T) == (pg, s, st) and x0 <= xc < x1:
                found[a].add((round(xc / 6), round(yc / 6)))
tot = 0
for a, v in found.items():
    print(a, len(v))
    tot += len(v)
print("TOTAL", tot)
