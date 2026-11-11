"""ROADMAP 2.288 round 4 -- the blind tiles after the attachment/side rules.

    python3 benchmarks/rests-claim-first-2026-11/tiles_288_r4.py --out OUT --seed 2884 \
        --r3 litolff=R3_LITOLFF_RECORD brahms=R3_BRAHMS_RECORD --r4 litolff=R4_LITOLFF_RECORD brahms=R4_BRAHMS_RECORD \
        --pdf litolff=PDF brahms=PDF

SELECTION RULE (stated, seeded; read off the two ON records of the SAME pages: a whole/half rest claim = a `claimed_area` row, source `page_boxes`, cls restWhole/restHalf, keyed by
(cell, class); r3 = round 3's tree, r4 = this tree):
  1. every rest claim of ANY kind r4 NEWLY REFUSES (in r3, not in r4; whole/half, 16th, ...), up to 11, drawn with `random.Random(seed)` -- tile 4's kind first;
  2. then a seeded sample of the whole/half rests r4 STILL CLAIMS on the two Brahms pages (where the false claim was), 11 minus group 3 minus group 1;
  3. then tile 1's site (Brahms p14, detector box [2074.3, 2202.3, 2096.9, 2219.2], the real whole rest still refused).
Tiles are shuffled; the key is ONE LEVEL ABOVE the tile folder; nothing on a tile says which group it is from.
A TILE: one staff window of the deskewed 600 dpi page, ONE thin orange box at the claim's extent, the claimed ink tinted blue with the staff line NOT tinted (a row whose dark run reaches past
the stroke on both sides). Nothing else drawn. Question: "Is the blue ink a rest, and only the rest? Which kind? If not, what is it?"
"""
import argparse
import importlib.util
import json
import pathlib
import random
import sys

sys.path.insert(0, ".")
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from tools.omr.preprocessing import render_page

HERE = pathlib.Path(__file__).parent
_spec = importlib.util.spec_from_file_location("t3", HERE / "tiles_288_r3.py")
T3 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T3)

TILE1 = dict(plate="brahms", page=14, box=[2074.3, 2202.3, 2096.9, 2219.2])


def claims_of(record, pages):
    rec = json.load(open(record))["record"]
    claims, strokes = {}, {}
    for o in rec["observations"]:
        d = o.get("detail") or {}
        if o["quantity"] == "page_stroke" and o["value"] != "barline":
            pg = int(o["subject"].split("/")[1])
            if pg in pages:
                strokes.setdefault(pg, {})[d["ordinal"]] = d
        if o["quantity"] == "claimed_area" and d.get("source") == "page_boxes" and d.get("unit") == "page_ink" and str(d.get("cls", "")).startswith("rest"):
            pg = int(o["subject"].split("/")[1])
            if pg in pages:
                claims[(o["subject"], d["cls"])] = dict(subject=o["subject"], cls=d["cls"], page=pg, ids=list(d["page_strokes"]))
    return claims, strokes


