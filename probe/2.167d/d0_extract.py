"""2.167d probe 0: from a 20261018-night record, pull for each sampled held bar (2.167c sample order) and its two neighbour cells:
cell box, staff lines/spacing, every detector box (class, conf, page bbox, reader) and every verdict on those glyphs.
READ-ONLY. usage: d0_extract.py RECORD SAMPLE.json OUT.json"""
import json
import sys
import time
import collections

rec_path, sample_path, out = sys.argv[1:4]
sample = [tuple(s) for s in json.load(open(sample_path))]
want = set()
for (p, s, st, c) in sample:
    for dc in (-1, 0, 1):
        want.add((p, s, st, c + dc))
staffs = {(p, s, st) for (p, s, st, c) in sample}
t = time.time()


def hook(o):
    if "quantity" in o and "outcome" in o:
        o.pop("considered", None)
        o.pop("correlated", None)
        o.pop("basis", None)
    return o


d = json.loads(open(rec_path).read(), object_hook=hook)
print("loaded", round(time.time() - t), flush=True)
R = d["record"]
obs = R["observations"]
ver = R["verdicts"]


def key(sub):
    p = sub.split("/")
    return tuple(int(x) for x in p[1:5])


cells = {}
geom = {}
G = collections.defaultdict(dict)
for o in obs:
    sub = o["subject"]
    q = o["quantity"]
    if sub.startswith("staff/"):
        k = tuple(int(x) for x in sub.split("/")[1:4])
        if k in staffs:
            geom.setdefault(k, {})[q] = o["value"]
    elif sub.startswith("cell/"):
        k = key(sub)
        if k in want and q == "cell_box":
            cells[k] = o["value"]
    elif sub.startswith("glyph/"):
        k = key(sub)
        if k in want and q == "glyph_box":
            det = o.get("detail") or {}
            G[k][sub] = dict(sub=sub, cls=o["value"][0], conf=o.get("score"), bbox=det.get("bbox_page_px"),
                             cat=det.get("category"), reader=o.get("reader"))
V = collections.defaultdict(list)
for v in ver:
    sub = v.get("subject", "")
    if sub.startswith("glyph/") and key(sub) in want:
        val = v.get("value")
        if isinstance(val, (list, dict)):
            val = str(val)[:80]
        V[sub].append([v["quantity"], v["outcome"], v.get("reason"), val, v.get("decider")])
out_rows = {}
for k in want:
    gl = list(G.get(k, {}).values())
    for g in gl:
        g["verdicts"] = V.get(g["sub"], [])
    out_rows["/".join(map(str, k))] = dict(cell_box=cells.get(k), glyphs=gl)
res = dict(cells=out_rows,
           staff={"/".join(map(str, k)): {"lines": v.get("staff_lines"), "spacing": v.get("staff_spacing"),
                                           "extent": v.get("staff_extent")} for k, v in geom.items()},
           input_domain=[o["value"] for o in obs if o["quantity"] == "input_domain"][:1])
json.dump(res, open(out, "w"))
print("wrote", out, len(out_rows), "cells", sum(len(v["glyphs"]) for v in out_rows.values()), "glyphs", round(time.time() - t))
