"""ROADMAP 2.158 -- every glyph_box (any category, any staff/cell) on a page whose page box overlaps a window; plus every
row of those glyphs' subjects that names a refusal. usage: boxes_near_2_158.py RECORD.json PAGE x0 y0 x1 y1"""
import sys

import ijson

REC, PG = sys.argv[1], int(sys.argv[2])
X0, Y0, X1, Y1 = (float(x) for x in sys.argv[3:7])
with open(REC, "rb") as fh:
    for o in ijson.items(fh, "record.observations.item", use_float=True):
        s = o["subject"]
        if not s.startswith("glyph/%d/" % PG) or o["quantity"] not in ("glyph_box", "arc_box"):
            continue
        b = (o.get("detail") or {}).get("bbox_page_px")
        if b and b[0] < X1 and b[2] > X0 and b[1] < Y1 and b[3] > Y0:
            print(s, o["quantity"], o["value"][0] if isinstance(o["value"], list) else o["value"], [round(x) for x in b])
