"""2.167 probe 4: crops. `sheet` = a contact sheet of ALL sampled heads for OUR OWN eyes (scratch, not evidence);
`tiles` = <=12 blind tiles for Sean under out/print/2.167-stems/: the page only, ONE blue box on the head asked about, labelled
"Tile N" only; the key (out/2.167/tiles-key.json) has one row per tile (checked equal) and each blue box is re-found in its PNG.

usage: p4_crops.py sheet STEMS.json OUT.png
       p4_crops.py tiles STEMS.json ROWS.jsonl CAUSES.json PRINTDIR KEYDIR [SEED=1670]
"""
import json
import os
import random
import sys

import fitz
import numpy as np
from PIL import Image, ImageDraw, ImageFont

PDF = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
       "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf")
SP = 27.3 if os.environ.get("DOC") == "brahms" else 15.75
BLUE = (31, 111, 235)
font = ImageFont.load_default()
BRAHMS = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
          "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")
_doc = fitz.open(BRAHMS if os.environ.get("DOC") == "brahms" else PDF)


def crop(sub, bb, bx, by, Z):
    """Page raster around the head box bb=[x0,y0,x1,y1] (page px, 600 dpi)."""
    blue = [bb[0] - 0.25 * SP, bb[1] - 0.25 * SP, bb[2] + 0.25 * SP, bb[3] + 0.25 * SP]
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    r = (cx - bx * SP, cy - by * SP, cx + bx * SP, cy + by * SP)
    k = 72 / 600
    pix = _doc[int(sub.split("/")[1])].get_pixmap(matrix=fitz.Matrix(600 / 72, 600 / 72),
                                                  clip=fitz.Rect(*[v * k for v in r]))
    im = Image.frombytes("RGB" if pix.n == 3 else "L", (pix.width, pix.height), pix.samples).convert("RGB")
    im = im.resize((int(im.width * Z), int(im.height * Z)), Image.LANCZOS)
    box = [(blue[0] - r[0]) * Z * (pix.width / (r[2] - r[0])) / Z * 1.0, 0, 0, 0]
    sx = im.width / (r[2] - r[0])
    sy = im.height / (r[3] - r[1])
    box = [(blue[0] - r[0]) * sx, (blue[1] - r[1]) * sy, (blue[2] - r[0]) * sx, (blue[3] - r[1]) * sy]
    return im, box


mode = sys.argv[1]
S = json.load(open(sys.argv[2]))
if mode == "sheet":
    subs = sorted(S)
    tiles = []
    for i, s in enumerate(subs):
        im, bx = crop(s, S[s]["page_bbox"], 5, 6, 1.3)
        t = Image.new("RGB", (im.width, im.height + 14), "white")
        t.paste(im, (0, 14))
        d = ImageDraw.Draw(t)
        d.rectangle([bx[0], bx[1] + 14, bx[2], bx[3] + 14], outline=BLUE, width=1)
        d.text((2, 2), "%d %s" % (i, s[6:]), fill=(0, 0, 0), font=font)
        tiles.append(t)
    cols = 8
    w, h = tiles[0].size
    rows_n = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows_n * h), "white")
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * w, (i // cols) * h))
    sheet.save(sys.argv[3])
    print("sheet", sheet.size, [(i, s) for i, s in enumerate(subs)])
else:
    rows = {r["sub"]: r for r in (json.loads(l) for l in open(sys.argv[3]))}
    C = json.load(open(sys.argv[4]))
    PR, KEYDIR = sys.argv[5], sys.argv[6]
    seed = int(sys.argv[7]) if len(sys.argv) > 7 else 1670
    os.makedirs(PR, exist_ok=True)
    os.makedirs(KEYDIR, exist_ok=True)
    rng = random.Random(seed)
    pick = []
    by_cause = {}
    for s, c in sorted(C.items()):
        by_cause.setdefault(c.split(":")[0].strip(), []).append(s)
    # 9 sample tiles: proportional-ish, every cause family present
    quota = {}
    fam = sorted(by_cause, key=lambda k: -len(by_cause[k]))
    for k in fam:
        quota[k] = 1
    left = 9 - len(fam)
    for k in fam:
        if left <= 0:
            break
        take = min(left, max(0, round(len(by_cause[k]) / 40 * 9) - 1))
        quota[k] += take
        left -= take
    while sum(quota.values()) < 9:
        quota[fam[0]] += 1
    for k in fam:
        pick += [(s, "sample:" + k) for s in rng.sample(by_cause[k], min(quota[k], len(by_cause[k])))]
    pick = pick[:9]
    # controls that can fail: a head whose stem IS connected and written; a whole note (no stem by convention)
    ok = [r for r in rows.values() if r["fate"] == "written" and not r["held_cell"] and r["head_stem"]
          and r["head_stem"][1] == "one_stem" and r["cls"].startswith("noteheadBlack") and r["bbox"]]
    wh = [r for r in rows.values() if r["fate"] == "written" and r["cls"].startswith("noteheadWhole") and r["bbox"]]
    pick.append((rng.choice(sorted(ok, key=lambda r: r["sub"]))["sub"], "control:connected_stem"))
    pick.append((rng.choice(sorted(wh, key=lambda r: r["sub"]))["sub"], "control:whole_note"))
    rng.shuffle(pick)
    key = []
    for n, (s, why) in enumerate(pick, 1):
        bb = (S[s]["page_bbox"] if s in S else rows[s]["bbox"])
        im, bx = crop(s, bb, 6, 7, 3)
        tile = Image.new("RGB", (im.width, im.height + 24), "white")
        tile.paste(im, (0, 24))
        d = ImageDraw.Draw(tile)
        b2 = [bx[0], bx[1] + 24, bx[2], bx[3] + 24]
        d.rectangle(b2, outline=BLUE, width=3)
        d.text((6, 6), "Tile %d" % n, fill=(0, 0, 0), font=font)
        fn = "tile_%02d.png" % n
        tile.save(os.path.join(PR, fn))
        a = np.asarray(Image.open(os.path.join(PR, fn)).convert("RGB"))
        on = [a[int(b2[1]), int((b2[0] + b2[2]) / 2)], a[int((b2[1] + b2[3]) / 2), int(b2[0])]]
        okb = all(tuple(int(v) for v in px) == BLUE for px in on)
        key.append(dict(tile=n, file=fn, subject=s, why=why, cause=C.get(s), page_box=bb,
                        blue_box_tile_px=[round(v, 1) for v in b2], blue_checked=okb))
        print(n, s, why, "blue ok" if okb else "BLUE NOT FOUND")
    assert all(k["blue_checked"] for k in key)
    json.dump(key, open(os.path.join(KEYDIR, "tiles-key.json"), "w"), indent=1)
    json.dump({"question": "Does the note in the blue box have a stem printed on it? (yes / no; if yes, which side)",
               "tiles": len(key), "blue": "the note asked about", "nothing else drawn": True},
              open(os.path.join(PR, "manifest.json"), "w"), indent=1)
    if not os.path.exists(os.path.join(PR, "answers.json")):
        json.dump({}, open(os.path.join(PR, "answers.json"), "w"))
    assert len(key) == len([f for f in os.listdir(PR) if f.startswith("tile_")])
