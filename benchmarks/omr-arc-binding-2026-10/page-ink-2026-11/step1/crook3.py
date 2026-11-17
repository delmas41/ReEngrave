"""2.274 r3: runs that lie inside a claimed WORD area (the "(C)" crook label and other words), before (round-2 output dir) and after.
    R2_CACHE=.. R2_SLICES=.. python3 crook3.py PLATE PAGE OLDDIR NEWDIR"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import viz3  # noqa: E402

plate, page, old, new = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
canvas, raw, sp, line_ys, boxes, areas, arc_boxes = viz3.load(plate, page)
words = [a for o, a in areas if o == "word"]
for label, d in (("old", old), ("new", new)):
    J = json.load(open("%s/%s-p%d.step1.json" % (d, plate, page)))
    hits = []
    for r in J["runs"]:
        x0, y0, x1, y1 = r["box"]
        for (a0, b0, a1, b1) in words:
            if x0 >= a0 - 5 and x1 <= a1 + 5 and y0 >= b0 - 5 and y1 <= b1 + 5 and (a1 - a0) < 8 * sp * 2:
                hits.append((r["id"], [round(v) for v in r["box"]], r.get("src"), bool(r["witnesses"]), [round(v) for v in (a0, b0, a1, b1)]))
                break
    print(label, "runs wholly inside a (small) word area:", len(hits))
    for h in hits:
        print("   ", h)
