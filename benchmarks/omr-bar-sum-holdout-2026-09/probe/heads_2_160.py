"""ROADMAP 2.160 -- one row per notehead-classed glyph of a stored record: its page box, class, detector confidence,
`notehead_ink` (value, and the raw / staff-erased / line-rows-left-out readings it is the max of), the cell's box and
staff space, and the nearest arc box on the same staff (gap in staff spaces, same-row overlap). GATHER rows only, read
from the record; nothing re-decided. STAGED GATHER (read-only).
usage: heads_2_160.py RECORD.json OUT.json"""
import collections
import json
import sys

import ijson

SRC, OUT = sys.argv[1:3]
heads = collections.defaultdict(dict)
arcs = collections.defaultdict(list)       # (page, system, staff) -> [(glyph, kind, bbox, conf, shape)]
cells = {}
space = {}
with open(SRC, "rb") as fh:
    for o in ijson.items(fh, "record.observations.item", use_float=True):
        s, q = o["subject"], o["quantity"]
        if s.startswith("cell/"):
            if q == "cell_box":
                cells[s] = o["value"]
            elif q == "cell_ink_pieces":
                space[s] = (o.get("detail") or {}).get("staff_space_page_px")
            continue
        if not s.startswith("glyph/"):
            continue
        d = o.get("detail") or {}
        if q == "glyph_box":
            heads[s]["cls"] = o["value"][0]
            heads[s]["box"] = d.get("bbox_page_px")
            heads[s]["cat"] = d.get("category")
            heads[s]["conf"] = o.get("score")
        elif q == "notehead_ink":
            heads[s]["ink"] = o["value"]
            heads[s]["ink_raw"] = (d.get("ink_raw") or {}).get("best")
            heads[s]["ink_net"] = (d.get("ink_net") or {}).get("best")
            heads[s]["ink_off"] = (d.get("ink_off_line") or {}).get("best")
            heads[s]["box_source"] = d.get("box_source")
        elif q == "arc_box":
            p = s.split("/")
            arcs[(p[1], p[2], p[3])].append((s, o["value"], d.get("bbox_page_px"), o.get("score")))
        elif q == "arc_ink_shape":
            heads[s]["arc_shape"] = o["value"]


def gap(a, b):
    dx = max(0.0, max(a[0], b[0]) - min(a[2], b[2]))
    dy = max(0.0, max(a[1], b[1]) - min(a[3], b[3]))
    return (dx * dx + dy * dy) ** 0.5


rows = {}
for g, h in heads.items():
    if h.get("cat") != "notehead" or not h.get("box"):
        continue
    p = g.split("/")
    cell = "cell/" + "/".join(p[1:5])
    sp = space.get(cell) or 15.0
    b = h["box"]
    best = None
    for a, kind, ab, ac in arcs[(p[1], p[2], p[3])]:
        if not ab:
            continue
        d = gap(b, ab) / sp
        if best is None or d < best[0]:
            best = (round(d, 3), a, kind, round(ac or 0, 3), heads.get(a, {}).get("arc_shape"))
    cb = cells.get(cell)
    rows[g] = dict(cls=h["cls"], box=[round(x, 2) for x in b], conf=round(h["conf"] or 0, 4), ink=h.get("ink"),
                   ink_raw=h.get("ink_raw"), ink_net=h.get("ink_net"), ink_off=h.get("ink_off"),
                   box_source=h.get("box_source"), sp=sp,
                   cell_box=cb, left_gap_sp=round((b[0] - cb[0]) / sp, 3) if cb else None,
                   arc=best)
json.dump(dict(src=SRC, n=len(rows), heads=rows), open(OUT, "w"))
print("heads", len(rows), "arc staves", len(arcs))
