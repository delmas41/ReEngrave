"""ROADMAP 2.305: Sean's blind tiles, drawn from the WRITTEN file (the ON arm's MusicXML: an arc's two notes, glyph keys), by a rule fixed before the draw.

    python3 tiles_2305.py OUT_DIR KEY_JSON SEED PLATE:WORKDIR:GATHERDIR:BASEWORK ...
WORKDIR = the lane replay's `work/` (PLATE.off|on.musicxml), GATHERDIR = the saved gather (PLATE.on.gathered.record.json: head boxes), BASEWORK = the replay of the
tree before 2.305 (its ON file).

RULE: (1) every arc the 2.305 change moved in the file (in ON-2.305, not in ON-before, or the reverse is not tiled: a lost arc has nothing written to show), in
page order; (2) then, seeded (`random.Random(SEED)`), SLURS the whole arc stack writes that OFF does not, until 12 (at least 4 slurs in all). Tile order shuffled
with the same generator. A tile: one staff strip of the 600 dpi print, both end notes and the arc between them, ONE thin orange box from the start note to the
stop note (the written ends) and over the arc's side -- nothing else. The key goes to KEY_JSON only.
QUESTION: "The box holds one written arc, from the first note in the box to the last. Is that right (same notes as the print)? Tie or slur?"
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

QUESTION = "The box holds one written arc, from the first note in the box to the last. Is that right (same notes as the print)? Tie or slur?"


def heads_and_staves(gdir, plate, pages):
    heads, lines = {}, {}
    for o in iter_array(pathlib.Path(gdir) / ("%s.on.gathered.record.json" % plate), "observations"):
        s = o["subject"]
        pg = L.page_of(s)
        if pg not in pages:
            continue
        if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("category") == "notehead":
            heads[s] = o["detail"]["bbox_page_px"]
    return heads


def main():
    out, keyp, seed = pathlib.Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
    rnd = random.Random(seed)
    out.mkdir(parents=True, exist_ok=True)
    moved, extra = [], []
    for spec in sys.argv[4:]:
        plate, work, gdir, base = spec.split(":")
        on = A.arcs_of_xml((pathlib.Path(work) / ("%s.on.musicxml" % plate)).read_text())
        off = A.arcs_of_xml((pathlib.Path(work) / ("%s.off.musicxml" % plate)).read_text())
        bon = A.arcs_of_xml((pathlib.Path(base) / ("%s.on.musicxml" % plate)).read_text())
        k = lambda a: (a["kind"], a["start"], a["stop"])  # noqa: E731
        bset, oset = {k(a) for a in bon}, {k(a) for a in off}
        for a in on:
            if a["start"].split("/")[1:4] != a["stop"].split("/")[1:4]:
                continue          # an arc across a system break (or staves) cannot be shown on ONE staff strip: not tiled, listed in the report
            if k(a) not in bset:
                moved.append(dict(a, plate=plate, gdir=gdir, why="moved by 2.305 (not in the ON file before)"))
            elif a["kind"] == "slur" and k(a) not in oset:
                extra.append(dict(a, plate=plate, gdir=gdir, why="slur the arc stack writes, OFF does not (seeded)"))
    moved.sort(key=lambda a: (a["plate"], a["start"]))
    rnd.shuffle(extra)
    items = moved[:12]
    n_slur = sum(1 for a in items if a["kind"] == "slur")
    for a in extra:
        if len(items) >= 12:
            break
        items.append(a)
        n_slur += 1
    rnd.shuffle(items)
    cache, imgs, tiles, key = {}, {}, [], []
    for n, it in enumerate(items, 1):
        plate = it["plate"]
        pg = int(it["start"].split("/")[1])
        if (plate, pg) not in cache:
            cache[(plate, pg)] = heads_and_staves(it["gdir"], plate, {pg})
        heads = cache[(plate, pg)]
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
        sp = 0.9 * max(ha[3] - ha[1], hz[3] - hz[1])          # a head is about one staff space tall
        bx0, bx1 = min(ha[0], hz[0]) - 0.3 * sp, max(ha[2], hz[2]) + 0.3 * sp
        by0, by1 = min(ha[1], hz[1]) - 2.0 * sp, max(ha[3], hz[3]) + 2.0 * sp          # the arc stands over or under its notes: both sides
        X0, X1 = int(max(0, bx0 - 5 * sp)), int(min(img.shape[1], bx1 + 5 * sp))
        Y0, Y1 = int(max(0, by0 - 3 * sp)), int(min(img.shape[0], by1 + 3 * sp))
        im = cv2.cvtColor(img[Y0:Y1, X0:X1].copy(), cv2.COLOR_GRAY2BGR)
        cv2.rectangle(im, (int(bx0 - X0), int(by0 - Y0)), (int(bx1 - X0), int(by1 - Y0)), (0, 140, 255), 2)
        s = min(1.0, 900.0 / im.shape[1])
        im = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(out / ("%02d.png" % n)), im)
        tiles.append((n, im))
        key.append(dict(tile=n, plate=plate, page=pg, kind=it["kind"], start=it["start"], stop=it["stop"], why=it["why"],
                        position={"page": pg, "box_page_px": [round(bx0), round(by0), round(bx1), round(by1)]}))
    json.dump(dict(question=QUESTION, seed=seed, rule=__doc__.split("RULE: ")[1].split("QUESTION")[0].strip(), slurs=n_slur, tiles=key), open(keyp, "w"), indent=1)
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
    print(len(tiles), "tiles (", n_slur, "slurs ) ->", out)


if __name__ == "__main__":
    main()
