"""Dropped real curves with an unbound end: how far is the nearest head of the owner staff beyond that end, in staff spaces (measure only)?
Tells a near miss (the arc stops short of its note: closest-note binds it) from a half arc (the head is another arc's). python3 ends_dist.py PLATE [ARM]"""
import collections
import json
import pathlib
import sys

plate = sys.argv[1]
arm = sys.argv[2] if len(sys.argv) > 2 else "base"
D = pathlib.Path("scratch/dd")
dump = json.load(open(D / ("%s.%s.arcs.json" % (plate, arm))))
led = json.load(open(D / ("%s.%s.ledger.json" % (plate, arm))))
heads_by_staff = collections.defaultdict(list)
for h in dump["heads"]:
    b = h["box"]
    if b:
        heads_by_staff["/".join(h["subject"].split("/")[1:4])].append(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, h["subject"]))
nin = {v["subject"]: v for v in dump["verdicts"] if v["quantity"] == "notehead_is_not_a_notehead"}
hist = collections.Counter()
bypieces = collections.Counter()
n_ends = 0
for r in led["rows"]:
    if r["fate"] not in ("dropped",) or r.get("x_left") is None:
        continue
    pb = r.get("binding") or {}
    own = r.get("owner")
    st = "/".join(own.split("/")[1:4]) if own else r["staff"]
    sp = r["sp"]
    for side, sgn, ex, ey in (("left", -1, r["x_left"], r["y_left"]), ("right", 1, r["x_right"], r["y_right"])):
        e = pb.get(side) or {}
        if e.get("unbound") != "no_head_at_end":
            continue
        cands = [(abs(cx - ex) + abs(cy - ey)) / sp for cx, cy, k in heads_by_staff[st]
                 if (cx - ex) * sgn > -0.8 * sp and not (nin.get(k) and nin[k]["value"] is True)]
        if not cands:
            hist["no_head_beyond (system edge)"] += 1
            continue
        d = min(cands)
        n_ends += 1
        b = "<=2 sp" if d <= 2 else "2-4 sp" if d <= 4 else "4-8 sp" if d <= 8 else ">8 sp"
        hist[b] += 1
        bypieces[(b, "lone piece" if r["n_pieces"] == 1 else "joined")] += 1
print(plate, arm, "unbound ends on dropped curves:", n_ends + hist["no_head_beyond (system edge)"], dict(hist))
print(sorted(bypieces.items()))
