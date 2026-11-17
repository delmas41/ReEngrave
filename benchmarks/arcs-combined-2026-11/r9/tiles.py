"""2.305 r9 -- 12 blind tiles for Sean, drawn at random (seed) from what the lane CHANGED (changes.py), 6 per plate where possible. Each tile: the arc's
ink as the reader held it boxed (thin orange), a small tick under each of the two notes the file joined (or joined before, for a removed arc), both ends
in the crop, nothing else drawn, >= 460 px tall. sheet.png two per row; the key goes OUTSIDE the tile folder.

    python3 tiles.py OUTDIR KEY.json SEED chg-brahms.json chg-litolff.json
"""
import json
import os
import random
import sys

sys.path.insert(0, os.getcwd())
from PIL import Image, ImageDraw  # noqa: E402

from tools.omr.preprocessing import render_page  # noqa: E402

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/"
PDF = {"brahms": LIB + "brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
       "litolff": LIB + "beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"}
ORANGE = (255, 120, 0)
MIN_H = 460


def main():
    out, key_path, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
    pools = [json.load(open(p)) for p in sys.argv[4:]]
    rng = random.Random(seed)
    drawn = []
    for pool in pools:
        ok = [r for r in pool if r.get("ink")]
        drawn += rng.sample(ok, min(6, len(ok)))
    if len(drawn) < 12:          # top up from whichever plate has more
        rest = [r for pool in pools for r in pool if r.get("ink") and r not in drawn]
        drawn += rng.sample(rest, min(12 - len(drawn), len(rest)))
    rng.shuffle(drawn)
    os.makedirs(out, exist_ok=True)
    pages, tiles, key = {}, [], []
    for i, r in enumerate(drawn, 1):
        pk = (r["plate"], r["page"])
        if pk not in pages:
            pages[pk] = Image.fromarray(render_page(PDF[r["plate"]], r["page"], dpi=600).rgb).convert("RGB")
        im = pages[pk].copy()
        dr = ImageDraw.Draw(im)
        ink = r["ink"]
        dr.rectangle([ink[0] - 4, ink[1] - 4, ink[2] + 4, ink[3] + 4], outline=ORANGE, width=2)
        for bx in (r["a_box"], r["b_box"]):
            cx = (bx[0] + bx[2]) / 2.0
            dr.line([(cx, bx[3] + 14), (cx, bx[3] + 36)], fill=ORANGE, width=3)
        xs = [ink[0], ink[2], r["a_box"][0], r["a_box"][2], r["b_box"][0], r["b_box"][2]]
        ys = [ink[1], ink[3], r["a_box"][1], r["b_box"][3] + 40, r["a_box"][3] + 40]
        x0, x1 = min(xs) - 140, max(xs) + 140
        y0, y1 = min(ys) - 90, max(ys) + 90
        if y1 - y0 < MIN_H:
            c = (y0 + y1) / 2.0
            y0, y1 = c - MIN_H / 2.0, c + MIN_H / 2.0
        if y0 < 0:
            y0, y1 = 0, y1 - y0
        if y1 > im.height:
            y0, y1 = y0 - (y1 - im.height), im.height
        tile = im.crop((int(max(0, x0)), int(max(0, y0)), int(min(im.width, x1)), int(min(im.height, y1))))
        tile.save(os.path.join(out, "tile_%02d.png" % i))
        tiles.append(tile)
        key.append(dict(tile=i, **{k: r[k] for k in ("plate", "page", "change", "a", "b", "before", "after", "src", "ink", "ink_from")}))
    # sheet, two per row, each scaled to one width
    W = 1100
    sc = [t.resize((W, max(1, int(t.height * W / t.width)))) for t in tiles]
    rows = [sc[j:j + 2] for j in range(0, len(sc), 2)]
    H = sum(max(t.height for t in row) + 40 for row in rows)
    sheet = Image.new("RGB", (2 * W + 30, H), "white")
    dr = ImageDraw.Draw(sheet)
    y = 0
    for j, row in enumerate(rows):
        for k, t in enumerate(row):
            dr.text((k * (W + 30) + 6, y + 6), "Tile %d" % (2 * j + k + 1), fill=(0, 0, 0))
            sheet.paste(t, (k * (W + 30), y + 30))
        y += max(t.height for t in row) + 40
    sheet.save(os.path.join(out, "sheet.png"))
    with open(os.path.join(out, "README.txt"), "w") as fh:
        fh.write("2.305 r9 arc tiles (seed %d). The orange box is the ink the reader read as ONE arc; the two orange ticks are under the two notes the "
                 "file joins with it (or joined before this change).\nQuestion per tile: is the boxed ink one arc from the first ticked note to the "
                 "second? If yes, a tie or a slur? If not, what is it?\n" % seed)
    json.dump(dict(seed=seed, tiles=key), open(key_path, "w"), indent=1)
    print("tiles", len(tiles), [(k["tile"], k["plate"], k["change"]) for k in key])


if __name__ == "__main__":
    main()
