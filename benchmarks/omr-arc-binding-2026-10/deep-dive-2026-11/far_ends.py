"""The unbound ends > 4 sp from any head: what lies past the traced end (measure only)? A neighbour arc box (any, even one refused as a staff
line or never traced) meeting that end = the arc was boxed in pieces and the trace did not join them; none = the arc ends in the open.
python3 far_ends.py PLATE [ARM]"""
import collections
import json
import pathlib
import sys

plate = sys.argv[1]
arm = sys.argv[2] if len(sys.argv) > 2 else "base"
D = pathlib.Path("scratch/dd")
dump = json.load(open(D / ("%s.%s.arcs.json" % (plate, arm))))
led = json.load(open(D / ("%s.%s.ledger.json" % (plate, arm))))
boxes = [(o["subject"], o["detail"]["bbox_page_px"]) for o in dump["arc_box"]]
refused = {r["curve"] for r in led["rows"] if r["fate"] == "not_an_arc"}
piece_refused = set()
for r in led["rows"]:
    if r["fate"] == "not_an_arc":
        piece_refused.update(r["pieces"])
heads_by_staff = collections.defaultdict(list)
for h in dump["heads"]:
    b = h["box"]
    if b:
        heads_by_staff["/".join(h["subject"].split("/")[1:4])].append(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2))
c = collections.Counter()
SPEC = []
for r in led["rows"]:
    if r["fate"] != "dropped" or r.get("x_left") is None:
        continue
    pb = r.get("binding") or {}
    st = "/".join(r["owner"].split("/")[1:4]) if r.get("owner") else r["staff"]
    sp = r["sp"]
    for side, sgn, ex, ey in (("left", -1, r["x_left"], r["y_left"]), ("right", 1, r["x_right"], r["y_right"])):
        if (pb.get(side) or {}).get("unbound") != "no_head_at_end":
            continue
        cands = [(abs(cx - ex) + abs(cy - ey)) / sp for cx, cy in heads_by_staff[st] if (cx - ex) * sgn > -0.8 * sp]
        if not cands or min(cands) <= 4:
            continue
        nb = None
        for k, b in boxes:
            if k in r["pieces"]:
                continue
            # a box that STARTS near this end (right end: its left edge) or ENDS near it (left end), at about the same height
            edge = b[0] if sgn > 0 else b[2]
            yc = (b[1] + b[3]) / 2
            if abs(edge - ex) <= 3 * sp and abs(yc - ey) <= 3 * sp and "/".join(k.split("/")[1:4]) == r["staff"]:
                nb = (k, "refused_as_staff_line" if k in piece_refused else "kept")
                break
        c[(side, "neighbour box " + nb[1] if nb else "no neighbour box (arc ends in the open here)", "cut_at_barline" if r.get("cut") else "free")] += 1
        if not nb and r.get("cut"):
            SPEC.append(dict(plate=plate, page=r["page"], box=[min(r["x_left"], r["box"][0]), r["box"][1], max(r["x_right"], r["box"][2]), r["box"][3]], sp=sp,
                             curve=r["curve"], side=side, kind=r.get("kind")))
tot = sum(c.values())
print(plate, arm, "far (>4 sp) unbound ends on dropped curves:", tot)
for k, v in c.most_common():
    print("  ", v, k)

import random
random.Random(5).shuffle(SPEC)
for i, s_ in enumerate(SPEC[:int(sys.argv[3]) if len(sys.argv) > 3 else 0], 1):
    s_["n"] = i
json.dump(SPEC[:int(sys.argv[3]) if len(sys.argv) > 3 else 0], open("scratch/dd/spec_far_%s.json" % plate, "w"), indent=1)
