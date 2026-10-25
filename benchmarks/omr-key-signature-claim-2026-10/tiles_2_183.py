"""2.183 blind tiles: 12 under OUTROOT/2.183-key-signature/ (ONE orange where-to-look box each, nothing else of ours drawn, plus a README);
the KEY goes to OUTROOT/2.183-key.json (outside the tiles folder). usage: tiles_2_183.py OUTROOT POPJSON SLICEDIR
Pool: POPJSON (from causes_2_183.py): Litolff cell-0 boxes written as RESTS that stand in the key-signature columns (the cause population the
claim as built does not change -- shown to Sean to CHECK THE COUNT, CLAUDE rule 7) -- 9 drawn with a fixed seed; plus 3 controls: eighth rests
printed AFTER the meter in a header cell (real rests the claim must keep). Orange (255,140,0) is a neutral marker: it means 'look here'."""
import json
import os
import random
import sys

sys.path.insert(0, ".")
from PIL import Image, ImageDraw  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402

OUTROOT, POP, SD = sys.argv[1:4]
TILES = os.path.join(OUTROOT, "2.183-key-signature")
KEY = os.path.join(OUTROOT, "2.183-key.json")
PDF = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
       "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf")
rnd = random.Random(2183)
pop = json.load(open(POP))
cause = [(r["g"], r["box"], r["cls"]) for r in pop["population"]]
controls = [(r["g"], r["box"], r["cls"]) for r in pop["controls"]]
rnd.shuffle(cause)
rnd.shuffle(controls)
items = [(g, b, c, "cause_population") for g, b, c in cause[:9]] + [(g, b, c, "control_real_rest_after_the_meter") for g, b, c in controls[:3]]
rnd.shuffle(items)
os.makedirs(TILES, exist_ok=True)
for f in os.listdir(TILES):
    if f.startswith("tile_"):
        os.remove(os.path.join(TILES, f))
rast, key = {}, []
for n, (g, b, cls, kind) in enumerate(items, 1):
    pg = int(g.split("/")[1])
    if pg not in rast:
        rast.clear()
        rast[pg] = Image.fromarray(render_page(PDF, pg, dpi=600).rgb).convert("RGB")
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    u = 15.75
    x0, y0, x1, y1 = int(cx - 8 * u), int(cy - 5 * u), int(cx + 6 * u), int(cy + 5 * u)
    crop = rast[pg].crop((x0, y0, x1, y1)).copy()
    rect = [round(b[0] - x0), round(b[1] - y0), round(b[2] - x0), round(b[3] - y0)]
    ImageDraw.Draw(crop).rectangle(rect, outline=(255, 140, 0), width=2)
    crop.save(os.path.join(TILES, "tile_%02d.png" % n))
    key.append(dict(tile=n, glyph=g, cls=cls, kind=kind, page=pg, box_page_px=b, crop_origin=[x0, y0], rect_in_tile=rect))
open(os.path.join(TILES, "README.md"), "w").write(
    "# 2.183 review\n\nEach picture is a piece of a scanned score page (Litolff, Beethoven 5) with ONE orange box on it and nothing else drawn. "
    "The orange box only says where to look; it means nothing else.\n\n**Question, for every tile:** is the thing in the orange box a rest, a note, "
    "or part of the key signature (a flat)? Answer by tile number, for example `1 flat, 2 rest, 3 note`.\n")
json.dump(key, open(KEY, "w"), indent=1)
tiles = sorted(f for f in os.listdir(TILES) if f.startswith("tile_"))
assert len(tiles) == len(key) == 12
for k in key:
    bx = k["box_page_px"]
    assert k["rect_in_tile"] == [round(bx[0] - k["crop_origin"][0]), round(bx[1] - k["crop_origin"][1]),
                                 round(bx[2] - k["crop_origin"][0]), round(bx[3] - k["crop_origin"][1])]
print("tiles", len(tiles), {k: sum(1 for i in key if i["kind"] == k) for k in {i["kind"] for i in key}})
