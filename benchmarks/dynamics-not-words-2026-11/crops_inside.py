"""ROADMAP 2.303: plain crops (no tint, claim box thin red, the READ word's box thin green) of every NON-compound dynamic claim whose centre lies inside a READ word's box -- the 11 cases to classify by eye.

    python3 benchmarks/dynamics-not-words-2026-11/crops_inside.py OUT.png litolff=REC:8 brahms=REC:0 brahms=REC:14
"""
import os
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
UNIT = {"litolff": 15.75, "brahms": 32.0}


def main():
    from PIL import Image, ImageDraw, ImageFont
    from tools.omr.staged import claim_readout as CR
    from tools.omr.preprocessing import render_page
    import inside_word as IW
    out = sys.argv[1]
    tiles = []
    font = ImageFont.load_default(size=48)
    for spec in sys.argv[2:]:
        plate, rest = spec.split("=", 1)
        rec, page = rest.rsplit(":", 1)
        page = int(page)
        items = [it for it in IW.analyse(rec, page) if it["inside_read_word"] and not it["compound_of"]]
        if not items:
            continue
        rows = CR.read_rows(CR.resolve_source(rec), [page])
        pdf = CR.LIB / CR.edition_info(rows)["edition_path"]
        rgb = np.array(render_page(str(pdf), page, dpi=600).rgb.copy())
        u = UNIT[plate]
        for it in items:
            w = it["inside_read_word"][0]
            b = it["box"]
            wb = w["box"]
            x0, x1 = max(0, int(min(wb[0], b[0]) - 1.5 * u)), int(max(wb[2], b[2]) + 1.5 * u)
            y0, y1 = max(0, int(min(wb[1], b[1]) - 1.5 * u)), int(max(wb[3], b[3]) + 1.5 * u)
            im = Image.fromarray(rgb[y0:y1, x0:x1].copy())
            d = ImageDraw.Draw(im)
            d.rectangle([wb[0] - x0, wb[1] - y0, wb[2] - x0, wb[3] - y0], outline=(0, 160, 0), width=2)
            d.rectangle([b[0] - x0, b[1] - y0, b[2] - x0, b[3] - y0], outline=(230, 0, 0), width=2)
            im = im.resize((640, int(640 * im.height / im.width)))
            tiles.append((im, "%s p%d %s in %r" % (plate, page, it["text"] or it["letter"], w["text"])))
    h = max(t.height for t, _ in tiles) + 60
    sheet = Image.new("RGB", (3 * 646, ((len(tiles) + 2) // 3) * h), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for n, (t, cap) in enumerate(tiles):
        x, y = (n % 3) * 646, (n // 3) * h
        d.text((x + 4, y + 2), "%d %s" % (n + 1, cap), fill=(0, 0, 0), font=ImageFont.load_default(size=22))
        sheet.paste(t, (x, y + 30))
    sheet.save(out)
    print(len(tiles), "crops")


main()
