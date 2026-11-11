"""ROADMAP 2.290 r1 -- MY OWN crop look: a contact sheet of the dropped boxes in a `mgdup_vs_pagemark.py` output (orange = dropped box, blue = its written mate).
    PYTHONPATH=. python3 benchmarks/page-heads-ledger-2026-11/pair_sheet.py OUT.png PLATE IN.json [IN.json ...]
"""
import json
import sys

from PIL import Image, ImageDraw

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
PDF = {"litolff": LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
UNIT = {"litolff": 15.75, "brahms": 32.0}


def main(out, plate, files):
    from tools.omr.preprocessing import render_page
    rows = []
    for f in files:
        rows += json.load(open(f))
    rows.sort(key=lambda r: int(r["sub"].split("/")[1]))
    cache, tiles = {}, []
    u = UNIT[plate]
    for r in rows:
        pg = int(r["sub"].split("/")[1])
        if pg not in cache:
            cache.clear()
            cache[pg] = Image.fromarray(render_page(PDF[plate], pg, dpi=600).rgb).convert("RGB")
        im = cache[pg]
        b, m = r["box"], r["mate_box"]
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        x0, y0, x1, y1 = int(cx - 3 * u), int(cy - 2.6 * u), int(cx + 3 * u), int(cy + 2.6 * u)
        crop = im.crop((x0, y0, x1, y1)).copy()
        d = ImageDraw.Draw(crop)
        d.rectangle([m[0] - x0, m[1] - y0, m[2] - x0, m[3] - y0], outline=(0, 90, 255), width=2)
        d.rectangle([b[0] - x0, b[1] - y0, b[2] - x0, b[3] - y0], outline=(255, 140, 0), width=2)
        crop = crop.resize((330, int(330 * crop.height / crop.width)))
        ImageDraw.Draw(crop).text((3, 2), "p%d %s" % (pg, r["sub"].split("/", 2)[2]), fill=(200, 0, 0))
        tiles.append(crop)
    cols = 5
    n = (len(tiles) + cols - 1) // cols
    h = max(t.height for t in tiles)
    sheet = Image.new("RGB", (cols * 338 + 8, n * (h + 8) + 8), (255, 255, 255))
    for i, t in enumerate(tiles):
        sheet.paste(t, (8 + (i % cols) * 338, 8 + (i // cols) * (h + 8)))
    sheet.save(out)
    print(len(tiles), "->", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
