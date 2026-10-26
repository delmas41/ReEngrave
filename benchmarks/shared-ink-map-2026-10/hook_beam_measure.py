"""ROADMAP 2.202: the hook-vs-beam measure, off a gathered ON record (read-only; no gather).

usage: hook_beam_measure.py ON.record.json [--out results/2.202/hook_beam_measure.json]

For the strokes `Q.GLYPH_STROKES` lists under (a) every detector BEAM box and (b) every detector FLAG box, takes the horizontal / curve ones and
prints their length, thickness, sagitta and angle by the number of vertical strokes each touches (`touches` -> kind vertical). That is the
population `beam_strokes.py`'s cut-offs are read off. Nothing here is fitted to a target: it prints the distributions and the gap.
"""
import collections
import json
import sys

sys.path.insert(0, ".")
from tools.omr.staged import record_io
from tools.omr.staged.record import STROKE_GLYPH_BASE

path = sys.argv[1]
out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
rec = record_io.load_record(path)["record"]
strokes, gs, gb = {}, {}, {}
for o in rec["observations"]:
    q, s = o["quantity"], o["subject"]
    if q == "stroke":
        p = s.split("/")
        strokes[("/".join(p[1:5]), int(p[5]) - STROKE_GLYPH_BASE)] = o
    elif q == "glyph_strokes":
        gs[s] = o
    elif q == "glyph_box" and o["reader"] == "detector":
        gb[s] = o


def nv(c, i):
    return sum(1 for j, _ in strokes[(c, i)]["detail"]["touches"] if strokes[(c, j)]["value"] == "vertical")


def q(xs, ps=(0, .05, .25, .5, .75, .95, 1)):
    xs = sorted(xs)
    n = len(xs)
    return [round(xs[min(n - 1, int(n * p))], 3) for p in ps] if xs else []


pops = collections.defaultdict(list)
for s, o in gb.items():
    cls = o["value"][0]
    if not (cls == "beam" or cls.startswith("flag")) or s not in gs:
        continue
    c = "/".join(s.split("/")[1:5])
    for i in gs[s]["value"]:
        st = strokes[(c, i)]
        if st["value"] not in ("horizontal", "curve"):
            continue
        d = st["detail"]
        pops["beam" if cls == "beam" else "flag"].append(
            dict(kind=st["value"], nv=nv(c, i), L=d["length_spaces"], T=d["thickness_spaces"], S=d.get("sagitta_spaces") or 0.0, A=abs(d["angle_deg"])))
res = {}
for name, v in pops.items():
    res[name] = {"n": len(v), "kinds": dict(collections.Counter(x["kind"] for x in v)),
                 "by_stems_touched": {}}
    for k in (0, 1, 2):
        sub = [x for x in v if (x["nv"] == k or (k == 2 and x["nv"] > 2))]
        res[name]["by_stems_touched"][str(k) + ("+" if k == 2 else "")] = {
            "n": len(sub), "L": q([x["L"] for x in sub]), "T": q([x["T"] for x in sub]), "S": q([x["S"] for x in sub]), "A": q([x["A"] for x in sub])}
span = [x for x in pops["beam"] if x["nv"] >= 2 and x["kind"] == "horizontal"]
res["thickness_of_spanning_horizontals"] = {
    "n": len(span), "below_0.5": sum(1 for x in span if x["T"] < 0.5), "at_or_above_0.5": sum(1 for x in span if x["T"] >= 0.5),
    "max_below": max([x["T"] for x in span if x["T"] < 0.5] or [0]), "min_above": min([x["T"] for x in span if x["T"] >= 0.5] or [0]),
    "median_above": q([x["T"] for x in span if x["T"] >= 0.5], (.5,))}
res["flag_strokes_one_stem"] = sorted((round(x["L"], 2), round(x["T"], 2), x["kind"], round(x["A"])) for x in pops["flag"] if x["nv"] == 1)
res["beam_box_one_stem_by_length"] = {
    "<=1.6": sum(1 for x in pops["beam"] if x["nv"] == 1 and x["L"] <= 1.6),
    "1.6-2.4": sum(1 for x in pops["beam"] if x["nv"] == 1 and 1.6 < x["L"] <= 2.4),
    ">2.4": sum(1 for x in pops["beam"] if x["nv"] == 1 and x["L"] > 2.4)}
print(json.dumps(res, indent=1))
if out:
    json.dump(res, open(out, "w"), indent=1)
