"""interior.py RECORD PLATE PAGES : for EVERY cell, does a staff-tall vertical stroke (a barline) stand inside it?
CV 'vertical' strokes with length_spaces >= 6.5 whose page x lies >= 1.2 sp inside both cell edges. Writes work/PLATE.interior.json {cell_key: n}."""
import json, sys, collections
from tools.omr.staged import lane_report as L
from tools.omr.staged.record_io import load_record
rec, plate, pages = sys.argv[1], sys.argv[2], {int(x) for x in sys.argv[3].split(",")}
u = L.PLATES[plate]["unit"]
res = load_record(rec)
r = res["record"] if "record" in res else res
cb = {}
for o in r["observations"]:
    if o["quantity"] == "cell_box":
        pg = L.page_of(o["subject"])
        if pg in pages:
            cb[o["subject"][5:]] = o["value"]
n = collections.Counter()
lens = []
for o in r["observations"]:
    if o["quantity"] != "stroke" or o["value"] != "vertical":
        continue
    d = o.get("detail") or {}
    s = o["subject"]            # glyph/p/s/st/c/idx
    p = s.split("/")
    if len(p) < 6:
        continue
    key = "/".join(p[1:5])
    box = cb.get(key)
    bp = d.get("bbox_page_px")
    if not box or not bp:
        continue
    L_ = d.get("length_spaces") or 0
    xc = (bp[0] + bp[2]) / 2
    if L_ >= 6.5 and xc > box[0] + 1.2 * u and xc < box[2] - 1.2 * u:
        n[key] += 1
        lens.append(round(L_, 1))
out = {k: n.get(k, 0) for k in cb}
json.dump(out, open("out/red-bars/work/%s.interior.json" % plate, "w"))
print(plate, "cells", len(cb), "with interior barline-like stroke", sum(1 for v in out.values() if v))
