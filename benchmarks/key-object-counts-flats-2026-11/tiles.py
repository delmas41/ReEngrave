"""2.302 blind staff-start tiles: clef + the whole key signature + the first note, a thin box on the signature, a LARGE number, nothing else.
    PYTHONPATH=. python3 benchmarks/key-object-counts-flats-2026-11/tiles.py OUT_DIR CASES.json
CASES.json: [{"plate", "staff": "p/s/li", "rule": why this tile, "off": ..., "on": ...}] in tile order; key.json beside the sheet carries the rest.
The box is the signature's own span (clef edge to the last counted slot's right edge + 0.3 space) from the ON replay row; pixels come from the page render."""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

from tools.omr.staged import lane_report as LR
from tools.omr.preprocessing import render_page


def font(sz):
    for f in ("/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf"):
        try:
            return ImageFont.truetype(f, sz)
        except Exception:
            pass
    return ImageFont.load_default()


def main():
    out, cases_p = sys.argv[1:3]
    cases = json.load(open(cases_p))
    os.makedirs(out, exist_ok=True)
    on = {pl: json.load(open(p)) for pl, p in cases[0]["on_files"].items()}
    ex = {pl: json.load(open(p)) for pl, p in cases[0]["ex_files"].items()}
    cache, tiles, key = {}, [], {}
    for n, c in enumerate(cases, 1):
        pl, st = c["plate"], c["staff"]
        pg = int(st.split("/")[0])
        if (pl, pg) not in cache:
            cache[(pl, pg)] = Image.fromarray(render_page(str(LR.LIB / LR.PLATES[pl]["pdf"]), pg, dpi=600).rgb).convert("RGB")
        im = cache[(pl, pg)]
        row = on[pl][st]
        sp = row["space"]
        # staff lines / clef edge: from the saved claimed-area row (area x0 = x_start, y from the area's padded extent)
        a = row["areas"][0][0]
        x_start = a[0]
        y_mid = (a[1] + a[3]) / 2.0
        x0, x1 = int(x_start - 4.2 * sp), int(x_start + 11 * sp)
        y0, y1 = int(y_mid - 4.0 * sp), int(y_mid + 4.0 * sp)
        t = im.crop((x0, y0, x1, y1)).copy()
        d = ImageDraw.Draw(t)
        bx0, bx1 = x_start - 0.2 * sp - x0, a[2] - x0
        d.rectangle([bx0, a[1] - y0, bx1, a[3] - y0], outline=(255, 140, 0), width=2)
        d.text((8, 4), str(n), fill=(200, 0, 0), font=font(int(1.6 * sp)))
        t.save(os.path.join(out, "tile_%02d.png" % n))
        tiles.append(t)
        key[str(n)] = {k: v for k, v in c.items() if k not in ("on_files", "ex_files")}
    W, H = max(t.width for t in tiles), max(t.height for t in tiles)
    cols = 3
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (W + 10), rows * (H + 10)), "white")
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * (W + 10), (i // cols) * (H + 10)))
    sheet.save(os.path.join(out, "sheet.png"))
    json.dump(key, open(os.path.join(out, "key.json"), "w"), indent=1)
    print(len(tiles), "tiles ->", out)


if __name__ == "__main__":
    main()
