"""ROADMAP 2.176 blind tiles (<= 12): heads the flag OMR_HEAD_ON_ANOTHER_MARK newly REFUSES (replay OFF vs ON), plus 3 controls (a real head the
flag keeps: a clef box over a head the detector scored higher; a head just inside a system's first bar; a plain head).

    python3 .../tiles_2_176.py OUTDIR SLICEDIR MAX      (ONE run: tiles AND key)

Roles (never drawn; the KEY only, out/2.176/tiles-key.json): refused -- the flag stops writing this head; control -- a head the flag keeps.
Each tile: the neighbourhood, ONE blue box (#1F6FEB) on the box asked about, "Tile N". Nothing else of ours.
Question: is the thing in the blue box a notehead? If not, what is it?"""
import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402

W, SD, MAX = sys.argv[1], sys.argv[2], int(sys.argv[3])
PDFS = {
    "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
               "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
OUT, KEY = Path("out/print/2.176-review"), Path("out/2.176/tiles-key.json")
rnd = random.Random(21760)


def boxes(doc):
    bx = {}
    for p in sorted(Path(SD, doc).glob("*.observations.jsonl")):
        for line in open(p):
            o = json.loads(line)
            d = o.get("detail") or {}
            if o["quantity"] == "glyph_box" and d.get("bbox_page_px") and d.get("category") == "notehead":
                bx[o["subject"]] = d["bbox_page_px"]
    return bx


cmp_ = {d: json.load(open("%s/%s.cmp.json" % (W, d))) for d in ("brahms", "litolff")}
ctl = json.load(open("%s/controls.json" % W))          # [{doc, glyph, why}]
picks = []
refused = []
for doc in ("brahms", "litolff"):
    bx = boxes(doc)
    on = json.load(open("%s/%s.on.json" % (W, doc)))
    for g in cmp_[doc]["new"]:
        if g in bx:
            refused.append(dict(doc=doc, glyph=g, bbox=bx[g], role="refused", reason=on["refusals"][g][1]))
# at most MAX-3 refused: spread over reasons and plates
rnd.shuffle(refused)
by = {}
for r in refused:
    by.setdefault((r["doc"], r["reason"]), []).append(r)
chosen = []
while len(chosen) < MAX - len(ctl) and any(by.values()):
    for k in sorted(by):
        if by[k] and len(chosen) < MAX - len(ctl):
            chosen.append(by[k].pop())
for c in ctl:
    bx = boxes(c["doc"])
    chosen.append(dict(doc=c["doc"], glyph=c["glyph"], bbox=bx[c["glyph"]], role="control", why=c["why"]))
rnd.shuffle(chosen)
picks = chosen

OUT.mkdir(parents=True, exist_ok=True)
for old in OUT.glob("tile_*.png"):
    old.unlink()
KEY.parent.mkdir(parents=True, exist_ok=True)
SP = 33.0
BLUE = (31, 111, 235)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 44)
except OSError:
    font = ImageFont.load_default()
pages, key = {}, []
for n, p in enumerate(picks, 1):
    pg = int(p["glyph"].split("/")[1])
    if (p["doc"], pg) not in pages:
        pages[(p["doc"], pg)] = np.asarray(Image.fromarray(render_page(PDFS[p["doc"]], pg, dpi=600).rgb).convert("RGB"))
    a = pages[(p["doc"], pg)]
    x0b, y0b, x1b, y1b = p["bbox"]
    x0, y0 = int(max(x0b - 7 * SP, 0)), int(max(y0b - 5 * SP, 0))
    x1, y1 = int(min(x1b + 7 * SP, a.shape[1])), int(min(y1b + 5 * SP, a.shape[0]))
    crop = Image.fromarray(a[y0:y1, x0:x1].copy())
    crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
    pad = 4
    rect = [(x0b - x0) * 2 - pad, (y0b - y0) * 2 - pad + 70, (x1b - x0) * 2 + pad, (y1b - y0) * 2 + pad + 70]
    tile = Image.new("RGB", (crop.width, crop.height + 70), "white")
    tile.paste(crop, (0, 70))
    ImageDraw.Draw(tile).rectangle(rect, outline=BLUE, width=4)
    ImageDraw.Draw(tile).text((10, 10), "Tile %d" % n, fill=(0, 0, 0), font=font)
    tile.save(OUT / ("tile_%02d.png" % n))
    key.append(dict(n=n, crop_origin=[x0, y0], rect_in_tile=rect, **p))
json.dump(dict(question="Is the thing in the blue box a notehead? If not, what is it?", tiles=len(picks),
               blue="the box asked about", nothing_else_drawn=True), open(OUT / "manifest.json", "w"), indent=1)
json.dump({}, open(OUT / "answers.json", "w"))
(OUT / "README.md").write_text("""# 2.176 blind tiles (%d)

Each tile shows one spot with ONE blue box on it. Blue = the box asked about. Nothing else of ours is drawn.

Question for every tile: is the thing in the blue box a notehead? If not, what is it (a barline, part of a clef, an accidental,
part of a rest, a letter, something else)?

Answer into `answers.json` (tile number -> "notehead" or what it is). The key (which tiles are boxes the new rule refuses
and which are 3 plain controls, real heads the rule keeps) is `out/2.176/tiles-key.json` and is not to be read before answering.
""" % len(picks))
json.dump(key, open(KEY, "w"), indent=1)

pngs = sorted(OUT.glob("tile_*.png"))
rows = json.load(open(KEY))
assert len(pngs) == len(rows) == len(picks)
assert [int(p.stem.split("_")[1]) for p in pngs] == [r["n"] for r in rows] == list(range(1, len(picks) + 1))
for png, r in zip(pngs, rows):
    im = np.asarray(Image.open(png).convert("RGB")).astype(int)
    blue = (abs(im[..., 0] - 31) < 4) & (abs(im[..., 1] - 111) < 4) & (abs(im[..., 2] - 235) < 4)
    ys, xs = np.nonzero(blue)
    got = [xs.min(), ys.min(), xs.max(), ys.max()]
    assert all(abs(g - w) <= 3 for g, w in zip(got, r["rect_in_tile"])), (png.name, got, r["rect_in_tile"])
import collections  # noqa: E402
print(len(pngs), "tiles | every tile's blue box == its key row's box | roles",
      dict(collections.Counter((r["doc"], r["role"]) for r in rows)))
