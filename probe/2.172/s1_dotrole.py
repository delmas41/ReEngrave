"""2.172 step 3: what dot_role says about the small view's augmentationDot boxes, per plate, against production's own dots. usage: s1_dotrole.py"""
import collections
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
for pl in ("lit", "bra"):
    R = json.loads(open(ROOT / ("rec172/%s-small.record.json" % pl)).read())["record"]
    src = {}
    for o in R["observations"]:
        if o["quantity"] == "glyph_box" and o["value"][0] == "augmentationDot":
            src[o["subject"]] = o.get("reader")
    c = collections.Counter()
    for v in R["verdicts"]:
        if v.get("quantity") == "dot_role" and v["subject"] in src:
            c[(src[v["subject"]], v["outcome"], str(v.get("value")) if v["outcome"] == "decided" else v.get("reason"))] += 1
    print("==", pl)
    for k, n in sorted(c.items(), key=lambda x: (x[0][0] or "", -x[1])):
        print("  ", k, n)
