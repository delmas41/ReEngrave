"""ROADMAP 2.202 cause study: the thickness of the horizontal strokes that span >= 2 stems and sit under a detector BEAM box, per plate (read-only, streams the
gathered ON record). usage: beam_thickness.py ON.record.json OUT.json

Why: `BEAM_MIN_THICKNESS_SP` 0.5 was read off two Litolff pages. This prints the same population for the whole sample of BOTH plates, split by whether the stroke's
centre lies within 0.4 sp of a staff line (the erased raster thins a beam there), so the cut is shown where it was not measured."""
import collections
import json
import sys

import ijson

BASE = 375000
path, out = sys.argv[1], sys.argv[2]
strokes, cls, gs = {}, {}, {}
with open(path, "rb") as f:
    for o in ijson.items(f, "record.observations.item", use_float=True):
        q, s = o["quantity"], o["subject"]
        if not s.startswith("glyph/"):
            continue
        if q == "stroke":
            p = s.split("/")
            d = o["detail"]
            st = d["end_steps_from_top"]
            strokes[("/".join(p[1:5]), int(p[5]) - BASE)] = (o["value"], d["length_spaces"], d["thickness_spaces"], [j for j, _ in d["touches"]], (st[0] + st[1]) / 2.0)
        elif q == "glyph_box" and o["reader"] == "detector":
            cls[s] = o["value"][0]
        elif q == "glyph_strokes":
            gs[s] = o["value"]
under_beam = set()
for sub, lst in gs.items():
    if cls.get(sub) == "beam":
        c = "/".join(sub.split("/")[1:5])
        under_beam.update((c, i) for i in lst)
bins = [0, .1, .2, .3, .4, .5, .6, .7, .8, 1.0, 1.2, 9]
res = {}
for key, sel in (("all_span", None), ("under_beam_box", under_beam)):
    h = {"on_line": collections.Counter(), "off_line": collections.Counter()}
    for (c, i), (kind, ln, th, tch, mid) in strokes.items():
        if kind != "horizontal" or (sel is not None and (c, i) not in sel):
            continue
        nv = sum(1 for j in tch if (c, j) in strokes and strokes[(c, j)][0] == "vertical" and strokes[(c, j)][1] <= 8.0)
        if nv < 2:
            continue
        on = min(abs(mid - k) for k in (0, 2, 4, 6, 8)) <= 0.8
        b = next(k for k in range(len(bins) - 1) if bins[k] <= th < bins[k + 1])
        h["on_line" if on else "off_line"]["%.1f-%.1f" % (bins[b], bins[b + 1])] += 1
    res[key] = {k: dict(sorted(v.items())) for k, v in h.items()}
json.dump(res, open(out, "w"), indent=1)
print(json.dumps(res))
