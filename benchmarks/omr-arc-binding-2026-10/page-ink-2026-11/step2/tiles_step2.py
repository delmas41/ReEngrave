"""2.274 step 2: 12 BLIND tiles for Sean. The question, every tile: "Does the arc start and end on the right notes?" Never tie vs slur.

    python3 tiles_step2.py WORKDIR SLICEDIR OUTDIR PLATE:PAGE[,PAGE] [PLATE:PAGE ...] [--seed 2746] [--quota replaced=4,new=4,abstained=3,unchanged=1]

One tile = one staff, cut from the page at 600 dpi, drawn from the WRITTEN ON file: the arc as the file writes it (a thin orange curve from the start note to the stop note, bowed
to the side the printed arc lies on and held a little clear of the ink so the print stays visible) and a thin orange box round each of its two noteheads. Nothing else, no labels,
no arrows. The crop runs from the left-most to the right-most of {both noteheads, the printed run's ends} plus 4 spaces, so BOTH ends of the printed arc are always in the tile.
Cases: `replaced` (a written run whose notes OFF wrote differently: cut / short / other kind), `new` (a written run OFF wrote nothing for), `unchanged` (a written run OFF wrote
the same), `abstained` (the binder wrote nothing: the tile shows the arc the file DOES have over that run -- the old path's -- so Sean judges what stays). Hold-out and
never-used pages only. The key (category, run, notes) goes in <OUTDIR>-key.json beside the folder.
"""
import json
import pathlib
import random
import sys

import cv2
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3]))

import arcs as A  # noqa: E402
import measure_first as M  # noqa: E402
from tools.omr.staged import lane_report as L  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402

ORANGE = (0, 140, 255)      # BGR, the lane report's neutral orange


def draw_arc(img, a, b, side, sp, ox, oy, sc):
    """quadratic curve from head box `a` to head box `b`; `side` -1 = over (cap), +1 = under (cup)"""
    ax, bx = (a[0] + a[2]) / 2.0, (b[0] + b[2]) / 2.0
    ya = a[1] - 0.3 * sp if side < 0 else a[3] + 0.3 * sp
    yb = b[1] - 0.3 * sp if side < 0 else b[3] + 0.3 * sp
    span = abs(bx - ax)
    bulge = side * min(2.5 * sp, max(0.8 * sp, 0.12 * span))
    bulge += side * 0.8 * sp          # held clear of the printed arc: one space further out
    pts = []
    for t in np.linspace(0, 1, 60):
        x = (1 - t) * ax + t * bx
        y = (1 - t) * ya + t * yb + 4 * t * (1 - t) * bulge
        pts.append([(x - ox) * sc, (y - oy) * sc])
    cv2.polylines(img, [np.array(pts, np.int32)], False, ORANGE, 2, cv2.LINE_AA)


