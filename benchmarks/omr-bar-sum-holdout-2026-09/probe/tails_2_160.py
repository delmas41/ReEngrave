"""ROADMAP 2.160 part 3 -- COUNT (not fix) notehead boxes that may be a tie/slur's TAIL at a bar's left edge: a GATHER fault
(2.158 tile 14). Geometry only, from `heads_2_160.py` rows and the record's arc boxes:
  * the head box starts within EDGE staff spaces of its cell's left edge (the barline side), and
  * an arc box (tie or slur) of the SAME staff, filed in an EARLIER cell, ends within GAP staff spaces left of the head box
    and overlaps it vertically (the arc runs into the bar and the head box sits on its end).
Every hit is a CANDIDATE for Sean's eye; nothing here says it is a tail. Also reported: the same test with the arc in the
SAME cell (an arc whose box covers the head), and the staff-erased ink of the hits.
usage: tails_2_160.py HEADS.json RECORD.json OUT.json [EDGE=0.5] [GAP=0.5]"""
import collections
import json
import sys

import ijson

HEADS, REC, OUT = sys.argv[1:4]
EDGE = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
GAP = float(sys.argv[5]) if len(sys.argv) > 5 else 0.5
H = json.load(open(HEADS))["heads"]
arcs = collections.defaultdict(list)
with open(REC, "rb") as fh:
    for o in ijson.items(fh, "record.observations.item", use_float=True):
        if o["quantity"] == "arc_box" and o["subject"].startswith("glyph/"):
            p = o["subject"].split("/")
            arcs[(p[1], p[2], p[3])].append((o["subject"], o["value"], (o.get("detail") or {}).get("bbox_page_px"),
                                             o.get("score")))
hits, same = [], []
for g, h in H.items():
    if h["left_gap_sp"] is None or h["left_gap_sp"] > EDGE:
        continue
    p = g.split("/")
    b, sp = h["box"], h["sp"]
    for a, kind, ab, sc in arcs[(p[1], p[2], p[3])]:
        if not ab or ab[1] > b[3] or ab[3] < b[1]:
            continue
        acell = int(a.split("/")[4])
        gap = (b[0] - ab[2]) / sp
        if acell < int(p[4]) and -0.25 <= gap <= GAP:
            hits.append(dict(glyph=g, arc_glyph=a, kind=kind, arc_conf=round(sc or 0, 3), gap_sp=round(gap, 3), **h))
            break
        if acell == int(p[4]) and ab[0] <= b[0] + 0.25 * sp and ab[2] >= b[2]:
            same.append(dict(glyph=g, arc_glyph=a, kind=kind, **h))
            break
json.dump(dict(edge=EDGE, gap=GAP, hits=hits, same_cell=same), open(OUT, "w"), indent=0)
byk = collections.Counter(x["kind"] for x in hits)
print("heads at the left edge", sum(1 for h in H.values() if h["left_gap_sp"] is not None and h["left_gap_sp"] <= EDGE),
      "| arc from an earlier cell ends on the head", len(hits), dict(byk), "| arc in the same cell over it", len(same))
nets = sorted(x["ink_net"] for x in hits if x["ink_net"] is not None)
if nets:
    print("hit ink_net: min %.3f med %.3f max %.3f; below 0.35: %d" % (nets[0], nets[len(nets) // 2], nets[-1],
                                                                    sum(1 for n in nets if n < 0.35)))
