"""ROADMAP 2.166 -- print what page_ab.py found for named glyphs (their box, every system arc touching them).
usage: peek.py AB.json GLYPH..."""
import json
import sys

d = json.load(open(sys.argv[1]))
for g in sys.argv[2:]:
    b = d["boxes"].get(g)
    print(g, b and b["value"], b and {k: b["detail"].get(k) for k in ("x0", "y0", "x1", "y1", "confidence")})
    pre = "/".join(g.split("/")[:4]) + "/"
    for o in d["sysarc"]:
        dd = o["detail"]
        if any(p.startswith(pre) for p in dd["pieces"]) or any(h["glyph"] == g for h in dd["through_boxes"]):
            print("  ARC", o["subject"], o["value"], dd["pieces"], dd["cells"], dd["x_left_page"], dd["x_right_page"],
                  dd["y_left_page"], dd["through_boxes"], dd["anchor_left"], dd["anchor_right"])
    print("  changed:", d["changed"].get(g))
print("erased cells", len(d["erased_cells"]), "px", sum(e["n"] for e in d["erased_cells"]))
