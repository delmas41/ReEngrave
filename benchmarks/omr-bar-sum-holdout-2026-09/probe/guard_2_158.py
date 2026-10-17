"""ROADMAP 2.158 -- for every note the flag changed (replay OUT.json), the existing readers a guard could use: its own
stem (`head_stem` verdict), detector confidence, `notehead_ink`, and whether its box overlaps a decided arc's box.
usage: guard_2_158.py REPLAY.json RECORD.json"""
import collections
import json
import sys

import ijson

R = json.load(open(sys.argv[1]))
want = set(R["changed"])
cells = {"/".join(g.split("/")[:5]).replace("glyph/", "") for g in want}
obs = collections.defaultdict(dict)
arcs = collections.defaultdict(list)
with open(sys.argv[2], "rb") as fh:
    for o in ijson.items(fh, "record.observations.item", use_float=True):
        s = o["subject"]
        if s in want:
            obs[s][o["quantity"]] = o
        if o["quantity"] == "arc_box" and s.startswith("glyph/"):
            pg = s.split("/")[1]
            arcs[pg].append((s, (o.get("detail") or {}).get("bbox_page_px")))
stem = {}
with open(sys.argv[2], "rb") as fh:
    for v in ijson.items(fh, "record.verdicts.item", use_float=True):
        if v["subject"] in want and v["quantity"] in ("head_stem", "stem_direction"):
            stem[(v["subject"], v["quantity"])] = (v["outcome"], v.get("reason"))
for g in sorted(want):
    o = obs[g]
    b = (o.get("glyph_box", {}).get("detail") or {}).get("bbox_page_px")
    ov = [a for a, ab in arcs[g.split("/")[1]] if ab and b and ab[0] < b[2] and ab[2] > b[0] and ab[1] < b[3] and ab[3] > b[1]]
    print(g, "stem", stem.get((g, "head_stem")), "conf %.2f" % o.get("glyph_conf", {}).get("value", -1),
          "ink", o.get("notehead_ink", {}).get("value"), "cls", (o.get("glyph_box", {}).get("value") or [None])[0],
          "arc_overlap", ov)
