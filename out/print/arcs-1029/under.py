"""For each refused slur group (clusters 'slur_binds_fewer_than_two_notes'): heads under its x-span (+-0.5u) within 6u of its y, WRITTEN (in file) vs DETECTED only.
usage: under.py PLATE"""
import json, sys, re, collections
from tools.omr.staged import lane_report as L
plate = sys.argv[1]
u = L.PLATES[plate]["unit"]
d = json.load(open("/private/tmp/claude-501/arcs/%s.json" % plate))
gb = json.load(open("/private/tmp/claude-501/arcs/%s.glyphboxes.json" % plate))
xml = open("/private/tmp/claude-501/arcs/%s.musicxml" % plate).read()
written = set(re.findall(r'rg="([^"]+)"', xml))
bypage = collections.defaultdict(list)
for k, v in gb.items():
    if (v["cls"] or "").startswith("notehead"):
        bypage[v["page"]].append((k, v["box"], k in written))
cat = collections.Counter()
for c in d["clusters"]:
    if c["fate"] != "refused:slur_binds_fewer_than_two_notes":
        continue
    x, y, w, h = c["box"]
    cx = y + h / 2
    w_, d_ = 0, 0
    for k, b, wr in bypage[c["page"]]:
        hx, hy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        if x - 0.5 * u <= hx <= x + w + 0.5 * u and abs(hy - cx) <= 6 * u:
            d_ += 1
            w_ += wr
    cat["written>=2" if w_ >= 2 else "detected>=2_written<2" if d_ >= 2 else "detected<2"] += 1
print(plate, dict(cat), "of", sum(cat.values()))
