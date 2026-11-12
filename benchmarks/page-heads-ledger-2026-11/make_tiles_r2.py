"""ROADMAP 2.290 build round 2 -- 12 BLIND tiles on the page heads' claimed ink (Sean, 2026-11-11: round 1's tiles were "very small and zoomed in, so I can't
always see the end of the stems").

    PYTHONPATH=. python3 benchmarks/page-heads-ledger-2026-11/make_tiles_r2.py OUTDIR PICKS.json

PICKS.json: a list of {plate, page, box (the claimed ink's extent, or the refused ink's, page px), staff_lines [top line y, bottom line y] (page px, the head's own
staff), kind, why, ...}, already in the order to show (lost / changed notes first, then every place a new refusal fired, then newly claimed heads; the caller
excludes round 1's places). Each tile: ONE staff, its whole height plus `MARGIN_SP` above and below (so a stem, flag or beam of the boxed note is whole),
`HALF_WIDTH_SP` either side of the box (about a bar), the PRINTED page as it is, and ONE thin orange box at the claimed ink's own extent. Nothing else is drawn:
no tint, no arrow, no inset. The sheet is 3 columns with LARGE tile numbers; key.json (everything we know) is written beside the tiles folder.
QUESTION: "Is the boxed ink ONE notehead, and only that notehead? If not, what is it?"
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
PDF = {"litolff": LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
MARGIN_SP = 7.0
HALF_WIDTH_SP = 11.0
TILE_W = 700


def main(out, picks_path):
    from tools.omr.preprocessing import render_page
    picks = json.load(open(picks_path))[:12]
    tdir = os.path.join(out, "tiles")
    os.makedirs(tdir, exist_ok=True)
    for f in os.listdir(tdir):
        os.remove(os.path.join(tdir, f))
    cache, key, ims = {}, [], []
    for n, r in enumerate(picks, 1):
        k = (r["plate"], r["page"])
        if k not in cache:
            cache.clear()
            cache[k] = Image.fromarray(render_page(PDF[r["plate"]], r["page"], dpi=600).rgb).convert("RGB")
        im = cache[k]
        top, bot = r["staff_lines"]
        sp = (bot - top) / 4.0
        b = r["box"]
        cx = (b[0] + b[2]) / 2
        x0, x1 = max(0, int(cx - HALF_WIDTH_SP * sp)), min(im.width, int(cx + HALF_WIDTH_SP * sp))
        y0, y1 = max(0, int(top - MARGIN_SP * sp)), min(im.height, int(bot + MARGIN_SP * sp))
        crop = im.crop((x0, y0, x1, y1)).copy()
        scale = TILE_W / float(crop.width)
        crop = crop.resize((TILE_W, max(1, int(crop.height * scale))), Image.LANCZOS)
        w = max(2, int(round(sp * scale / 14)))
        ImageDraw.Draw(crop).rectangle([(b[0] - x0) * scale - 1, (b[1] - y0) * scale - 1, (b[2] - x0) * scale + 1, (b[3] - y0) * scale + 1], outline=(255, 120, 0), width=w)
        crop.save(os.path.join(tdir, "tile_%02d.png" % n))
        ims.append(crop)
        key.append(dict(tile=n, crop_origin=[x0, y0], scale=scale, **r))
    cols, pad, lab = 3, 20, 70
    rows = [ims[i:i + cols] for i in range(0, len(ims), cols)]
    hs = [max(im.height for im in row) + lab for row in rows]
    sheet = Image.new("RGB", (cols * (TILE_W + pad) + pad, sum(hs) + pad * (len(rows) + 1)), "white")
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 56)
    except Exception:
        font = ImageFont.load_default()
    y, n = pad, 1
    for row, h in zip(rows, hs):
        x = pad
        for im in row:
            d.text((x, y), "Tile %d" % n, fill="black", font=font)
            sheet.paste(im, (x, y + lab))
            x += TILE_W + pad
            n += 1
        y += h + pad
    sheet.save(os.path.join(tdir, "sheet.png"))
    json.dump(key, open(os.path.join(out, "key.json"), "w"), indent=1, default=str)
    open(os.path.join(tdir, "README.md"), "w").write(
        "# 2.290 build round 2 -- noteheads claimed on the page\n\nEach picture is one whole staff of the printed score with room above and below for the stems. "
        "The thin orange box is drawn around the ink we claim (or refuse to claim); nothing else is drawn.\n\n**Question, for every tile:** Is the boxed ink ONE "
        "notehead, and only that notehead? If not, what is it?\n\nAnswer by tile number.\n")
    print("tiles", len(key), "->", tdir)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