def font(n):
    for p in ("/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Supplemental/Arial.ttf"):
        try:
            return ImageFont.truetype(p, n)
        except Exception:
            pass
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=2884)
    ap.add_argument("--r3", nargs="+", required=True)
    ap.add_argument("--r4", nargs="+", required=True)
    ap.add_argument("--pdf", nargs="+", required=True)
    ap.add_argument("--pages", nargs="+", default=["litolff=2,8", "brahms=14,19"])
    a = ap.parse_args()
    kv = lambda xs: dict(x.split("=", 1) for x in xs)
    r3, r4, pdf, pg = kv(a.r3), kv(a.r4), kv(a.pdf), {k: [int(p) for p in v.split(",")] for k, v in kv(a.pages).items()}
    out = pathlib.Path(a.out)
    (out / "tiles").mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    refused, still, data = [], [], {}
    for plate in r4:
        c3, _ = claims_of(r3[plate], pg[plate])
        c4, st4 = claims_of(r4[plate], pg[plate])
        data[plate] = st4
        # r3 strokes for a claim r4 dropped: read them from the r3 record
        c3b, st3 = claims_of(r3[plate], pg[plate])
        for k in sorted(set(c3) - set(c4)):
            refused.append(dict(plate=plate, group="newly-refused", strokes=st3, **c3[k]))
        for k in sorted(set(c4) & set(c3)):
            if plate == "brahms" and k[1] in ("restWhole", "restHalf"):
                still.append(dict(plate=plate, group="still-claimed", strokes=st4, **c4[k]))
        for k in sorted(set(c4) - set(c3)):
            if plate == "brahms" and k[1] in ("restWhole", "restHalf"):
                still.append(dict(plate=plate, group="newly-claimed-by-r4", strokes=st4, **c4[k]))
    rng.shuffle(refused)
    chosen = refused[:11]
    rng.shuffle(still)
    chosen += still[:max(0, 11 - len(chosen))]
    chosen.append(dict(plate=TILE1["plate"], group="tile-1-site", page=TILE1["page"], cls="restWhole", subject="cell/14/0/7/2", ids=[], box=TILE1["box"], strokes=data[TILE1["plate"]]))
    n_ref = sum(c["group"] == "newly-refused" for c in chosen)
    rng.shuffle(chosen)
    cache, tiles, key = {}, [], []
    for i, c in enumerate(chosen, 1):
        k2 = (c["plate"], c["page"])
        if k2 not in cache:
            cache[k2] = render_page(pdf[c["plate"]], c["page"], 600)
        sts = c["strokes"].get(c["page"], {})
        ids = c["ids"] or [j for j in T3.overlapping(sts, c["box"]) if sts[j]["bbox_page_px"] and sts[j].get("length_spaces", 0) < 6]
        sbs = [sts[j]["bbox_page_px"] for j in ids if j in sts]
        box = c.get("box")
        if sbs and not box:
            box = [min(b[0] for b in sbs), min(b[1] for b in sbs), max(b[2] for b in sbs), max(b[3] for b in sbs)]
        sps = [d["staff_space_local_px"] for d in sts.values() if d.get("staff_space_local_px")]
        sp = float(np.median(sps)) if sps else 25.0
        t = T3.tile(cache[k2], box, sbs, sp)
        t.save(out / "tiles" / ("tile_%02d.png" % i))
        tiles.append(t)
        key.append(dict(tile=i, plate=c["plate"], page=c["page"], cls=c["cls"], group=c["group"], box=[round(v, 1) for v in box], ids=ids, cell=c["subject"]))
    w, h = max(t.width for t in tiles), max(t.height for t in tiles)
    cols = 3
    sheet = Image.new("RGB", (cols * w, ((len(tiles) + cols - 1) // cols) * h), (255, 255, 255))
    f = font(54)
    for i, t in enumerate(tiles):
        d = ImageDraw.Draw(t)
        d.rectangle([0, 0, 78, 70], fill=(255, 255, 255))
        d.text((6, 2), str(i + 1), fill=(200, 0, 0), font=f)
        sheet.paste(t, ((i % cols) * w, (i // cols) * h))
    sheet.save(out / "tiles" / "sheet.png")
    (out / "key.json").write_text(json.dumps(dict(seed=a.seed, rule=__doc__, n_newly_refused=n_ref, tiles=key), indent=1))
    (out / "tiles" / "README.md").write_text(
        "# Tiles for Sean\n\nEach picture is ONE staff window of a scanned page with ONE thin orange box and some ink tinted blue (the staff line is not tinted). Nothing else is drawn.\n\n"
        "**Question, for every tile:** is the blue ink a rest, and ONLY the rest (no part of a note, a stem, a beam, a letter or a sign)? Which kind: whole, half, or something else? If not a rest, what is it?\n\nAnswer by tile number.\n")
    print("tiles", len(tiles), "newly refused in tiles", n_ref, "of", len(refused))


if __name__ == "__main__":
    main()
