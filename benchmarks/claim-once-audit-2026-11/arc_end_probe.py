"""2.283 probe (READ-ONLY): where does an arc's TRACE end relative to the head boxes whose strokes it claims?  usage: arc_end_probe.py SLICE_DIR arc_trace.json
For each head box on an arc-claimed stroke (arc_trace_probe.py output) find the Q.SYSTEM_ARC row(s) whose trace runs through the box's columns and say
whether the trace ENDS inside the head box's x-range (the tail runs into the head), runs THROUGH it (ink on both sides), or only touches an edge."""
import collections
import json
import sys

sl, tj = sys.argv[1], sys.argv[2]
arcs = [x for x in json.load(open(tj)) if x.get("heads")]
pages = sorted({x["page"] for x in arcs})
box, sysarc = {}, []
for line in open(sl + "/observations.jsonl"):
    if '"glyph_box"' not in line[:300] and '"system_arc"' not in line[:300]:
        continue
    o = json.loads(line)
    if o["quantity"] == "glyph_box":
        box[o["subject"]] = o["detail"]["bbox_page_px"]
    elif o["quantity"] == "system_arc":
        sysarc.append(o)
res = collections.Counter()
rows = []
for s in sorted({s for x in arcs for s, _, _ in x["heads"]}):
    bx0, by0, bx1, by1 = box[s]
    page = int(s.split("/")[1])
    best = None
    for o in sysarc:
        if int(o["subject"].split("/")[1]) != page:
            continue
        d = o["detail"]
        tr = d.get("trace") or []
        cols = [(x, a, b) for x, a, b in tr if bx0 <= x <= bx1]
        if not cols:
            continue
        inside = [c for c in cols if by0 - 4 <= (c[1] + c[2]) / 2 <= by1 + 4]
        if not inside:
            continue
        xl, xr = d["x_left_page"], d["x_right_page"]
        kind = "ends_inside" if (bx0 <= xl <= bx1 or bx0 <= xr <= bx1) else ("through" if xl < bx0 and xr > bx1 else "edge")
        best = (kind, len(inside), round(bx1 - bx0))
        break
    res[best[0] if best else "no_trace_in_box"] += 1
    rows.append((s, best))
print(dict(res))
print(rows[:10])
