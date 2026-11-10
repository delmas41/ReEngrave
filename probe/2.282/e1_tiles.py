"""2.282 step 3: 12 blind tiles from the arm disagreements. 6 where accidentals-first takes the ink (a stroke -> accidental, or a head box refused claimed_by the accidental),
6 where heads-first takes it (a contested stroke -> head / ledger). One staff window, ONE thin orange box on the contested ink, nothing else drawn.
Question (all tiles): "Is the boxed ink part of a note (head or stem), part of an accidental, or something else?"  Key kept OUTSIDE the tile folder.
usage: e1_tiles.py OUTDIR SEED"""
import json
import os
import random
import sys

sys.path.insert(0, "probe/2.282")
import crop as C                                           # noqa: E402
from PIL import Image                                       # noqa: E402

out, seed = sys.argv[1], int(sys.argv[2])
os.makedirs(out + "/tiles", exist_ok=True)
SP = {"litolff": 15.75, "brahms": 27.2}


def sbox_lookup(base, need):
    got = {}
    for line in open(base + "/observations.jsonl"):
        if '"stroke"' in line:
            o = json.loads(line)
            sub = o["subject"]
            if o["quantity"] == "stroke" and sub.startswith("glyph/"):
                k = ("cell/" + sub[6:].rsplit("/", 1)[0], int(sub.rsplit("/", 1)[1]) - 375000)
                if k in need:
                    got[k] = o["detail"].get("bbox_page_px")
    return got


pool = {"accidental": [], "head": []}
for plate in ("litolff", "brahms"):
    base = "out/2.282/base/" + plate
    acc = json.load(open("out/2.282/d1_acc_%s.json" % plate))
    hf = json.load(open("out/2.282/d1_hf_%s.json" % plate)) if os.path.exists("out/2.282/d1_hf_%s.json" % plate) else []
    need = {(r["cell"], r["ordinal"]) for r in acc + hf if r["kind"] == "stroke"}
    sb = sbox_lookup(base, need)
    for r in acc:
        if r["kind"] == "stroke" and r["arm"] and r["arm"][1] == "accidental" and sb.get((r["cell"], r["ordinal"])):
            pool["accidental"].append(dict(plate=plate, page=r["page"], box=sb[(r["cell"], r["ordinal"])], what="stroke %s/%d" % (r["cell"], r["ordinal"]),
                                           today=r["base"][:2] if r["base"] else None, wins="accidentals_first -> accidental"))
        elif r["kind"] == "head" and r["arm"] and "claimed_by" in str(r["arm"][1]):
            pool["accidental"].append(dict(plate=plate, page=r["page"], box=r["box"], what="head box " + r["sub"], today=list(r["base"]),
                                           wins="accidentals_first -> head box refused claimed_by accidental"))
    for r in hf:
        if r["kind"] == "stroke" and r["arm"] and r["arm"][1] in ("head", "ledger") and sb.get((r["cell"], r["ordinal"])):
            pool["head"].append(dict(plate=plate, page=r["page"], box=sb[(r["cell"], r["ordinal"])], what="stroke %s/%d" % (r["cell"], r["ordinal"]),
                                     today=r["base"][:2] if r["base"] else None, wins="heads_first -> %s" % r["arm"][1]))
rng = random.Random(seed)
for k in pool:
    rng.shuffle(pool[k])
pick = pool["accidental"][:6] + pool["head"][:6]
n_pool = {k: len(v) for k, v in pool.items()}
rng.shuffle(pick)
key, ims = {}, []
for i, p in enumerate(pick, 1):
    im = C.crop(p["plate"], p["page"], p["box"], SP[p["plate"]], hw=7.0, hh=4.5, width=640)
    fn = "tile_%02d.png" % i
    im.save("%s/tiles/%s" % (out, fn))
    ims.append(im)
    key[str(i)] = dict(file=fn, **p)
json.dump(dict(seed=seed, pool_sizes=n_pool, question="Is the boxed ink part of a note (head or stem), part of an accidental, or something else?", tiles=key),
          open(out + "/key.json", "w"), indent=1)
cols = 3
w, h = ims[0].width, max(i.height for i in ims)
sheet = Image.new("RGB", (cols * w, ((len(ims) + cols - 1) // cols) * h), (255, 255, 255))
for i, im in enumerate(ims):
    sheet.paste(im, ((i % cols) * w, (i // cols) * h))
sheet.save(out + "/tiles/sheet.png")
open(out + "/tiles/README.md", "w").write("# 2.282 blind tiles\n\nOne staff, one thin orange box. For every tile: **Is the boxed ink part of a note (head or stem), part of an accidental, or something else?**\n")
print("pool", n_pool, "tiles", len(pick))
