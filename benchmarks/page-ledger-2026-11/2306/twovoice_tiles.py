"""2.306 two-voice piece: the control tiles -- one staff each, a thin red box on the head (or chord), nothing else drawn -- and a key (outside the
tile folder) with what each arm's written file holds at that head: part, bar, voice, onset, value, pitch, and every other note of that bar that
starts at the same onset. Usage: twovoice_tiles.py WORKDIR OUTDIR KEY.json plate:dump.pkl:member[,member...] ..."""
import sys, os, json, pickle
import numpy as np
from PIL import Image, ImageDraw

work, outd, keyp = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(outd, exist_ok=True)
syms = {}
tiles, key, cache = [], [], {}
for n, spec in enumerate(sys.argv[4:], 1):
    plate, dp, mems = spec.split(":")
    mems = mems.split(",")
    for arm in ("base", "new"):
        if (plate, arm) not in syms:
            syms[(plate, arm)] = json.load(open(os.path.join(work, "%s.%s.symbols.json" % (plate, arm))))
    if dp not in cache:
        cache.clear()
        cache[dp] = pickle.load(open(dp, "rb"))
    D = cache[dp]
    hs = [h for h in D["heads"] if any(m in h["members"] for m in mems)]
    allm = sorted({m for h in hs for m in h["members"]})
    x0 = min(h["box"][0] for h in hs); y0 = min(h["box"][1] for h in hs)
    x1 = max(h["box"][2] for h in hs); y1 = max(h["box"][3] for h in hs)
    sp = float(D["sp"])
    ink = np.asarray(D["binary"]) < 128
    X0, X1 = int(max(0, x0 - 7 * sp)), int(min(ink.shape[1], x1 + 7 * sp))
    Y0, Y1 = int(max(0, (y0 + y1) / 2 - 6 * sp)), int(min(ink.shape[0], (y0 + y1) / 2 + 6 * sp))
    k = 3
    im = Image.fromarray((~ink[Y0:Y1, X0:X1]).astype(np.uint8) * 255).convert("RGB").resize(((X1 - X0) * k, (Y1 - Y0) * k), Image.NEAREST)
    ImageDraw.Draw(im).rectangle([(x0 - X0) * k - 3, (y0 - Y0) * k - 3, (x1 - X0) * k + 3, (y1 - Y0) * k + 3], outline=(230, 0, 0), width=1)
    im.save(os.path.join(outd, "tile%02d.png" % n))
    tiles.append(im)
    ent = dict(tile=n, plate=plate, heads=allm)
    for arm in ("base", "new"):
        hosts = [h for h in syms[(plate, arm)]["hosts"] if h.get("kind") == "note"]
        mine = [h for h in hosts if h.get("rg") in allm]
        ctx = []
        for h in mine:
            ctx += [dict(rg=o.get("rg"), voice=o.get("voice"), onset=o.get("onset"), type=o.get("type"), pitch=o.get("pitch"),
                         dots=len((o.get("sub") or {}).get("dot") or []), blue=o.get("blue"))
                    for o in hosts if o.get("part") == h.get("part") and o.get("measure") == h.get("measure") and o.get("onset") == h.get("onset")
                    and o.get("rg") not in allm]
        ent[arm] = dict(written=[dict(rg=h.get("rg"), part=h.get("part"), bar=h.get("measure"), voice=h.get("voice"), onset=h.get("onset"),
                                      type=h.get("type"), dots=len((h.get("sub") or {}).get("dot") or []), pitch=h.get("pitch"), blue=h.get("blue"),
                                      chord=h.get("chord")) for h in mine],
                        same_onset_others=ctx)
    key.append(ent)
cols = 4
W = max(t.width for t in tiles); H = max(t.height for t in tiles)
sheet = Image.new("RGB", (cols * (W + 12), ((len(tiles) + cols - 1) // cols) * (H + 30)), "white")
d = ImageDraw.Draw(sheet)
for i, t in enumerate(tiles):
    x, y = (i % cols) * (W + 12), (i // cols) * (H + 30)
    d.text((x + 4, y + 4), "tile %d" % (i + 1), fill=(0, 0, 0))
    sheet.paste(t, (x, y + 20))
sheet.save(os.path.join(os.path.dirname(outd.rstrip("/")), "sheet.png"))
json.dump(key, open(keyp, "w"), indent=1)
print(len(tiles), "tiles")
