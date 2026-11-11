"""ROADMAP 2.288 round 1 -- the blind tiles of REST CLAIMS (the exported file does not change with `OMR_PAGE_CLAIM_RESTS`, so the claims are what there is to show Sean).

    python3 benchmarks/rests-claim-first-2026-11/tiles_288.py --out OUT --seed 288 \
        litolff:RECORD.json:PDF:2,8 brahms:RECORD.json:PDF:14,19 [--control LABEL:PLATE:PAGE:x0,y0,x1,y1]

SELECTION RULE (stated, seeded): the READ rest claims (`Q.CLAIMED_AREA`, `source: page_boxes`) of the ON records, twin claims folded (same class, box rounded to 6 px),
pooled over the plates, sampled with `random.Random(seed)` per stratum: 4 quarter rests, 4 smaller rests (eighth / sixteenth / thirty-second / half), 3 whole rests; plus 1 control that
can fail (a claim the first 2.288 gather made and the area guard now refuses: the "c" "r" of "cresc." under a rest-8th box). Tiles are shuffled; the key is ONE LEVEL ABOVE the tile folder.

A TILE shows ONE staff window of the page (the deskewed 600 dpi page the boxes are in), ONE thin orange box at the claim's own extent (the union of the strokes it owns), and the ink the claim
owns tinted blue (the dark pixels of its strokes' boxes, minus the staff-line pixels: a dark pixel whose horizontal run reaches past the stroke box on both sides is a staff line). Nothing else is drawn.
Question for Sean: is the blue ink a rest, and ONLY the rest (no stem, no note, no letters)?
"""
import argparse
import json
import pathlib
import random
import sys

sys.path.insert(0, ".")
import numpy as np
from PIL import Image, ImageDraw

from tools.omr.preprocessing import render_page


def claims_of(record, pages):
    obs = json.load(open(record))["record"]["observations"]
    strokes = {}
    for o in obs:
        if o["quantity"] == "page_stroke":
            strokes[(o["subject"], o["detail"]["ordinal"])] = o["detail"]
    out, seen = [], set()
    for o in obs:
        d = o.get("detail") or {}
        if d.get("source") != "page_boxes" or d.get("unit") != "page_ink":
            continue
        pg = int(o["subject"].split("/")[1])
        if pg not in pages:
            continue
        sd = [strokes[("page/%d" % pg, i)] for i in o["value"] if ("page/%d" % pg, i) in strokes]
        if not sd:
            continue
        bbs = [s["bbox_page_px"] for s in sd]
        box = [min(b[0] for b in bbs), min(b[1] for b in bbs), max(b[2] for b in bbs), max(b[3] for b in bbs)]
        k = (pg, d["cls"]) + tuple(int(round(v / 6)) for v in box)
        if k in seen:
            continue
        seen.add(k)
        sp = float(sd[0].get("staff_space_local_px") or 25.0)
        out.append(dict(page=pg, cls=d["cls"], box=box, strokes=bbs, sp=sp, subject=o["subject"]))
    return out


def tile(page_img, c, size=(340, 220)):
    rgb, bin_ = page_img.rgb, page_img.binary
    H, W = bin_.shape
    x0, y0, x1, y1 = c["box"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hw, hh = int(c["sp"] * 9), int(c["sp"] * 4.5)
    X0, X1, Y0, Y1 = int(max(0, cx - hw)), int(min(W, cx + hw)), int(max(0, cy - hh)), int(min(H, cy + hh))
    im = rgb[Y0:Y1, X0:X1].copy()
    dark = bin_ == 0
    for sx0, sy0, sx1, sy1 in c["strokes"]:
        sx0, sy0, sx1, sy1 = int(round(sx0)), int(round(sy0)), int(round(sx1)), int(round(sy1))
        for y in range(max(sy0, Y0), min(sy1, Y1)):
            row = dark[y]
            xs = np.nonzero(row[max(sx0, X0):min(sx1, X1)])[0] + max(sx0, X0)
            for x in xs:
                # a staff-line pixel: the dark run through it reaches at least 5 px past the stroke box on BOTH sides
                if x - 1 >= 0 and row[max(0, sx0 - 5):sx0].all() and row[sx1:min(W, sx1 + 5)].all() and sx0 - 5 >= 0:
                    continue
                im[y - Y0, x - X0] = (0, 120, 255)
    pil = Image.fromarray(im)
    ImageDraw.Draw(pil).rectangle([x0 - X0 - 2, y0 - Y0 - 2, x1 - X0 + 2, y1 - Y0 + 2], outline=(255, 140, 0), width=1)
    return pil


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=288)
    ap.add_argument("--control", default=None, help="LABEL:PLATE:PAGE:x0,y0,x1,y1")
    ap.add_argument("plates", nargs="+")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    (out / "tiles").mkdir(parents=True, exist_ok=True)
    pdfs, pools = {}, []
    for spec in a.plates:
        plate, rec, pdf, pages = spec.split(":")
        pdfs[plate] = pdf
        for c in claims_of(rec, [int(p) for p in pages.split(",")]):
            c["plate"] = plate
            pools.append(c)
    rng = random.Random(a.seed)
    strata = (("quarter", ("restQuarter",), 4), ("smaller", ("rest8th", "rest16th", "rest32nd", "restHalf"), 4), ("whole", ("restWhole",), 3))
    chosen = []
    for name, classes, n in strata:
        pool = sorted([c for c in pools if c["cls"] in classes], key=lambda c: (c["plate"], c["page"], c["box"]))
        for c in rng.sample(pool, min(n, len(pool))):
            c["stratum"] = name
            chosen.append(c)
    if a.control:
        label, plate, page, b = a.control.split(":")
        box = [float(v) for v in b.split(",")]
        # the control's owned ink: the strokes of the page inside its box, read from the first gather's claim (the box itself)
        chosen.append(dict(plate=plate, page=int(page), cls="control:" + label, box=box, strokes=[box], sp=25.0, stratum="control"))
    rng.shuffle(chosen)
    pages_cache, tiles, key = {}, [], []
    for i, c in enumerate(chosen, 1):
        k = (c["plate"], c["page"])
        if k not in pages_cache:
            pages_cache[k] = render_page(pdfs[c["plate"]], c["page"], 600)
        t = tile(pages_cache[k], c)
        t.save(out / "tiles" / ("tile_%02d.png" % i))
        tiles.append(t)
        key.append(dict(tile=i, plate=c["plate"], page=c["page"], cls=c["cls"], stratum=c["stratum"], box=[round(v, 1) for v in c["box"]], subject=c.get("subject")))
    w = max(t.width for t in tiles)
    h = max(t.height for t in tiles)
    cols = 3
    sheet = Image.new("RGB", (cols * w, ((len(tiles) + cols - 1) // cols) * h), (255, 255, 255))
    for i, t in enumerate(tiles):
        d = ImageDraw.Draw(t)
        d.text((4, 4), str(i + 1), fill=(200, 0, 0))
        sheet.paste(t, ((i % cols) * w, (i // cols) * h))
    sheet.save(out / "tiles" / "sheet.png")
    (out / "key.json").write_text(json.dumps(dict(seed=a.seed, rule=__doc__, tiles=key), indent=1))
    (out / "tiles" / "README.md").write_text(
        "# Tiles for Sean\n\nEach picture is ONE staff window of a scanned page with ONE thin orange box and the ink one claim owns tinted blue. Nothing else is drawn.\n\n"
        "**Question, for every tile:** is the blue ink a rest, and ONLY the rest -- no part of a stem, a note, a letter or a sign?\n\nAnswer by tile number.\n")


if __name__ == "__main__":
    main()
