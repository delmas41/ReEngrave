"""ROADMAP 2.161 (from 2.159's) -- blind tiles for Sean: every head the flag changes that he has not judged (both plates),
plus 2 controls that can fail (a black-classed head he judged a quarter, one he judged a half; drawn at random among the
eligible judged heads the flag does not change, never an earlier review's control). Nothing of ours drawn but ONE blue box
round the head (detector box joined with the box extended to its stem); each tile labelled "Tile N" only; the key apart
(KEYDIR/tiles-key.json); answers.json {}; every tile checked against its key row (the blue box re-found in the saved PNG at
the key's offset).
usage: tiles_2_161.py OUTDIR PRINTDIR SEED SLICEDIR KEYDIR"""
import glob
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
OUT, PR, SEED, SD, KEYDIR = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5]
os.makedirs(PR, exist_ok=True)
os.makedirs(KEYDIR, exist_ok=True)
J = json.load(open("benchmarks/acceptance/judged-tiles.json"))["tiles"]
judged = {(t["doc"], t["subject"]) for t in J if t.get("subject")}
rng = random.Random(SEED)
pick = []
changed = {}
for doc in ("litolff", "brahms"):
    R = json.load(open(os.path.join(OUT, "replay2161_%s.json" % doc)))
    changed[doc] = set(R["changed"])
    refused = set(json.load(open(os.path.join(OUT, "refused_%s.json" % doc)))["refused"])   # 2.143: not a note
    ch = sorted(g for g, c in R["changed"].items()
                if (c["adj_on"] or {}).get("bridged") and (doc, g) not in judged and g not in refused)
    pick += [(doc, g, "changed") for g in ch]
earlier_controls = {"glyph/10/1/4/8/7"}
for p in glob.glob("out/print/*/manifest.json"):
    try:
        for t in json.load(open(p)).get("tiles", []) or []:
            if isinstance(t, dict) and t.get("control"):
                earlier_controls.add(t.get("glyph"))
    except Exception:  # noqa: BLE001
        pass
ctl = {"black": [], "half": []}
for doc in ("litolff", "brahms"):
    H = json.load(open(os.path.join(OUT, "heads_%s.json" % doc)))
    for s, h in sorted(H.items()):
        if s in changed[doc] or s in earlier_controls:
            continue
        js = h.get("judged", [])
        cls = ((h.get("notehead_class") or {}).get("value")) or ""
        if not js or not cls.startswith("noteheadBlack"):
            continue
        kind = "half" if js[0]["value"] == 2.0 else "black" if js[0]["value"] == 1.0 else None
        if kind and doc == ("litolff" if kind == "half" else "brahms"):
            ctl[kind].append((doc, s, "control_" + kind))
pick += [rng.choice(ctl["black"]), rng.choice(ctl["half"])]
rng.shuffle(pick)
heads = {d: json.load(open(os.path.join(OUT, "heads_%s.json" % d))) for d in PDFS}
bridge = {d: json.load(open(os.path.join(OUT, "bridge_%s.json" % d))) for d in PDFS}
boxes = {}
for d in PDFS:
    want = {g for dd, g, _ in pick if dd == d}
    for p in sorted(glob.glob(os.path.join(SD, d, "p*.observations.jsonl"))):
        for line in open(p):
            if '"glyph_box"' in line:
                o = json.loads(line)
                if o["subject"] in want:
                    boxes[(d, o["subject"])] = (o["detail"]["bbox_page_px"], o["value"])
font = ImageFont.load_default()
key = []
for n, (doc, s, why) in enumerate(pick, 1):
    bb, gv = boxes[(doc, s)]
    sp = {"litolff": 15.75, "brahms": 27.3}[doc]
    hb = list(bb)
    if s in bridge[doc]:          # join the box extended to its stem (canonical -> page by the box's own scale)
        k_cp = (bb[2] - bb[0]) / float(gv[3])
        x, y, w, h = bridge[doc][s]["bridged_box"]
        px0, py0 = bb[0] + (x - gv[1]) * k_cp, bb[1] + (y - gv[2]) * k_cp
        hb = [min(hb[0], px0), min(hb[1], py0), max(hb[2], px0 + w * k_cp), max(hb[3], py0 + h * k_cp)]
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
    a = np.asarray(Image.open(os.path.join(PR, fn)).convert("RGB"))
    on = [a[int(bx[1]), int((bx[0] + bx[2]) / 2)], a[int((bx[1] + bx[3]) / 2), int(bx[0])]]
    ok = all(tuple(int(v) for v in px) == BLUE for px in on)
    key.append(dict(tile=n, file=fn, doc=doc, subject=s, why=why, page_box=bb, blue_box_page_px=[round(v, 1) for v in blue],
                    blue_box_tile_px=[round(v, 1) for v in bx], blue_checked=ok))
    print(n, doc, s, why, "blue ok" if ok else "BLUE NOT FOUND")
json.dump(key, open(os.path.join(KEYDIR, "tiles-key.json"), "w"), indent=1)
json.dump({"question": "What is the written value of the note in the blue box (1, 2, 4, 8 ..., dot, or not a note)?",
           "tiles": len(key), "blue": "the note asked about", "nothing else drawn": True},
          open(os.path.join(PR, "manifest.json"), "w"), indent=1)
if not os.path.exists(os.path.join(PR, "answers.json")):
    json.dump({}, open(os.path.join(PR, "answers.json"), "w"))
assert all(k["blue_checked"] for k in key)
