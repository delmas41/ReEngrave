"""2.174 (manager's question, Sean: "easier to see the beam outside of the staff than inside"): is the beam stroke nearest a head INSIDE the staff
(its centre between the top and bottom line, +-0.5 space) or OUTSIDE? For two groups of heads with an own stem:
  MISS = first-verdict DECIDED quarter `head_and_marks`, a CV or detector stroke in the cell  (the 2.174 population)
  HIT  = first-verdict DECIDED `head_and_marks` EIGHT/SIXTEENTH read from a beam (levels_certain >= 1, beams_by_stem >= 1)
Stroke = the cell stroke whose x-span is nearest the head's centre. usage: inout_2_174.py DOC OUT.json"""
import collections
import glob
import json
import os
import sys

DOC, OUT = sys.argv[1:3]
D = "scratch/slices/" + DOC
res = collections.Counter()
for p in sorted(glob.glob(os.path.join(D, "p*.verdicts.jsonl"))):
    pg = int(os.path.basename(p)[1:3])
    first = {}
    for l in open(p):
        v = json.loads(l)
        if v["quantity"] == "duration" and v.get("decider") == "adjudicate_duration" and v["subject"] not in first:
            first[v["subject"]] = v
    want = {}
    for s, v in first.items():
        d = v.get("detail") or {}
        val = v["value"] if isinstance(v.get("value"), dict) else {}
        if v["outcome"] != "decided" or v.get("reason") != "head_and_marks" or d.get("head_is_open") or not (d.get("stems_attached") or d.get("beam_side")):
            continue
        if val.get("written") == 1.0 and not val.get("dots") and (d.get("cv_beams") or d.get("yolo_beams")):
            want[s] = "miss"
        elif val.get("written") in (0.5, 0.25) and not val.get("dots") and (d.get("levels_certain") or 0) >= 1 and (d.get("beams_by_stem") or 0) >= 1:
            want[s] = "hit"
    cells = {"cell/" + "/".join(s.split("/")[1:5]) for s in want}
    cellbox, strokes, heads, lines = {}, collections.defaultdict(list), {}, {}
    for l in open(os.path.join(D, "p%02d.observations.jsonl" % pg)):
        o = json.loads(l)
        q, s = o["quantity"], o["subject"]
        if q == "staff_lines":
            lines[s] = o["value"]
        elif s in cells and q == "cell_box":
            cellbox[s] = o["value"]
        elif s in cells and q == "beam_stroke":
            strokes[s].append(o)
        elif s in want and q == "glyph_box":
            heads[s] = o
    for s, kind in want.items():
        cell = "cell/" + "/".join(s.split("/")[1:5])
        staff = "staff/" + "/".join(s.split("/")[1:4])
        if s not in heads or cell not in cellbox or staff not in lines or not strokes.get(cell):
            res[kind, "no_geometry"] += 1
            continue
        h = heads[s]
        gb = h["detail"]["bbox_page_px"]
        k = (gb[2] - gb[0]) / float(h["value"][3])
        ox, oy = cellbox[cell][0], cellbox[cell][1]
        hc = h["value"][1] + h["value"][3] / 2.0
        best = min(strokes[cell], key=lambda b: 0 if b["value"][0] <= hc <= b["value"][0] + b["value"][2]
                   else min(abs(b["value"][0] - hc), abs(b["value"][0] + b["value"][2] - hc)))
        yc = oy + (best["value"][1] + best["value"][3] / 2.0) * k
        ln = lines[staff]
        sp = (ln[-1] - ln[0]) / (len(ln) - 1)
        inside = ln[0] - 0.5 * sp <= yc <= ln[-1] + 0.5 * sp
        res[kind, "inside" if inside else "outside"] += 1
out = {"%s/%s" % k: v for k, v in res.items()}
print(DOC, out)
json.dump(out, open(OUT, "w"))
