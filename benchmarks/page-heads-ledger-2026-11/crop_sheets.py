"""ROADMAP 2.290 r1 -- MY OWN crop look (NOT Sean's tiles): a contact sheet of up to N boxes of one refusal reason, seeded.

    PYTHONPATH=. python3 benchmarks/page-heads-ledger-2026-11/crop_sheets.py OUTDIR SEED N LABEL FATE_SUBSTR [--none] [--lowiou] FATES.json ...

Orange = the box that was not written (the one asked about); blue = the written box nearest it (twin look only). For the reader's eyes, never for Sean: Sean's tiles
draw one thin box and nothing else (`make_tiles.py`).
"""
import json
import os
import random
import sys

from PIL import Image, ImageDraw

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
PDF = {"litolff": LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
UNIT = {"litolff": 15.75, "brahms": 32.0}


def main(argv):
    from tools.omr.preprocessing import render_page
    out, seed, n, label, sub = argv[0], int(argv[1]), int(argv[2]), argv[3], argv[4]
    flags = [a for a in argv[5:] if a.startswith("--")]
    files = [a for a in argv[5:] if not a.startswith("--")]
    pool = []
    for f in files:
        d = json.load(open(f))
        if isinstance(d, dict):
            plate, rows = d["plate"], d["rows"]
        else:
            plate = "brahms" if "brh" in f else "litolff"
            rows = d
        for r in rows:
            if sub in r["fate"]:
                r = dict(r, plate=plate)
                pool.append(r)
    if "--none" in flags:
        pool = [r for r in pool if r.get("_best_iou", 0) < 0.1]
    if "--lowiou" in flags:
        pool = [r for r in pool if 0.1 <= r.get("_best_iou", 1) < 0.5]
    rng = random.Random(seed)
    pick = rng.sample(pool, min(n, len(pool)))
    pick.sort(key=lambda r: (r["plate"], int(r["sub"].split("/")[1])))     # one page render at a time
    os.makedirs(out, exist_ok=True)
    cache = {}
    tiles = []
    for r in pick:
        pg = int(r["sub"].split("/")[1])
        k = (r["plate"], pg)
        if k not in cache:
            cache.clear()
            cache[k] = Image.fromarray(render_page(PDF[r["plate"]], pg, dpi=600).rgb).convert("RGB")
        im = cache[k]
        u = UNIT[r["plate"]]
        b = r["box"]
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        x0, y0, x1, y1 = int(cx - 3 * u), int(cy - 2.6 * u), int(cx + 3 * u), int(cy + 2.6 * u)
        crop = im.crop((x0, y0, x1, y1)).copy()
        dr = ImageDraw.Draw(crop)
        dr.rectangle([b[0] - x0, b[1] - y0, b[2] - x0, b[3] - y0], outline=(255, 140, 0), width=2)
        if r.get("_best"):
            for q in json.load(open(files[0].replace(".json", ".twin.json"))) if False else []:
                pass
        crop = crop.resize((330, int(330 * crop.height / crop.width)))
        d2 = ImageDraw.Draw(crop)
        d2.text((3, 2), "%s p%d %s" % (r["plate"][:3], pg, r["sub"].split("/", 2)[2]), fill=(200, 0, 0))
        tiles.append((crop, r))
    cols = 5
    rows_n = (len(tiles) + cols - 1) // cols
    h = max((t.height for t, _ in tiles), default=10)
    sheet = Image.new("RGB", (cols * 338 + 8, rows_n * (h + 8) + 8), (255, 255, 255))
    meta = []
    for i, (t, r) in enumerate(tiles):
        sheet.paste(t, (8 + (i % cols) * 338, 8 + (i // cols) * (h + 8)))
        meta.append(dict(n=i + 1, sub=r["sub"], fate=r["fate"], cls=(r["cls"][0] if isinstance(r["cls"], list) else r["cls"]), box=r["box"], iou=r.get("_best_iou"),
                         conf=r.get("conf"), plate=r["plate"]))
    sheet.save(os.path.join(out, "%s.png" % label))
    json.dump(dict(pool=len(pool), seed=seed, picks=meta), open(os.path.join(out, "%s.json" % label), "w"), default=str)
    print(label, "pool", len(pool), "picked", len(pick))


if __name__ == "__main__":
    main(sys.argv[1:])
