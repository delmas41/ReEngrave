"""ROADMAP 2.288 round 3 -- the blind tiles of WHOLE / HALF REST claims whose block the detector box holds but the page stroke carries a slab of its staff line
(`page_claim_names.block_rest_strokes`).

    python3 benchmarks/rests-claim-first-2026-11/tiles_288_r3.py --out OUT --seed 2883 \
        litolff:ON_RECORD.json:PDF:2,8 brahms:ON_RECORD.json:PDF:14,19

SELECTION RULE (stated, seeded; read off the census row of the ON records: `rest_block_named_boxes` = whole/half rest boxes this round's block share newly names, and
`rest_weak_boxes` with why `names_no_stroke` and class restWhole / restHalf = boxes still refused):
  1. up to 9 newly claimed whole/half rests, drawn with `random.Random(seed)` alternating between the plates (Litolff first; when one plate's pool is empty the other fills);
  2. then 3 still-refused whole/half boxes (`names_no_stroke`), drawn the same way (alternating, seeded);
  12 tiles in all. Tiles are shuffled; the key is ONE LEVEL ABOVE the tile folder; nothing on a tile says which group it is from.

A TILE shows ONE staff window of the deskewed 600 dpi page (about 18 spaces wide, 11 tall), ONE thin orange box, and the ink tinted blue. For a claimed rest the box is the extent of the
page strokes the claim owns and the blue is those strokes' dark pixels MINUS the staff-line pixels (a row the dark run of which reaches past the stroke on both sides); for a refused
box the box is the detector's and the blue is the dark pixels of the strokes it overlaps, the same way. Nothing else is drawn.
Question for Sean: is the blue ink a rest, and ONLY the rest? Which kind (whole / half / other)?
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
                strokes.setdefault(pg, {})[o["detail"]["ordinal"]] = o["detail"]
        d = o.get("detail") or {}
        if d.get("source") == "page_boxes" and d.get("unit") == "page_ink_census" and sub.startswith("page/"):
            pg = int(sub.split("/")[1])
            if pg in pages:
                census.append((pg, d))
    return strokes, census


def overlapping(strokes, box):
    out = []
    for i, d in strokes.items():
        x0, y0, x1, y1 = d["bbox_page_px"]
        if min(x1, box[2]) > max(x0, box[0]) and min(y1, box[3]) > max(y0, box[1]):
            out.append(i)
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
            line = sx0 - 5 >= 0 and row[sx0 - 5:sx0].all() and row[sx1:min(W, sx1 + 5)].all()
            if line:
                continue                                    # a staff-line pixel: the dark run reaches past the stroke box on both sides
            for x in xs:
                im[y - Y0, x - X0] = (0, 120, 255)
    pil = Image.fromarray(im)
    ImageDraw.Draw(pil).rectangle([x0 - X0 - 2, y0 - Y0 - 2, x1 - X0 + 2, y1 - Y0 + 2], outline=(255, 140, 0), width=1)
    return pil


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=2883)
    ap.add_argument("plates", nargs="+")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    (out / "tiles").mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    pdfs, data, claimed, refused = {}, {}, [], []
    for spec in a.plates:
        plate, rec, pdf, pages = spec.split(":")
        pages = [int(p) for p in pages.split(",")]
        pdfs[plate] = pdf
        strokes, census = load(rec, pages)
        data[plate] = strokes
        for pg, d in census:
            for cls, box, ids, cell in d.get("rest_block_named_boxes", []):
                claimed.append(dict(plate=plate, page=pg, cls=cls, box=box, ids=ids, cell=cell))
            for cls, box, why, cell in d.get("rest_weak_boxes", []):
                if why == "names_no_stroke" and cls in ("restWhole", "restHalf"):
                    refused.append(dict(plate=plate, page=pg, cls=cls, box=box, ids=[], cell=cell))

    def draw(pool_items, n, group):
        pools = {p: sorted([r for r in pool_items if r["plate"] == p], key=lambda r: (r["page"], r["box"])) for p in data}
        for p in pools:
            rng.shuffle(pools[p])
        order, k, got = list(pools), 0, []
        while len(got) < n and any(pools.values()):
            p = order[k % len(order)]
            k += 1
            if pools[p]:
                got.append(dict(pools[p].pop(), group=group))
        return got

    chosen = draw(claimed, 9, "newly-claimed")
    chosen += draw(refused, 12 - len(chosen) if len(chosen) < 9 else 3, "still-refused")
    rng.shuffle(chosen)
    cache, tiles, key = {}, [], []
    for i, c in enumerate(chosen, 1):
        k2 = (c["plate"], c["page"])
        if k2 not in cache:
            cache[k2] = render_page(pdfs[c["plate"]], c["page"], 600)
        sts = data[c["plate"]].get(c["page"], {})
        ids = c["ids"] or [j for j in overlapping(sts, c["box"]) if sts[j]["bbox_page_px"] and sts[j].get("length_spaces", 0) < 6]
        sbs = [sts[j]["bbox_page_px"] for j in ids]
        box = c["box"]
        if c["group"] == "newly-claimed" and sbs:
            box = [min(b[0] for b in sbs), min(b[1] for b in sbs), max(b[2] for b in sbs), max(b[3] for b in sbs)]
        sps = [d["staff_space_local_px"] for d in sts.values() if d.get("staff_space_local_px")]
        sp = float(np.median(sps)) if sps else 25.0
        t = tile(cache[k2], box, sbs, sp)
        t.save(out / "tiles" / ("tile_%02d.png" % i))
        tiles.append(t)
        key.append(dict(tile=i, plate=c["plate"], page=c["page"], cls=c["cls"], group=c["group"], box=[round(v, 1) for v in box], detector_box=[round(v, 1) for v in c["box"]],
                        ids=ids, cell=c["cell"]))
    w, h = max(t.width for t in tiles), max(t.height for t in tiles)
    cols = 3
    sheet = Image.new("RGB", (cols * w, ((len(tiles) + cols - 1) // cols) * h), (255, 255, 255))
    for i, t in enumerate(tiles):
        ImageDraw.Draw(t).text((4, 4), str(i + 1), fill=(200, 0, 0))
        sheet.paste(t, ((i % cols) * w, (i // cols) * h))
    sheet.save(out / "tiles" / "sheet.png")
    (out / "key.json").write_text(json.dumps(dict(seed=a.seed, rule=__doc__, tiles=key), indent=1))
    (out / "tiles" / "README.md").write_text(
        "# Tiles for Sean\n\nEach picture is ONE staff window of a scanned page with ONE thin orange box and some ink tinted blue. Nothing else is drawn.\n\n"
        "**Question, for every tile:** is the blue ink a rest, and ONLY the rest (no part of a note, a stem, a beam, a letter or a sign)? Which kind: whole, half, or something else?\n\nAnswer by tile number.\n")


if __name__ == "__main__":
    main()
