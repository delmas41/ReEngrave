"""2.167d probe 4: MECHANICAL fate census of every notehead/rest-class record box (conf >= 0.25) inside each sampled held bar.
A box is WRITTEN if its glyph id appears in an exporter event of the bar. Otherwise its fate is the exporter fate (noteheads) or, for rests,
the verdicts on it. Prints per-bar lines and totals. usage: d4_boxfates.py lit|bra"""
import collections
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
plate = sys.argv[1]
d = ROOT + "/probe/2.167d/data/"
sample = json.load(open(d + "%s_sample.json" % plate))
rec = json.load(open(d + "%s_rec.json" % plate))
held = json.load(open(d + "%s_held_sample.json" % plate))
out = {}
tot = collections.Counter()
for i, (p, s, st, c) in enumerate(sample):
    key = "%d/%d/%d/%d" % (p, s, st, c)
    h = held[key]
    written = set()
    for e in h["events"]:
        for hh in e.get("heads", []):
            written.add(hh.get("glyph"))
        if e.get("rest"):
            written.add(e["rest"].get("glyph"))
    fates = {b["sub"]: b["fate"] for b in h["boxes"]}
    rows = []
    for g in rec["cells"][key]["glyphs"]:
        cls = g["cls"]
        if not cls.startswith(("notehead", "rest")):
            continue
        v = {q[0]: q[1:4] for q in g["verdicts"]}
        if g["sub"] in written:
            fate = "written"
        elif cls.startswith("notehead"):
            fate = fates.get(g["sub"], "no_fate")
        else:
            r = v.get("rest_is_not_a_rest")
            fate = "rest:" + (str(r[0]) + "/" + str(r[1]) if r else "noverdict")
            dd = v.get("duration")
            if dd:
                fate += " dur=" + str(dd[0]) + "/" + str(dd[1])
        rows.append(dict(sub=g["sub"], cls=cls, conf=round(g["conf"], 2), fate=fate))
        tot[(cls[:4], fate.split(":")[0] if cls.startswith("notehead") else fate)] += 1
    out[key] = rows
    nonw = [r for r in rows if r["fate"] != "written"]
    print(i, key, h["name"], "events", len(h["events"]), "boxes", len(rows), "unwritten", [(r["cls"][:14], r["conf"], r["fate"][:48]) for r in nonw])
json.dump(out, open(d + "%s_boxfates.json" % plate, "w"))
