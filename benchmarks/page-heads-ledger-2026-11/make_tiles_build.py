"""ROADMAP 2.290 build r1 -- Sean's 12 BLIND tiles on the page heads' CLAIMED ink (one staff, a thin box sized to the head's claimed extent, the claimed ink
tinted, nothing else drawn, the head's stem left visible; key one level above the tiles folder).

    PYTHONPATH=. python3 benchmarks/page-heads-ledger-2026-11/make_tiles_build.py OUTDIR PICKS.json [SEED=2290]

PICKS.json: {"lost": [...], "undecided": [...], "ledger": [...], "chord": [...]} -- each item {plate, page, box (the claimed extent, page px),
pixels: [[x, y], ...] the claimed ink (page px) or null, staff_band [y0, y1] (page px, the head's own staff plus 2 sp), why}. SELECTION RULE (stated,
seeded): every lost/changed note first (in plate, page, x order), then the partition disagreements no rule decided (random.Random(SEED) draw), then the
2.291 chord heads (two), then heads newly on the ledger split evenly across the two plates (same RNG), to 12; the tile order is shuffled by the same RNG.
QUESTION: "Is the tinted ink ONE notehead, and only that notehead? If not, what is it?"
"""
import json
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
PDF = {"litolff": LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
UNIT = {"litolff": 15.75, "brahms": 32.0}
TINT = (30, 140, 255)
BOX = (255, 140, 0)


def choose(picks, seed):
    rng = random.Random(seed)
    out = [("lost_or_changed", r) for r in sorted(picks.get("lost") or [], key=lambda r: (r["plate"], r["page"], r["box"][0]))][:12]
    und = list(picks.get("undecided") or [])
    rng.shuffle(und)
    out += [("partition_undecided", r) for r in und[:max(0, 12 - len(out) - 2 - 2)]]
    ch = list(picks.get("chord") or [])
    out += [("chord_2.291", r) for r in ch[:2]][:max(0, 12 - len(out))]
    led = {p: [r for r in (picks.get("ledger") or []) if r["plate"] == p] for p in ("litolff", "brahms")}
    for p in led:
        rng.shuffle(led[p])
    i = 0
    while len(out) < 12 and (led["litolff"] or led["brahms"]):
        p = ("litolff", "brahms")[i % 2]
        if led[p]:
            out.append(("newly_on_ledger", led[p].pop()))
        i += 1
    rng.shuffle(out)
    return out


def main(out, picks_path, seed):
    from tools.omr.preprocessing import render_page
    picks = json.load(open(picks_path))
    chosen = choose(picks, seed)
    tdir = os.path.join(out, "tiles")
    os.makedirs(tdir, exist_ok=True)
    for f in os.listdir(tdir):
        os.remove(os.path.join(tdir, f))
    cache, key, ims = {}, [], []
    for n, (name, r) in enumerate(chosen, 1):
        k = (r["plate"], r["page"])
        if k not in cache:
            cache.clear()
            cache[k] = Image.fromarray(render_page(PDF[r["plate"]], r["page"], dpi=600).rgb).convert("RGB")
        im = cache[k]
        u = UNIT[r["plate"]]
        b = r["box"]
        cx = (b[0] + b[2]) / 2
        y0, y1 = r["staff_band"]
        x0, x1 = max(0, int(cx - 5 * u)), int(cx + 5 * u)
        crop = im.crop((x0, int(y0), x1, int(y1))).copy()
        px = crop.load()
        for x, y in r.get("pixels") or ():
            xx, yy = int(x) - x0, int(y) - int(y0)
            if 0 <= xx < crop.width and 0 <= yy < crop.height:
                px[xx, yy] = TINT
        ImageDraw.Draw(crop).rectangle([b[0] - x0 - 1, b[1] - y0 - 1, b[2] - x0 + 1, b[3] - y0 + 1], outline=BOX, width=max(1, int(u / 14)))
        crop = crop.resize((520, max(1, int(520 * crop.height / crop.width))))
        crop.save(os.path.join(tdir, "tile_%02d.png" % n))
        ims.append(crop)
        key.append(dict(tile=n, stratum=name, seed=seed, crop_origin=[x0, int(y0)], **{kk: vv for kk, vv in r.items() if kk != "pixels"}))
    # sheet: 3 columns, LARGE tile numbers above each tile, no insets
    cols, pad, lab = 3, 16, 56
    w = 520
    rows = [ims[i:i + cols] for i in range(0, len(ims), cols)]
    hs = [max(im.height for im in row) + lab for row in rows]
    sheet = Image.new("RGB", (cols * (w + pad) + pad, sum(hs) + pad * (len(rows) + 1)), "white")
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 44)
    except Exception:
        font = ImageFont.load_default()
    y = pad
    n = 1
    for row, h in zip(rows, hs):
        x = pad
        for im in row:
            d.text((x, y), "Tile %d" % n, fill="black", font=font)
            sheet.paste(im, (x, y + lab))
            x += w + pad
            n += 1
        y += h + pad
    sheet.save(os.path.join(tdir, "sheet.png"))
    json.dump(key, open(os.path.join(out, "key.json"), "w"), indent=1, default=str)
    open(os.path.join(tdir, "README.md"), "w").write(
        "# 2.290 build -- noteheads claimed on the page\n\nEach picture is one staff of the printed score. The BLUE tint is the ink we now claim as ONE notehead; "
        "the thin orange box is drawn around that ink only (a place to look). Nothing else is drawn.\n\n**Question, for every tile:** Is the tinted ink ONE "
        "notehead, and only that notehead? If not, what is it?\n\nAnswer by tile number.\n")
    print("tiles", len(key), "->", tdir)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 2290)
