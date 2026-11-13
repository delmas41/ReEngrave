"""ROADMAP 2.305 r4: blind tiles of arcs WRITTEN across a system break -- both halves in one tile: the end of the first system (its last note's staff, from the note to
the system's right edge) above, the start of the next system (the same instrument's staff, from the left margin to the second note) below. One thin orange box on each
end note, sized to the note; nothing else. Seeded order; key outside the tile folder.

    python3 tiles_cross_2305.py OUT_DIR KEY_JSON SEED PLATE:WORK:GATHERWORK ...
QUESTION: "Top strip: the end of one system; bottom strip: the start of the next, same instrument. Is there one arc from the boxed note on top to the boxed note
below? If yes, tie or slur?"
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
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-arc-binding-2026-10" / "page-ink-2026-11" / "step2"))
import arcs as A  # noqa: E402
from tools.omr.staged import lane_report as L  # noqa: E402
from tools.omr.staged.judged import iter_array  # noqa: E402

QUESTION = ("Top strip: the end of one system; bottom strip: the start of the next, same instrument. Is there one arc from the boxed note on top to the boxed note "
            "below? If yes, tie or slur?")


def main():
    out, keyp, seed = pathlib.Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    items, gws = [], {}
    for spec in sys.argv[4:]:
        plate, work, gw = spec.split(":")
        gws[plate] = gw
        for a in A.arcs_of_xml((pathlib.Path(work) / ("%s.on.musicxml" % plate)).read_text()):
            if a["start"].split("/")[1:3] != a["stop"].split("/")[1:3]:
                items.append(dict(a, plate=plate))
    rnd = random.Random(seed)
    rnd.shuffle(items)
    items = items[:12]
    boxes, imgs, tiles, key = {}, {}, [], []
    for plate in {i["plate"] for i in items}:
        pages = {int(k.split("/")[1]) for i in items if i["plate"] == plate for k in (i["start"], i["stop"])}
        for o in iter_array(pathlib.Path(gws[plate]) / ("%s.on.gathered.record.json" % plate), "observations"):
            if o["quantity"] == "glyph_box" and L.page_of(o["subject"]) in pages and (o.get("detail") or {}).get("category") == "notehead":
                boxes[(plate, o["subject"])] = o["detail"]["bbox_page_px"]

    def page_img(plate, pg):
        if (plate, pg) not in imgs:
            doc = fitz.open(str(L.LIB / L.PLATES[plate]["pdf"]))
            pix = doc[pg].get_pixmap(dpi=600, colorspace=fitz.csGRAY)
            imgs[(plate, pg)] = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w)
        return imgs[(plate, pg)]

    W = 1100
    for n, it in enumerate(items, 1):
        plate = it["plate"]
        ba, bz = boxes.get((plate, it["start"])), boxes.get((plate, it["stop"]))
        if not ba or not bz:
            print("no head box, no tile:", it)
            continue
        strips = []
        for k, b, which in ((it["start"], ba, "end"), (it["stop"], bz, "start")):
            img = page_img(plate, int(k.split("/")[1]))
            sp = 0.9 * (b[3] - b[1])
            if which == "end":
                x0, x1 = int(max(0, b[0] - 8 * sp)), img.shape[1]
            else:
                x0, x1 = 0, int(min(img.shape[1], b[2] + 8 * sp))
            y0, y1 = int(max(0, b[1] - 6 * sp)), int(min(img.shape[0], b[3] + 6 * sp))
            im = cv2.cvtColor(img[y0:y1, x0:x1].copy(), cv2.COLOR_GRAY2BGR)
            cv2.rectangle(im, (int(b[0] - x0 - 3), int(b[1] - y0 - 3)), (int(b[2] - x0 + 3), int(b[3] - y0 + 3)), (0, 140, 255), 2)
            s = W / im.shape[1]
            im = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            strips.append(im)
        tile = np.vstack([strips[0], np.full((16, W, 3), 160, np.uint8), strips[1]])
        cv2.imwrite(str(out / ("%02d.png" % n)), tile)
        tiles.append((n, tile))
        key.append(dict(tile=n, plate=plate, kind=it["kind"], start=it["start"], stop=it["stop"], part=it.get("part")))
    json.dump(dict(question=QUESTION, seed=seed, tiles=key), open(keyp, "w"), indent=1)
    cells = []
    for n, im in tiles:
        band = np.full((70, W, 3), 255, np.uint8)
        cv2.putText(band, str(n), (6, 58), cv2.FONT_HERSHEY_SIMPLEX, 2.2, (0, 0, 0), 5)
        cells.append(np.vstack([band, im, np.full((14, W, 3), 120, np.uint8)]))
    rows = []
    for i in range(0, len(cells), 3):
        row = cells[i:i + 3]
        hmax = max(c.shape[0] for c in row)
        row = [np.vstack([c, np.full((hmax - c.shape[0], W, 3), 255, np.uint8)]) if c.shape[0] < hmax else c for c in row]
        while len(row) < 3:
            row.append(np.full((hmax, W, 3), 255, np.uint8))
        rows.append(np.hstack(row))
    if rows:
        cv2.imwrite(str(out / "sheet.png"), np.vstack(rows))
    print(len(tiles), "tiles ->", out)


if __name__ == "__main__":
    main()
