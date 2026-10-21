"""ROADMAP 2.179 -- red bars OFF vs ON by (page/system/staff/cell, part): which went red, which stopped being red, and the new-box glyphs in them.
usage: b1_bar_diff.py OFF.red_rows.json ON.red_rows.json ON.new_glyphs.json"""
import json
import sys

off, on, new = (json.load(open(p)) for p in sys.argv[1:4])
k = lambda b: (b["bar_key"], b["part"])  # noqa: E731
A, B = {k(b): b for b in off}, {k(b): b for b in on}
newcells = {}
for g in new:
    newcells.setdefault("/".join(g["glyph"].split("/")[1:5]), []).append(g)
went = [x for x in B if x not in A]
left = [x for x in A if x not in B]
print("went red", len(went), "| stopped red", len(left))
for x in went:
    c = "%s" % x[0]
    print("  RED  ", x, B[x]["words"][15:], "| new boxes here:", [(g["glyph"].split("/")[-1], g["detail"]["read_from"][:14], g["placed"]) for g in newcells.get(c, [])])
for x in left[:5]:
    print("  FIXED", x, A[x]["words"][15:])
