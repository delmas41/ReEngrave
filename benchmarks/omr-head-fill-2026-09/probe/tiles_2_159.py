"""ROADMAP 2.159 -- blind tiles for Sean: heads the flag changes that he has not judged (both plates), plus 2 controls that can
fail (a head he judged a quarter, a head he judged a half). Nothing of ours drawn but ONE blue box round the head; each tile
labelled "Tile N" only; the key apart (out/2.159/tiles-key.json); answers.json {}; every tile checked against its key row
(the blue box re-found in the saved PNG at the key's offset).
usage: tiles_2_159.py OUTDIR PRINTDIR N_PER_DOC SEED"""
import json
import os
import random
import sys

sys.path.insert(0, ".")
import fitz  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

PDFS = {
    "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
               "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
}
BLUE = (31, 111, 235)
OUT, PR, NPER, SEED = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
os.makedirs(PR, exist_ok=True)
J = json.load(open("benchmarks/acceptance/judged-tiles.json"))["tiles"]
judged = {(t["doc"], t["subject"]) for t in J if t.get("subject")}
rng = random.Random(SEED)
pick = []
for doc in ("litolff", "brahms"):
    R = json.load(open(os.path.join(OUT, "replay_%s.json" % doc)))
    refused = set(json.load(open(os.path.join(OUT, "refused_%s.json" % doc)))["refused"])   # 2.143: not a note
    ch = [g for g, c in R["changed"].items()
          if (c["adj_on"] or {}).get("hff") and (doc, g) not in judged and g not in refused]
    rng.shuffle(ch)
    pick += [(doc, g, "changed") for g in sorted(ch[:NPER])]
# controls: one head Sean judged a quarter (black), one he judged a half -- both BLACK-classed boxes the flag reads
ctl = {"black": None, "half": None}
for doc in ("litolff", "brahms"):
    H = json.load(open(os.path.join(OUT, "heads_%s.json" % doc)))
    for s, h in sorted(H.items()):
        for j in h.get("judged", []):
            cls = ((h.get("notehead_class") or {}).get("value")) or ""
            if not cls.startswith("noteheadBlack"):
                continue
            kind = "half" if j["value"] == 2.0 else "black" if j["value"] == 1.0 else None
            if kind and ctl[kind] is None and doc == ("litolff" if kind == "half" else "brahms"):
                ctl[kind] = (doc, s, "control_" + kind)
pick += [ctl["black"], ctl["half"]]
rng.shuffle(pick)
heads = {d: json.load(open(os.path.join(OUT, "heads_%s.json" % d))) for d in PDFS}
loc = {d: json.load(open(os.path.join(OUT, "located_%s.json" % d))) for d in PDFS}
boxes = {}
for d in PDFS:      # page boxes for heads not in heads_<doc>.json (changed heads that were not hf / judged)
    want = {g for dd, g, _ in pick if dd == d and g not in heads[d]}
    if want:
        import glob
        for p in sorted(glob.glob(os.path.join(sys.argv[5] if len(sys.argv) > 5 else "", d, "p*.observations.jsonl"))):
            for line in open(p):
                if '"glyph_box"' in line:
                    o = json.loads(line)
                    if o["subject"] in want:
                        boxes[(d, o["subject"])] = o["detail"]["bbox_page_px"]
font = ImageFont.load_default()
key = []
for n, (doc, s, why) in enumerate(pick, 1):
    bb = boxes.get((doc, s)) or heads[doc][s]["glyph_box"]["detail"]["bbox_page_px"]
    sp = {"litolff": 15.75, "brahms": 27.3}[doc]
    hb = list(bb)
    if s in loc[doc]:
        x, y, w, h = loc[doc][s]["box_page"]
        hb = [min(hb[0], x), min(hb[1], y), max(hb[2], x + w), max(hb[3], y + h)]
    blue = [hb[0] - 0.25 * sp, hb[1] - 0.25 * sp, hb[2] + 0.25 * sp, hb[3] + 0.25 * sp]
    r = (blue[0] - 5 * sp, blue[1] - 5 * sp, blue[2] + 5 * sp, blue[3] + 5 * sp)
    k = 72 / 600
    pix = fitz.open(PDFS[doc])[int(s.split("/")[1])].get_pixmap(matrix=fitz.Matrix(600 / 72, 600 / 72),
                                                                clip=fitz.Rect(*[v * k for v in r]))
    im = Image.frombytes("RGB" if pix.n == 3 else "L", (pix.width, pix.height), pix.samples).convert("RGB")
    Z = 3 if doc == "litolff" else 2
    im = im.resize((im.width * Z, im.height * Z), Image.LANCZOS)
    tile = Image.new("RGB", (im.width, im.height + 24), "white")
    tile.paste(im, (0, 24))
    d = ImageDraw.Draw(tile)
    bx = [(blue[0] - r[0]) * Z, (blue[1] - r[1]) * Z + 24, (blue[2] - r[0]) * Z, (blue[3] - r[1]) * Z + 24]
    d.rectangle(bx, outline=BLUE, width=3)
    d.text((6, 6), "Tile %d" % n, fill=(0, 0, 0), font=font)
    fn = "tile_%02d.png" % n
    tile.save(os.path.join(PR, fn))
    # check the tile against its key row: the blue outline is where the key says
    a = np.asarray(tile)
    on = [a[int(bx[1]), int((bx[0] + bx[2]) / 2)], a[int((bx[1] + bx[3]) / 2), int(bx[0])]]
    ok = all(tuple(int(v) for v in px) == BLUE for px in on)
    key.append(dict(tile=n, file=fn, doc=doc, subject=s, why=why, page_box=bb, blue_box_page_px=[round(v, 1) for v in blue],
                    blue_box_tile_px=[round(v, 1) for v in bx], blue_checked=ok))
    print(n, doc, s, why, "blue ok" if ok else "BLUE NOT FOUND")
json.dump(key, open(os.path.join(OUT, "tiles-key.json"), "w"), indent=1)
json.dump({"question": "What is the written value of the note in the blue box (1, 2, 4, 8 ..., dot, or not a note)?",
           "tiles": len(key), "blue": "the note asked about", "nothing else drawn": True},
          open(os.path.join(PR, "manifest.json"), "w"), indent=1)
if not os.path.exists(os.path.join(PR, "answers.json")):
    json.dump({}, open(os.path.join(PR, "answers.json"), "w"))
assert all(k["blue_checked"] for k in key)
