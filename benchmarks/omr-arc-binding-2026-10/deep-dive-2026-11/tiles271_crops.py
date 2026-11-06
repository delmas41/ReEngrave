"""ANNOTATED crops for the 2.271 tile question (a control for me, not a tile for Sean): orange = the detector piece box(es) of the curve that bound the pair,
blue = the traced curve's extent, green = the two heads the pair names. python3 tiles271_crops.py OUTDIR"""
import json
import pathlib
import sys

from PIL import ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import crops as C
import ledger as LG

D = pathlib.Path("scratch/dd")
out = pathlib.Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
tiles = json.load(open(D / "tiles271.json"))
for t in tiles:
    plate, page = t["plate"], t["page"]
    dump = json.load(open(D / ("%s.r1closest.arcs.json" % plate)))
    heads = {h["subject"]: h["box"] for h in dump["heads"]}
    a, b = t["pair"]
    boxes = [heads[a], heads[b]] + [list(x) for x in t["boxes"]]
    x0 = min(x[0] for x in boxes)
    y0 = min(x[1] for x in boxes)
    x1 = max(x[2] for x in boxes)
    y1 = max(x[3] for x in boxes)
    sp = t["sp"][0]
    im = C.page_image(plate, page)
    win = (int(x0 - 4 * sp), int(y0 - 7 * sp), int(x1 + 4 * sp), int(y1 + 7 * sp))
    c = im.crop(win).copy()
    d = ImageDraw.Draw(c)
    for hb in (heads[a], heads[b]):
        d.rectangle((hb[0] - win[0], hb[1] - win[1], hb[2] - win[0], hb[3] - win[1]), outline=(0, 170, 0), width=2)
    for bx in t["boxes"]:
        d.rectangle((bx[0] - win[0], bx[1] - win[1], bx[2] - win[0], bx[3] - win[1]), outline=(255, 140, 0), width=2)
    for (xl, xr), bx in zip(t["extents"], t["boxes"]):
        if xl is not None:
            yy = (bx[1] + bx[3]) / 2 - win[1]
            d.line((xl - win[0], yy + 6, xr - win[0], yy + 6), fill=(0, 90, 255), width=3)
    if c.width > 1500:
        c = c.resize((1500, int(c.height * 1500 / c.width)))
    name = "tile%02d_%s_p%d.png" % (t["tile"], plate, page)
    c.save(out / name)
    print(name, c.size)
