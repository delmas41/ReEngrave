"""2.306 r13 study, Q4: where both readers stem a head and name different directions. OLD's direction is the end of the stem box that sticks
out further past the heads the box overlaps; NEW's is the side the stroke stands on (page-facts: up -> right, down -> left). For each
disagreement: is it the same stroke, and does OLD's direction break the convention against OLD's OWN stem box (stem at the head's left, called up)?
Who says it is right: the convention Sean confirmed (page-facts), not a look. Usage: dirs.py"""
import json, collections
from common import *
for pl in ("lit", "bra"):
    T = json.load(open(S + "/r13/%s.trace.json" % pl))
    C = [r for r in T if r["old_stem"] and r["new_read"] and r["old_dir"] and r["new_dir"] and r["old_dir"] != r["new_dir"] and not r.get("not_real")]
    c = collections.Counter()
    for r in C:
        xf = r["old_xfrac"]
        side = "left" if xf is not None and xf < 0.3 else ("right" if xf is not None and xf > 0.7 else "through")
        same = bool(r["old_box"] and r["new_box"] and abs((r["old_box"][0] + r["old_box"][2]) / 2 - (r["new_box"][0] + r["new_box"][2]) / 2) <= max(3, 0.35 * r["sp"]))
        conv = {"left": "down", "right": "up"}.get(side)
        c[("same stroke" if same else "different strokes", "OLD's stem at the head's %s, OLD says %s" % (side, r["old_dir"]),
           "OLD breaks up-right/down-left" if conv and conv != r["old_dir"] else ("OLD keeps the convention" if conv else "OLD's stem runs through the box"), r["new_how"])] += 1
    print(pl, "both stem, directions differ:", len(C))
    for k, v in c.most_common():
        print("  %3d  %s" % (v, " | ".join(k)))
    allb = [r for r in T if r["old_stem"] and r["old_dir"] and r["old_xfrac"] is not None and not r.get("not_real")]
    bad = sum(1 for r in allb if (r["old_xfrac"] < 0.3 and r["old_dir"] == "up") or (r["old_xfrac"] > 0.7 and r["old_dir"] == "down"))
    thr = sum(1 for r in allb if 0.3 <= r["old_xfrac"] <= 0.7)
    nod = sum(1 for r in T if r["old_stem"] and not r["old_dir"] and not r.get("not_real"))
    print("  all OLD-stemmed real heads with a direction: %d | OLD's direction against its own stem's side: %d | stem through the middle of the box: %d | OLD stem with NO direction: %d" % (len(allb), bad, thr, nod))
