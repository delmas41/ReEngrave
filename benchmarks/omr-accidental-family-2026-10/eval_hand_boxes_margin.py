"""2.263: eval_hand_boxes.py again, keeping the signed MARGIN of each reading (the 2.201 run did not store it). Same 142 hand boxes, same reader (current tree).
reader on the mark's own strokes, with the box = Sean's hand box. The cut-offs were set on the 58 answered tiles, not on these.
usage: eval_hand_boxes.py [OUT.json]"""
import json, sys, os
sys.path.insert(0, "."); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collections import defaultdict, Counter
from tools.omr.staged import pipeline, gather as G, stroke_map as SM, accidental_family as AF
import cause_cut as CC
HERE = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    items = json.load(open(os.path.join(HERE, "data", "truth_brahms.json")))["items"]
    by = defaultdict(list)
    for it in items:
        by[it["page"]].append(it)
    out = []
    for page, its in sorted(by.items()):
        pws, cells = pipeline.prepare_pages(CC.PDF["brahms"], [page], dpi=600)[0]
        for it in its:
            bx0, by0, bx1, by1 = it["box"]
            best = None
            for c in cells:
                cb = c.bbox_page_px
                ix = max(0, min(bx1, cb[2]) - max(bx0, cb[0])); iy = max(0, min(by1, cb[3]) - max(by0, cb[1]))
                fr = ix * iy / max(1e-9, (bx1 - bx0) * (by1 - by0))
                if best is None or fr > best[0]:
                    best = (fr, c)
            fr, c = best
            grid = G._cell_grid(c); sp = grid[1] * 2.0
            res = SM.map_strokes(c.image_no_staff, sp, list(c.staff_line_ys_canonical), c.binary)
            up, cb = c.upscale_factor, c.bbox_page_px
            box = ((bx0 - cb[0]) * up, (by0 - cb[1]) * up, (bx1 - cb[0]) * up, (by1 - cb[1]) * up)
            fam = AF.family_row(it["cls"], box, res.strokes, SM.strokes_in_box(res, box), sp)
            out.append(dict(box=it["box"], src=it["src"], page=page, role=it["label_family"], sean=it["type"], cls=it["cls"], type=fam["type"], why=fam["why"],
                            grown=max(fam["grown_sp"].values()), cell_frac=round(fr, 2), margin=fam["margin"], feat=fam["features"]))
    tab = defaultdict(Counter)
    for o in out:
        k = (o["role"], o["sean"])
        tab[k]["n"] += 1
        tab[k]["right"] += o["type"] == o["sean"]
        tab[k]["unclear"] += o["type"] in ("unclear", "unread")
        tab[k]["wrong"] += o["type"] in AF.TYPES and o["type"] != o["sean"]
        tab[k]["cut>=0.5sp"] += o["grown"] >= 0.5
    for k, v in sorted(tab.items()):
        print(k, dict(v))
    tot = Counter()
    for v in tab.values():
        tot.update(v)
    print("TOTAL", dict(tot))
    print("wrong:", [(o["src"], o["page"], o["sean"], o["type"], o["why"]) for o in out if o["type"] in AF.TYPES and o["type"] != o["sean"]])
    if len(sys.argv) > 1:
        json.dump(out, open(sys.argv[1], "w"), indent=1, default=float)
