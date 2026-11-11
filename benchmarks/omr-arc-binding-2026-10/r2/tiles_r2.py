"""arcs-r2: blind tiles for Sean from a selection file, drawn from the WRITTEN binding (the replay's `<plate>.on.extra.json`: the two heads the exported arc is hung on).

    python3 tiles_r2.py SELECTION.json OUT_DIR KEY_JSON
SELECTION.json = {"seed": n, "rule": "...", "items": [{"plate", "pickdir", "page", "run", "why"}]} in tile order (already seeded-shuffled by the caller or ordered by the rule).
A tile = one staff strip of the printed page (600 dpi) wide enough for BOTH ends of the arc and the notes it binds (strip is two staves tall where the arc's ink and its notes could be on
neighbouring staves), ONE thin orange box round the arc's own ink (the page-ink run), a small tick (a short vertical bar under the head, green start / magenta stop) at each bound head --
nothing else. The key (why each tile is there, the written kind) goes to KEY_JSON, never next to the tiles. sheet.png: 3 columns, large numbers, no insets.
Question: "Is this one arc? Does it start and stop on the two ticked notes? Tie or slur?"
"""
import json
import pathlib
import sys

import cv2
import fitz
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import lane_report as L  # noqa: E402


def load(plate, pickdir, pages):
    heads, runs, staves = {}, {}, {}
    rp = pathlib.Path(pickdir) / ("%s.on.gathered.record.json" % plate)
    from tools.omr.staged.judged import iter_array
    for o in iter_array(rp, "observations"):
        s = o["subject"]
        pg = L.page_of(s)
        if pg not in pages:
            continue
        q = o["quantity"]
        if q == "glyph_box" and (o.get("detail") or {}).get("category") == "notehead":
            heads[s] = o["detail"]["bbox_page_px"]
        elif q == "page_arc" and o["value"] == "run":
            runs[(pg, o["detail"]["ordinal"])] = o["detail"]
    ex = {}
    for v in json.load(open(pathlib.Path(pickdir) / ("%s.on.extra.json" % plate))):
        for r in v["detail"]["runs"]:
            ex.setdefault((int(v["subject"].split("/")[1]), r["ordinal"]), []).append(r)
    return heads, runs, ex


def main():
    sel = json.load(open(sys.argv[1]))
    out = pathlib.Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    cache, imgs, tiles, key = {}, {}, [], []
    for n, it in enumerate(sel["items"], 1):
        plate, pg, rn = it["plate"], int(it["page"]), int(it["run"])
        if (plate, it["pickdir"]) not in cache:
            pages = {int(x["page"]) for x in sel["items"] if x["plate"] == plate and x["pickdir"] == it["pickdir"]}
            cache[(plate, it["pickdir"])] = load(plate, it["pickdir"], pages)
        heads, runs, ex = cache[(plate, it["pickdir"])]
        d = runs[(pg, rn)]
        es = [e for e in ex[(pg, rn)] if e.get("status") == "written"]
        e = es[it.get("piece") or 0] if es else None
        if e is None:
            print("not written, no tile:", it)
            continue
        if (plate, pg) not in imgs:
            imgs.clear()
            doc = fitz.open(str(L.LIB / L.PLATES[plate]["pdf"]))
            pix = doc[pg].get_pixmap(dpi=600, colorspace=fitz.csGRAY)
            imgs[(plate, pg)] = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w)
        img = imgs[(plate, pg)]
        pts = np.array(d["points"], float)
        sp = float(d["space_page_px"])
        hs = [heads[k] for k in (e["start"], e["stop"]) if k in heads]
        xs = list(pts[:, 0]) + [h[0] for h in hs] + [h[2] for h in hs]
        ys = list(pts[:, 1]) + [h[1] for h in hs] + [h[3] for h in hs]
        X0, X1 = int(max(0, min(xs) - 4 * sp)), int(min(img.shape[1], max(xs) + 4 * sp))
        Y0, Y1 = int(max(0, min(ys) - 4 * sp)), int(min(img.shape[0], max(ys) + 4 * sp))
        im = cv2.cvtColor(img[Y0:Y1, X0:X1].copy(), cv2.COLOR_GRAY2BGR)
        bx0, by0, bx1, by1 = pts[:, 0].min() - 4, pts[:, 1].min() - 0.5 * sp, pts[:, 0].max() + 4, pts[:, 1].max() + 0.5 * sp
        cv2.rectangle(im, (int(bx0 - X0), int(by0 - Y0)), (int(bx1 - X0), int(by1 - Y0)), (0, 140, 255), 2)
        for k, col in ((e["start"], (0, 170, 0)), (e["stop"], (210, 0, 210))):
            if k in heads:
                h = heads[k]
                cx = int((h[0] + h[2]) / 2 - X0)
                y = int(h[3] - Y0) + 6
                cv2.line(im, (cx, y), (cx, y + 18), col, 3)
                cv2.line(im, (cx - 8, y + 18), (cx + 8, y + 18), col, 3)
        s = min(0.75, 900.0 / im.shape[1])
        im = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(out / ("%02d.png" % n)), im)
        tiles.append((n, im))
        key.append(dict(tile=n, plate=plate, page=pg, run=rn, why=it.get("why"), kind=e.get("kind"), start=e["start"], stop=e["stop"]))
    json.dump(dict(question="Is this one arc? Does it start and stop on the two ticked notes? Tie or slur?", seed=sel.get("seed"), rule=sel.get("rule"), tiles=key), open(sys.argv[3], "w"), indent=1)
    # sheet: 3 columns, large numbers, no insets
    W = 900
    cells = []
    for n, im in tiles:
        s = W / im.shape[1]
        im2 = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
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