def main():
    argv = sys.argv[1:]
    seed, quota = 2746, dict(replaced=4, new=4, abstained=3, unchanged=1)
    if "--seed" in argv:
        i = argv.index("--seed")
        seed = int(argv[i + 1])
        del argv[i:i + 2]
    if "--quota" in argv:
        i = argv.index("--quota")
        quota = {k: int(v) for k, v in (kv.split("=") for kv in argv[i + 1].split(","))}
        del argv[i:i + 2]
    workdir, slicedir, out = argv[0], argv[1], pathlib.Path(argv[2])
    specs = argv[3:]
    out.mkdir(parents=True, exist_ok=True)
    pool = {k: [] for k in quota}
    ctx = {}
    for sp_ in specs:
        plate, pg = sp_.split(":")
        pages = [int(x) for x in pg.split(",")]
        off, on, extra, boxes, runs = M.load(workdir, slicedir, plate, pages)
        recs = A.per_run(extra, off, boxes, runs)
        ctx[plate] = dict(off=off, on=on, boxes=boxes, runs=runs)
        for r in recs:
            r["plate"] = plate
            if r["status"] == "written":
                cat = {"whole": "unchanged", "none": "new"}.get(r["off"], "replaced")
            elif r["status"] == "abstained" and r["off_overlap"]:
                cat = "abstained"
            else:
                continue
            if cat in pool:
                pool[cat].append(r)
    rng = random.Random(seed)
    pick = []
    for cat, n in quota.items():
        items = pool[cat]
        rng.shuffle(items)
        pick += [(cat, r) for r in items[:n]]
    rng.shuffle(pick)
    key = []
    imgs = {}
    for n, (cat, r) in enumerate(pick, 1):
        plate, page = r["plate"], r["page"]
        c = ctx[plate]
        if (plate, page) not in imgs:
            imgs.clear()
            imgs[(plate, page)] = cv2.cvtColor(render_page(str(L.LIB / L.PLATES[plate]["pdf"]), page, dpi=600).rgb, cv2.COLOR_RGB2BGR)
        im = imgs[(plate, page)]
        sp = L.PLATES[plate]["unit"]
        if cat == "abstained":
            best, bo = None, 0
            for a in r["off_overlap"]:       # the arc the file DOES have over this run (the old path's): the biggest overlap
                s = A.span_of(a, c["boxes"])
                if s and min(s[1], r["x1"]) - max(s[0], r["x0"]) > bo:
                    best, bo = a, min(s[1], r["x1"]) - max(s[0], r["x0"])
            arc = dict(kind=best["kind"], start=best["start"], stop=best["stop"])
        else:
            arc = dict(kind=r["kind"], start=r["start"], stop=r["stop"])
        ha, hb = c["boxes"][arc["start"]]["box"], c["boxes"][arc["stop"]]["box"]
        row = c["runs"][(page, r["ordinal"])]
        side = -1 if row["sagitta_spaces"] < 0 else +1          # sagitta positive = the middle is LOWER than the chord = a cup (under its notes)
        pts = np.array(row["points"], float)
        xs0, xs1 = min(ha[0], hb[0], pts[:, 0].min()), max(ha[2], hb[2], pts[:, 0].max())
        ys0 = min(ha[1], hb[1], pts[:, 1].min())
        ys1 = max(ha[3], hb[3], pts[:, 1].max())
        x0, x1 = int(max(0, xs0 - 4 * sp)), int(min(im.shape[1], xs1 + 4 * sp))
        y0, y1 = int(max(0, ys0 - 5 * sp)), int(min(im.shape[0], ys1 + 5 * sp))
        crop = im[y0:y1, x0:x1].copy()
        sc = min(3.0, 1000.0 / max(1, x1 - x0))
        crop = cv2.resize(crop, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC if sc > 1 else cv2.INTER_AREA)
        draw_arc(crop, ha, hb, side, sp, x0, y0, sc)
        for b in (ha, hb):
            pad = 0.15 * sp
            cv2.rectangle(crop, (int((b[0] - pad - x0) * sc), int((b[1] - pad - y0) * sc)), (int((b[2] + pad - x0) * sc), int((b[3] + pad - y0) * sc)), ORANGE, 2)
        cv2.imwrite(str(out / ("tile-%02d.png" % n)), crop)
        key.append(dict(tile=n, category=cat, plate=plate, page=page, run=r["ordinal"], staff=row["staff"], kind=arc["kind"], start=arc["start"], stop=arc["stop"],
                        closest_ends=r.get("closest"), why=r.get("why"), status=r["status"], run_x=[round(r["x0"]), round(r["x1"])]))
    json.dump(key, open(out.parent / (out.name + "-key.json"), "w"), indent=1)
    (out / "README.md").write_text(
        "# 2.274 step 2 tiles\n\nEach picture is one staff of a scanned score page. The orange curve is the arc OUR FILE WRITES; the two orange boxes are the two notes it is "
        "attached to. The printed arc is the black one underneath (the orange curve is held a little clear of it).\n\n"
        "**Question, for every tile:** Does the arc start and end on the right notes (the two boxed notes)?\n\nAnswer by tile number: yes, no, or which note it should be.\n")
    print(len(key), "tiles ->", out, {k: sum(1 for x in key if x["category"] == k) for k in quota}, "pools", {k: len(v) for k, v in pool.items()})


if __name__ == "__main__":
    main()
