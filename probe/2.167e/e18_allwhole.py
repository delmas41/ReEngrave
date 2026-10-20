"""2.167e probe 18: every whole-valued head of both plates as contact-sheet lists (my own look at all of them). usage: e18_allwhole.py"""
import json

d = "probe/2.167e/data/"
items = []
for pl in ("lit", "bra"):
    rows = json.load(open(d + "%s_whole.json" % pl))
    for r in rows:
        items.append([pl, r["sub"], "%s %s c%.2f ctr%s st%s" % (pl, r["sub"].split("/", 1)[1], r["conf"], r["center"], int(r["stem_ink"]))])
json.dump(items[:40], open("/private/tmp/claude-501/s173/look/allwhole_a.json", "w"))
json.dump(items[40:], open("/private/tmp/claude-501/s173/look/allwhole_b.json", "w"))
print(len(items))
