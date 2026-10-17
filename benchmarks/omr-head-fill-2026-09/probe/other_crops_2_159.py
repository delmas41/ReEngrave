"""ROADMAP 2.159 -- the litolff-unread-35 crops 1-22 whose half is NOT narrowed by head_fill_from_ink: their head rows.
usage: other_crops_2_159.py SLICEDIR OUT.json"""
import json
import os
import sys

SD, OUT = sys.argv[1:3]
want = {"glyph/3/1/2/17/6": 2, "glyph/5/1/6/5/2": 4, "glyph/6/0/5/7/0": 5, "glyph/7/1/3/13/1": 7,
        "glyph/9/1/7/1/3": 9, "glyph/11/0/2/8/3": 14, "glyph/11/0/1/10/7": 16}
res = {}
for s in want:
    pg = int(s.split("/")[1])
    for line in open(os.path.join(SD, "litolff", "p%02d.observations.jsonl" % pg)):
        if '"%s"' % s in line and any(q in line for q in ('"glyph_box"', '"notehead_ink"', '"notehead_class"')):
            o = json.loads(line)
            res.setdefault(s, {})[o["quantity"]] = o
    for line in open(os.path.join(SD, "litolff", "p%02d.verdicts.jsonl" % pg)):
        if '"%s"' % s in line and '"adjudicate_duration"' in line:
            res[s]["adj"] = json.loads(line)
            break
json.dump(res, open(OUT, "w"))
for s, n in want.items():
    r = res[s]
    d = r["notehead_ink"]["detail"]
    iw = d.get("interior_white") or {}
    b = r["glyph_box"]["value"]
    a = r["adj"]["detail"]
    print(n, s, b[0], "box %.2fx%.2f" % (b[3] / 100, b[4] / 100), "rs", iw.get("rows_share"), "hole",
          iw.get("hole_share"), "c23", d["ink_raw"]["windows"]["center"],
          (d.get("ink_off_line") or {}).get("windows", {}).get("center"), "hff", a.get("head_fill_first"),
          "stems", a.get("stems_attached"), r["adj"]["reason"])
