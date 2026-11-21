"""2.306 r18: 12 tiles of chords the ON arm now writes that the OFF arm refused (`chord_value_undecided` -> written), one staff each, a thin red
box on the chord's heads and nothing else; key (outside the tile folder) holds what the file writes for each head.
Usage: r18_chord_tiles.py OUTDIR KEY.json SEED (plate:dumpdir:workdir ...)"""
import sys, os, json, pickle, random, collections
import numpy as np
from PIL import Image, ImageDraw

outd, keyp, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
cands = []
for spec in sys.argv[4:]:
    plate, ddir, work = spec.split(":")
    F = pickle.load(open(os.path.join(work, "%s.fates.pkl" % plate), "rb"))
    sym = json.load(open(os.path.join(work, "%s.on.symbols.json" % plate)))
    by_rg = {h["rg"]: h for h in sym["hosts"] if h.get("rg")}
    groups = collections.defaultdict(list)
    for k in F["off"]:
        if F["off"][k] == "chord_value_undecided" and F["on"].get(k) == "written":
            groups["/".join(k.split("/")[:5])].append(k)
    for cell, ks in groups.items():
        cands.append((plate, ddir, cell, ks, [dict(rg=k, type=by_rg.get(k, {}).get("type"), pitch=by_rg.get(k, {}).get("pitch"),
                                                   dots=len((by_rg.get(k, {}).get("sub") or {}).get("dot") or [])) for k in ks]))
random.Random(seed).shuffle(cands)
os.makedirs(os.path.join(outd, "tiles"), exist_ok=True)
tiles, key, cache = [], [], {}
for n, (plate, ddir, cell, ks, written) in enumerate(cands[:12], 1):
    p = int(cell.split("/")[1])
    if (ddir, p) not in cache:
        cache[(ddir, p)] = pickle.load(open(os.path.join(ddir, "p%d.pkl" % p), "rb"))
    D = cache[(ddir, p)]
    hs = [h for h in D["heads"] if any(k in h["members"] for k in ks)]
    if not hs:
        continue
    x0 = min(h["box"][0] for h in hs); y0 = min(h["box"][1] for h in hs)
    x1 = max(h["box"][2] for h in hs); y1 = max(h["box"][3] for h in hs)
    sp = float(hs[0]["sp"])
    b = np.asarray(D["binary"]); ink = b < 128
    X0, X1 = int(max(0, x0 - 5 * sp)), int(min(ink.shape[1], x1 + 5 * sp))
    Y0, Y1 = int(max(0, y0 - 4 * sp)), int(min(ink.shape[0], y1 + 4 * sp))
    k = 3
    im = Image.fromarray((~ink[Y0:Y1, X0:X1]).astype(np.uint8) * 255).convert("RGB").resize(((X1 - X0) * k, (Y1 - Y0) * k), Image.NEAREST)
    ImageDraw.Draw(im).rectangle([(x0 - X0) * k - 3, (y0 - Y0) * k - 3, (x1 - X0) * k + 3, (y1 - Y0) * k + 3], outline=(230, 0, 0), width=2)
    im.save(os.path.join(outd, "tiles", "tile%02d.png" % n))
    tiles.append(im)
    key.append(dict(tile=n, plate=plate, cell=cell, written=written))
cols = 4
W = max(t.width for t in tiles); H = max(t.height for t in tiles)
sheet = Image.new("RGB", (cols * (W + 12), ((len(tiles) + cols - 1) // cols) * (H + 30)), "white")
d = ImageDraw.Draw(sheet)
for i, t in enumerate(tiles):
    x, y = (i % cols) * (W + 12), (i // cols) * (H + 30)
    d.text((x + 4, y + 4), "tile %d" % (i + 1), fill=(0, 0, 0))
    sheet.paste(t, (x, y + 20))
sheet.save(os.path.join(outd, "sheet.png"))
json.dump(key, open(keyp, "w"), indent=1)
print(len(tiles), "tiles", len(cands), "chords")
