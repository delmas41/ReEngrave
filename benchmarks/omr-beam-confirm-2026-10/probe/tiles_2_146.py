"""ROADMAP 2.146 -- blind tiles of every head whose duration the stem-tip rule changed (replay_score_2_146 outputs).
Blue box = the note asked about; nothing else of ours drawn. Shuffled; hidden key beside the tiles' parent.
usage: tiles_2_146.py OUTDIR KEY.json DOC:PDF:SCORE.json [DOC:PDF:SCORE.json ...]"""
import json, random, sys
import fitz
from PIL import Image, ImageDraw, ImageFont
OUT, KEY = sys.argv[1], sys.argv[2]
import os; os.makedirs(OUT, exist_ok=True)
items = []
for spec in sys.argv[3:]:
    doc, pdf, score = spec.split(":")
    for r in json.load(open(score)):
        if r["on"][2] in ("stem_tip_reads_no_beam", "stem_tip_reads_a_beam") and r["off"] != r["on"] and r["bbox"]:
            items.append(dict(doc=doc, pdf=pdf, glyph=r["glyph"], bbox=r["bbox"], off=r["off"], on=r["on"]))
random.Random(2146).shuffle(items)
pages = {}
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 64)
except Exception:
    font = ImageFont.load_default()
key = []
for n, it in enumerate(items, 1):
    page = int(it["glyph"].split("/")[1])
    k = (it["pdf"], page)
    if k not in pages:
        d = fitz.open(it["pdf"]); pix = d[page].get_pixmap(dpi=600, alpha=False)
        pages[k] = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    im = pages[k]
    x0, y0, x1, y1 = it["bbox"]
    px, py = 260, 300
    c = im.crop((int(x0 - px), int(y0 - py), int(x1 + px), int(y1 + py))).copy()
    dr = ImageDraw.Draw(c)
    dr.rectangle((px - 6, py - 6, px + (x1 - x0) + 6, py + (y1 - y0) + 6), outline=(31, 111, 235), width=4)
    if it["doc"] == "litolff":   # the Litolff plate is engraved smaller: same 600 dpi, half the staff space on screen
        c = c.resize((c.width * 2, c.height * 2), Image.LANCZOS)
    t = Image.new("RGB", (c.width, c.height + 90), "white"); t.paste(c, (0, 90))
    ImageDraw.Draw(t).text((10, 8), f"Tile {n}", fill=(0, 0, 0), font=font)
    t.save(f"{OUT}/tile_{n:02d}.png")
    key.append(dict(n=n, **{k2: it[k2] for k2 in ("doc", "glyph", "bbox", "off", "on")}))
json.dump(key, open(KEY, "w"), indent=1)
json.dump({"question": "What is the written value of the note in the blue box (4, 8, 16 ...)?", "tiles": len(key),
           "blue": "the note asked about", "nothing else drawn": True}, open(f"{OUT}/manifest.json", "w"), indent=1)
print(len(key), "tiles")
