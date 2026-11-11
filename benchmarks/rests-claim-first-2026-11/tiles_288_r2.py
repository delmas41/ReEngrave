"""ROADMAP 2.288 round 2 -- the blind tiles of REST CLAIMS after the attachment rule (`page_claim_names.rest_attachment`).

    python3 benchmarks/rests-claim-first-2026-11/tiles_288_r2.py --out OUT --seed 2882 \
        litolff:ON_RECORD.json:PDF:2,8 brahms:ON_RECORD.json:PDF:14,19 [--extra LABEL:PLATE:PAGE:x0,y0,x1,y1 ...]

SELECTION RULE (stated, seeded; read off the census row `rest_changed_boxes` of the ON records -- the boxes where round 2's standing differs from round 1's):
  1. every box round 1 stood READ and round 2 refuses ("refused_*": the ink hangs from a stem carrying a head, touches a head, or is a bare vertical), Brahms p19
     detector box [3676.6,1620.8,3708.3,1668.6] (Sean's round-1 tile 7, whose claim extent was [3680,1612,3711,1651]) first, then the rest in page order; at most 7 of them (an even draw with `random.Random(seed)` if more);
  2. then the newly claimed eighth rests ("freed_*": round 1 weak, round 2 READ), drawn with `random.Random(seed)` alternating between the plates;
  3. then `--extra` boxes (a file change, a control twin), in the order given;
  up to 12 tiles. Tiles are shuffled; the key is ONE LEVEL ABOVE the tile folder.

A TILE shows ONE staff window of the deskewed 600 dpi page (about 18 spaces wide, 11 tall, so the stem and the head a flag hangs from are in view), ONE thin orange box at the
claim's extent, and the ink the claim owns tinted blue (the dark pixels of the page strokes whose box lies mostly inside the detector's rest box, minus staff-line pixels).
Nothing else is drawn. Question for Sean: is the blue ink a rest, and ONLY the rest (no stem, no flag, no note, no letters)?
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


def load(record, pages):
    rec = json.load(open(record))["record"]
    strokes, census = {}, []
    for o in rec["observations"]:
        sub = o["subject"]
        if o["quantity"] == "page_stroke" and o["value"] != "barline":
            pg = int(sub.split("/")[1])
            if pg in pages:
                d = o["detail"]
                strokes.setdefault(pg, {})[d["ordinal"]] = d
        d = o.get("detail") or {}
        if d.get("source") == "page_boxes" and d.get("unit") == "page_ink_census" and sub.startswith("page/"):
            pg = int(sub.split("/")[1])
            if pg in pages:
                census.append((pg, d))
    return strokes, census


def owned(strokes, box):
    out = []
    bx0, by0, bx1, by1 = box
    for i, d in strokes.items():
        x0, y0, x1, y1 = d["bbox_page_px"]
        ix, iy = max(0, min(x1, bx1) - max(x0, bx0)), max(0, min(y1, by1) - max(y0, by0))
        a = max(1e-9, (x1 - x0) * (y1 - y0))
        if ix * iy / a >= 0.5:
            out.append(d["bbox_page_px"])
    return out


def tile(page_img, box, sbs, sp):
    rgb, bin_ = page_img.rgb, page_img.binary
    H, W = bin_.shape
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hw, hh = int(sp * 9), int(sp * 5.5)
    X0, X1, Y0, Y1 = int(max(0, cx - hw)), int(min(W, cx + hw)), int(max(0, cy - hh)), int(min(H, cy + hh))
    im = rgb[Y0:Y1, X0:X1].copy()
    dark = bin_ == 0
    for sx0, sy0, sx1, sy1 in sbs:
        sx0, sy0, sx1, sy1 = int(round(sx0)), int(round(sy0)), int(round(sx1)), int(round(sy1))
        for y in range(max(sy0, Y0), min(sy1, Y1)):
            row = dark[y]
            xs = np.nonzero(row[max(sx0, X0):min(sx1, X1)])[0] + max(sx0, X0)
            for x in xs:
                if sx0 - 5 >= 0 and row[sx0 - 5:sx0].all() and row[sx1:min(W, sx1 + 5)].all():
                    continue                                    # a staff-line pixel: the dark run reaches past the stroke box on both sides
                im[y - Y0, x - X0] = (0, 120, 255)
    pil = Image.fromarray(im)
    ImageDraw.Draw(pil).rectangle([x0 - X0 - 2, y0 - Y0 - 2, x1 - X0 + 2, y1 - Y0 + 2], outline=(255, 140, 0), width=1)
    return pil


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=2882)
    ap.add_argument("--extra", action="append", default=[], help="LABEL:PLATE:PAGE:x0,y0,x1,y1")
    ap.add_argument("plates", nargs="+")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    (out / "tiles").mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    pdfs, data, refused, freed = {}, {}, [], []
    for spec in a.plates:
        plate, rec, pdf, pages = spec.split(":")
        pages = [int(p) for p in pages.split(",")]
        pdfs[plate] = pdf
        strokes, census = load(rec, pages)
        data[plate] = strokes
        for pg, d in census:
            for cls, box, why, cell in d.get("rest_changed_boxes", []):
                item = dict(plate=plate, page=pg, cls=cls, box=box, why=why, cell=cell)
                if why.startswith("refused_") and "names_no_stroke" not in why:
                    refused.append(item)
                elif cls == "rest8th":
                    freed.append(item)
    tile7 = [r for r in refused if r["plate"] == "brahms" and r["page"] == 19 and abs(r["box"][0] - 3676.6) < 4 and abs(r["box"][1] - 1620.8) < 4]
    rest = sorted([r for r in refused if r not in tile7], key=lambda r: (r["plate"], r["page"], r["box"]))
    if len(rest) > 6:
        rest = sorted(rng.sample(rest, 6), key=lambda r: (r["plate"], r["page"], r["box"]))
    chosen = [dict(r, group="refused-hang") for r in tile7 + rest]
    pools = {p: sorted([r for r in freed if r["plate"] == p], key=lambda r: (r["page"], r["box"])) for p in data}
    for p in pools:
        rng.shuffle(pools[p])
    order = list(pools)
    k = 0
    while len(chosen) < 12 - len(a.extra) and any(pools.values()):
        p = order[k % len(order)]
        k += 1
        if pools[p]:
            chosen.append(dict(pools[p].pop(), group="newly-claimed-eighth"))
    for e in a.extra:
        label, plate, page, b = e.split(":")
        box = [float(v) for v in b.split(",")]
        chosen.append(dict(plate=plate, page=int(page), cls="extra:" + label, box=box, why=label, cell="", group="extra"))
    rng.shuffle(chosen)
    cache, tiles, key = {}, [], []
    for i, c in enumerate(chosen, 1):
        k2 = (c["plate"], c["page"])
        if k2 not in cache:
            cache[k2] = render_page(pdfs[c["plate"]], c["page"], 600)
        sts = data[c["plate"]].get(c["page"], {})
        sbs = owned(sts, c["box"])
        sps = [d["staff_space_local_px"] for d in sts.values() if d.get("staff_space_local_px")]
        sp = float(np.median(sps)) if sps else 25.0
        t = tile(cache[k2], c["box"], sbs, sp)
        t.save(out / "tiles" / ("tile_%02d.png" % i))
        tiles.append(t)
        key.append(dict(tile=i, plate=c["plate"], page=c["page"], cls=c["cls"], group=c["group"], why=c["why"], box=[round(v, 1) for v in c["box"]], cell=c["cell"]))
    w, h = max(t.width for t in tiles), max(t.height for t in tiles)
    cols = 3
    sheet = Image.new("RGB", (cols * w, ((len(tiles) + cols - 1) // cols) * h), (255, 255, 255))
    for i, t in enumerate(tiles):
        ImageDraw.Draw(t).text((4, 4), str(i + 1), fill=(200, 0, 0))
        sheet.paste(t, ((i % cols) * w, (i // cols) * h))
    sheet.save(out / "tiles" / "sheet.png")
    (out / "key.json").write_text(json.dumps(dict(seed=a.seed, rule=__doc__, tiles=key), indent=1))
    (out / "tiles" / "README.md").write_text(
        "# Tiles for Sean\n\nEach picture is ONE staff window of a scanned page with ONE thin orange box and the ink one claim owns tinted blue. Nothing else is drawn.\n\n"
        "**Question, for every tile:** is the blue ink a rest, and ONLY the rest -- no part of a stem, a flag, a note, a letter or a sign?\n\nAnswer by tile number.\n")


if __name__ == "__main__":
    main()
