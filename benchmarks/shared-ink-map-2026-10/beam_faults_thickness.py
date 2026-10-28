"""ROADMAP 2.202b (read-only): the thickness distribution of the horizontal strokes that span >= 2 stems and sit under a detector BEAM box, in the three
readings of `beam_faults_live.py` (old = erased raster, A = erased ink put back, B = A minus the line band at the run's ends), per plate, split by whether
the stroke's centre lies within 0.8 half-spaces (= 0.4 sp) of a staff line. usage: beam_faults_thickness.py LIVE_DIR ON_RECORD_litolff ON_RECORD_brahms OUT.json"""
import collections, json, sys
import ijson
BASE = 375000
import os
live_dir, recs, out = sys.argv[1], sys.argv[2:4], sys.argv[4]
PLATES = os.environ.get("PLATES", "litolff,brahms").split(",")
bins = [0, .1, .2, .3, .4, .45, .5, .55, .6, .7, .8, 1.0, 1.2, 9]
res = {}
for plate, path in zip(("litolff", "brahms"), recs):
    if plate not in PLATES:
        continue
    live = json.load(open("%s/%s.json" % (live_dir, plate)))
    cls, gs = {}, {}
    with open(path, "rb") as f:
        for o in ijson.items(f, "record.observations.item", use_float=True):
            s = o["subject"]
            if not s.startswith("glyph/"):
                continue
            if o["quantity"] == "glyph_box" and o["reader"] == "detector":
                cls[s] = o["value"][0]
            elif o["quantity"] == "glyph_strokes":
                gs[s] = o["value"]
    under = set()
    for sub, lst in gs.items():
        if cls.get(sub) == "beam":
            p = sub.split("/")
            under.update(("/".join(p[1:5]), i) for i in lst)
    h = {a: {"on_line": collections.Counter(), "off_line": collections.Counter()} for a in ("old", "A")}
    moved = []
    for cell, rows in live.items():
        for r in rows:
            if r["kind"] != "horizontal" or r["nv"] < 2 or (cell, r["i"]) not in under:
                continue
            on = min(abs(r["mid"] - k) for k in (0, 2, 4, 6, 8)) <= 0.8
            for a in h:
                b = next(k for k in range(len(bins) - 1) if bins[k] <= r[a] < bins[k + 1])
                h[a]["on_line" if on else "off_line"]["%.2f-%.2f" % (bins[b], bins[b + 1])] += 1
            if r["A"] != r["old"] :
                moved.append((cell, r["i"], on, r["old"], r["A"]))
    n = sum(sum(v.values()) for v in h["old"].values())
    res[plate] = dict(n=n, hist={a: {k: dict(sorted(v.items())) for k, v in d.items()} for a, d in h.items()}, moved=len(moved),
                      moved_rows=[list(m) for m in moved][:400])
    print(plate, n, "moved", len(moved))
    for a in h:
        print(" ", a, {k: dict(sorted(v.items())) for k, v in h[a].items()})
json.dump(res, open(out, "w"))
