"""ROADMAP 2.305 round 2: Sean's 12 blind tiles, by a rule fixed before the draw (`random.Random(SEED)`).

    python3 tiles_2305_r2.py OUT_DIR KEY_JSON SEED FIXED.json PLATE:WORK:GATHERDIR:PRIORWORK ...
WORK = the round-2 replay's `work/` (PLATE.off|on.musicxml), GATHERDIR = the saved gather (head boxes), PRIORWORK = the round-1 replay (its ON file).

RULE: (1) the round-1 faults Sean named (FIXED.json: [{plate, start, stop, why}]), each drawn on its two notes whatever the new file writes there (the key says
what it writes now); (2) 4 places where a SLUR the OFF file writes is no longer written ON (box on the OFF slur's two notes), seeded; (3) the rest from arcs the
round-2 file writes that the round-1 file did not, seeded. Arcs whose two notes are on different systems or staves are not tiled. Order shuffled.
A tile: the print, one staff tall and generous (3 spaces above and below the notes, 6 spaces either side), ONE thin orange box from the first note to the last
and 3 spaces above and below them (the whole arc inside it) -- nothing else.
QUESTION: "In the box: is there one arc from the first note to the last note? If yes, is it a tie or a slur?"
"""
import json
import pathlib
import random
import sys

import cv2
import fitz
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "page-ink-2026-11" / "step2"))
import arcs as A  # noqa: E402
from tools.omr.staged import lane_report as L  # noqa: E402
from tools.omr.staged.judged import iter_array  # noqa: E402

QUESTION = "In the box: is there one arc from the first note to the last note? If yes, is it a tie or a slur?"


def same_staff(a):
    return a["start"].split("/")[1:4] == a["stop"].split("/")[1:4]


def main():
    out, keyp, seed, fixedp = pathlib.Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]), sys.argv[4]
    rnd = random.Random(seed)
    out.mkdir(parents=True, exist_ok=True)
    specs = {}
    files = {}
    for spec in sys.argv[5:]:
        plate, work, gdir, prior = spec.split(":")
        specs[plate] = gdir
        rd = lambda p, arm: A.arcs_of_xml((pathlib.Path(p) / ("%s.%s.musicxml" % (plate, arm))).read_text())  # noqa: E731
        files[plate] = dict(on=rd(work, "on"), off=rd(work, "off"), prior=rd(prior, "on"))
    k = lambda a: (a["kind"], a["start"], a["stop"])  # noqa: E731

    def now(plate, s, t):
        hit = [a["kind"] for a in files[plate]["on"] if {a["start"], a["stop"]} == {s, t}]
        return hit[0] if hit else "nothing"

    items = []
    for f in json.load(open(fixedp)):
        items.append(dict(f, kind_now=now(f["plate"], f["start"], f["stop"])))
    removed, gained = [], []
    for plate, fl in files.items():
        on = {k(a) for a in fl["on"]}
        prior = {k(a) for a in fl["prior"]}
        for a in fl["off"]:
            if a["kind"] == "slur" and k(a) not in on and same_staff(a):
                removed.append(dict(plate=plate, start=a["start"], stop=a["stop"], why="OFF slur not written ON (box on the OFF slur's notes)", kind_now=now(plate, a["start"], a["stop"]),
                                    kind_off="slur"))
        for a in fl["on"]:
            if k(a) not in prior and same_staff(a):
                gained.append(dict(plate=plate, start=a["start"], stop=a["stop"], why="written by round 2, not by round 1", kind_now=a["kind"]))
    taken = {(i["start"], i["stop"]) for i in items}
    rnd.shuffle(removed)
    rnd.shuffle(gained)
    for pool, n in ((removed, 4), (gained, 12)):
        for a in pool:
            if len(items) >= 12 or n <= 0:
                break
            if (a["start"], a["stop"]) in taken:
                continue
            items.append(a)
            taken.add((a["start"], a["stop"]))
            n -= 1
    rnd.shuffle(items)
    heads_cache, imgs, tiles, key = {}, {}, [], []
    for n, it in enumerate(items, 1):
        plate = it["plate"]
        pg = int(it["start"].split("/")[1])
        if (plate, pg) not in heads_cache:
            hs = {}
            for o in iter_array(pathlib.Path(specs[plate]) / ("%s.on.gathered.record.json" % plate), "observations"):
                if o["quantity"] == "glyph_box" and L.page_of(o["subject"]) == pg and (o.get("detail") or {}).get("category") == "notehead":
                    hs[o["subject"]] = o["detail"]["bbox_page_px"]
            heads_cache[(plate, pg)] = hs
        heads = heads_cache[(plate, pg)]
        if it["start"] not in heads or it["stop"] not in heads:
            print("no head box, no tile:", it)
            continue
        if (plate, pg) not in imgs:
            imgs.clear()
            doc = fitz.open(str(L.LIB / L.PLATES[plate]["pdf"]))
            pix = doc[pg].get_pixmap(dpi=600, colorspace=fitz.csGRAY)
            imgs[(plate, pg)] = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w)
        img = imgs[(plate, pg)]
        ha, hz = heads[it["start"]], heads[it["stop"]]
        sp = 0.9 * max(ha[3] - ha[1], hz[3] - hz[1])
        bx0, bx1 = min(ha[0], hz[0]) - 0.5 * sp, max(ha[2], hz[2]) + 0.5 * sp
        by0, by1 = min(ha[1], hz[1]) - 3.0 * sp, max(ha[3], hz[3]) + 3.0 * sp
        X0, X1 = int(max(0, bx0 - 6 * sp)), int(min(img.shape[1], bx1 + 6 * sp))
        Y0, Y1 = int(max(0, by0 - 3 * sp)), int(min(img.shape[0], by1 + 3 * sp))
        im = cv2.cvtColor(img[Y0:Y1, X0:X1].copy(), cv2.COLOR_GRAY2BGR)
        cv2.rectangle(im, (int(bx0 - X0), int(by0 - Y0)), (int(bx1 - X0), int(by1 - Y0)), (0, 140, 255), 2)
        s = min(1.0, 900.0 / im.shape[1])
        im = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(out / ("%02d.png" % n)), im)
        tiles.append((n, im))
        key.append(dict(tile=n, page=pg, **{k_: v for k_, v in it.items()},
                        position={"page": pg, "box_page_px": [round(bx0), round(by0), round(bx1), round(by1)]}))
    json.dump(dict(question=QUESTION, seed=seed, rule=__doc__.split("RULE: ")[1].split("QUESTION")[0].strip(), tiles=key), open(keyp, "w"), indent=1)
    W = 900
    cells = []
    for n, im in tiles:
        sc = W / im.shape[1]
        im2 = cv2.resize(im, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
        band = np.full((70, W, 3), 255, np.uint8)
        cv2.putText(band, str(n), (6, 58), cv2.FONT_HERSHEY_SIMPLEX, 2.2, (0, 0, 0), 5)
        cells.append(np.vstack([band, im2, np.full((14, W, 3), 120, np.uint8)]))
    rows = []
    for i in range(0, len(cells), 3):
        row = cells[i:i + 3]
        hmax = max(c.shape[0] for c in row)
        row = [np.vstack([c, np.full((hmax - c.shape[0], W, 3), 255, np.uint8)]) if c.shape[0] < hmax else c for c in row]
        while len(row) < 3:
            row.append(np.full((hmax, W, 3), 255, np.uint8))
        rows.append(np.hstack(row))
    cv2.imwrite(str(out / "sheet.png"), np.vstack(rows))
    print(len(tiles), "tiles ->", out)


if __name__ == "__main__":
    main()
