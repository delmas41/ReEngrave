"""2.306 r13 blind tiles for Sean: 12 heads, 6 per plate, a seeded random sample (seed 2306013) of ALL page heads the NEW stem reader considered on
the frozen pages -- not filtered by outcome. One staff, the print as it is; a thin orange box round the STEM INK exactly as NEW holds it (the box of
the page strokes its stem claim names; no box where NEW took none) and a small orange tick under the head. Nothing else drawn. Key OUTSIDE the folder.
Usage (cwd = repo root): tiles.py OUTDIR KEY.json"""
import sys, os, json, random, math
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import look as LK
from PIL import Image, ImageDraw, ImageFont

out, keyp = sys.argv[1], sys.argv[2]
os.makedirs(os.path.join(out, "tiles"), exist_ok=True)
rng = random.Random(2306013)
ORANGE = (255, 130, 0)
picks = []
for plate in ("lit", "bra"):
    D = load(plate)
    heads = {}
    for g, r in sorted(D["pstem"].items()):
        if r.get("head") is not None and g in D["heads"]:
            heads.setdefault((pg(g), int(r["head"])), g)
    for k in rng.sample(sorted(heads), 6):
        picks.append((plate, heads[k], D))
rng.shuffle(picks)
key, thumbs = [], []
for i, (plate, g, D) in enumerate(picks, 1):
    p = pg(g)
    im = LK.page_img(plate, p).copy()
    hb = D["heads"][g]["box"]
    lines = D["staff_lines"][staff_of(g)]
    sp = (lines[-1] - lines[0]) / 4.0
    o, n = old_answer(D, g), new_answer(D, g)
    sb = n["row"].get("stem_box") if n["read"] else None
    cx = (hb[0] + hb[2]) / 2
    top = min(lines[0], hb[1], sb[1] if sb else hb[1]) - 2.5 * sp
    bot = max(lines[-1], hb[3], sb[3] if sb else hb[3]) + 2.5 * sp
    x0, x1, y0, y1 = int(cx - 7 * sp), int(cx + 7 * sp), int(top), int(bot)
    x0, y0 = max(0, x0), max(0, y0)
    z = max(2, int(math.ceil(450.0 / (y1 - y0))))
    tile = im.crop((x0, y0, x1, y1)).resize(((x1 - x0) * z, (y1 - y0) * z), Image.LANCZOS)
    d = ImageDraw.Draw(tile)
    if sb:
        d.rectangle([(sb[0] - 2 - x0) * z, (sb[1] - 1 - y0) * z, (sb[2] + 2 - x0) * z, (sb[3] + 1 - y0) * z], outline=ORANGE, width=2)
    tx, ty = (cx - x0) * z, (hb[3] - y0) * z + 0.2 * sp * z
    a = 0.4 * sp * z
    d.line([tx - a, ty + a, tx, ty, tx + a, ty + a], fill=ORANGE, width=3)
    tile.save(os.path.join(out, "tiles", "tile%02d.png" % i))
    thumbs.append(tile)
    members = None
    for c in D["claims"][p]:
        if c.get("reader") == "cv_page_stems" and c.get("owner") == "stem" and c["value"] == n["stroke"]:
            members = c.get("page_strokes")
    key.append(dict(tile=i, plate=NAME[plate], page=p, glyph=g, cls=D["cls"].get(g), head_box_page_px=[round(v, 1) for v in hb],
                    old=dict(stem=bool(o["stem"]), why=o["why"], direction=o["direction"], direction_why=o["dir_why"]),
                    new=dict(stem=bool(n["read"]), reason=n["how"], direction=n["direction"], stem_box_page_px=sb, page_strokes=members),
                    written_off=g in D["written_off"], written_on=g in D["written_on"]))
W = max(t.width for t in thumbs)
rows = (len(thumbs) + 1) // 2
hs = [max(thumbs[2 * r].height, thumbs[2 * r + 1].height if 2 * r + 1 < len(thumbs) else 0) for r in range(rows)]
sheet = Image.new("RGB", (2 * (W + 20), sum(hs) + 50 * rows), "white")
dr = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 34)
except Exception:
    font = None
y = 0
for r in range(rows):
    for cidx in range(2):
        k = 2 * r + cidx
        if k >= len(thumbs):
            continue
        x = cidx * (W + 20)
        dr.text((x + 6, y + 6), str(k + 1), fill=(0, 0, 0), font=font)
        sheet.paste(thumbs[k], (x, y + 46))
    y += hs[r] + 50
sheet.save(os.path.join(out, "sheet.png"))
json.dump(dict(question="The tick marks a notehead. Is the boxed ink all of that note's stem -- yes, only part, not its stem -- or, if there is no box, does that note have a stem (up or down)?",
               seed=2306013, drawn_from="all page heads the page stem reader considered on the frozen pages of the r12 gather, 6 per plate, not filtered by outcome",
               tiles=key), open(keyp, "w"), indent=1)
for k in key:
    print(k["tile"], k["plate"], k["glyph"], "| OLD", k["old"]["why"], k["old"]["direction"], "| NEW", k["new"]["reason"], k["new"]["direction"], k["new"]["stem_box_page_px"])
