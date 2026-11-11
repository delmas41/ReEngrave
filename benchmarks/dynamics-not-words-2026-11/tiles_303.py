"""ROADMAP 2.303: blind tiles of EVERY dynamic claim the flag `OMR_LETTERS_ARE_THE_WORD` removes (and, with --controls, claims it leaves alone), the claimed ink tinted, every piece of the claim boxed.

    python3 benchmarks/dynamics-not-words-2026-11/tiles_303.py --off litolff=REC brahms=REC --on litolff=REC brahms=REC --pages litolff=8 brahms=0,14 --out DIR [--controls N] [--seed 2188]

REMOVED = a dynamic claim of the OFF record (owner `word`, source `dynamic_letters`) that the ON record no longer files as a dynamic over the same ink (no ON dynamic claim holds half of its box).
One tile per removed claim (the pieces of one claim, rows sharing a `letter_rows` set, are one tile): the window holds the WHOLE word the claim stands in (the READ word's box when one holds it, else
the OCR candidate's box when a probe is given, else 9 staff spaces either side), the tinted ink is the ink the OFF ledger gives that claim, a thin box on every piece of the claim. Nothing else
is drawn: no text, no arrow. The key (key.json, beside the sheet) names plate / page / box / the word it sat in / what OFF filed / what the rule did. The sheet: 3 columns, large numbers.
"""
import argparse
import collections
import json
import os
import pathlib
import random
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
UNIT = {"litolff": 15.75, "brahms": 32.0}
TINT = (0, 112, 255)


def share(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    return ix * iy / max(1.0, (a[2] - a[0]) * (a[3] - a[1]))


def dyn_claims(rows):
    out = []
    for o in rows["observations"]:
        d = o.get("detail") or {}
        if o["quantity"] == "claimed_area" and d.get("owner") == "word" and d.get("source") == "dynamic_letters" and isinstance(o.get("value"), list):
            out.append(dict(id=o["id"], box=[float(t) for t in o["value"]], text=d.get("text"), letter=d.get("detector_letter"), compound=bool(d.get("compound_of")),
                            letters=tuple(d.get("letter_rows") or ()), standing=d.get("standing", "READ"), sub=o["subject"]))
    return out


def words_of(rows):
    return [dict(box=[float(t) for t in o["detail"]["bbox_page_px"]], text=o["value"]) for o in rows["observations"]
            if o["quantity"] == "direction_word" and (o.get("detail") or {}).get("bbox_page_px")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--off", nargs="+", required=True)
    ap.add_argument("--on", nargs="+", required=True)
    ap.add_argument("--pages", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--controls", type=int, default=0)
    ap.add_argument("--seed", type=int, default=2188)
    ap.add_argument("--max", type=int, default=12)
    a = ap.parse_args()
    from PIL import Image, ImageDraw, ImageFont
    from tools.omr.staged import claim_readout as CR
    from tools.omr.staged import cell_map as CM
    from tools.omr.preprocessing import render_page
    import kind_patch
    kind_patch.apply()
    pages_of = {kv.split("=")[0]: [int(x) for x in kv.split("=")[1].split(",")] for kv in a.pages}
    rec = {"off": dict(kv.split("=", 1) for kv in a.off), "on": dict(kv.split("=", 1) for kv in a.on)}
    items = []
    rng = random.Random(a.seed)
    rowsets = {}
    for plate, pgs in pages_of.items():
        for pg in pgs:
            off = CR.read_rows(CR.resolve_source(rec["off"][plate]), [pg])
            on = CR.read_rows(CR.resolve_source(rec["on"][plate]), [pg])
            rowsets[(plate, pg)] = off
            offc, onc, words = dyn_claims(off), dyn_claims(on), words_of(off)
            groups = collections.OrderedDict()
            for c in offc:
                groups.setdefault(c["letters"] or (c["id"],), []).append(c)
            for key, pieces in groups.items():
                gone = all(not any(share(c["box"], k["box"]) >= 0.5 for k in onc) for c in pieces)
                if gone:
                    ub = [min(c["box"][0] for c in pieces), min(c["box"][1] for c in pieces), max(c["box"][2] for c in pieces), max(c["box"][3] for c in pieces)]
                    w = next((w for w in words if share(ub, w["box"]) >= 0.5), None)
                    items.append(dict(plate=plate, page=pg, role="removed by the flag", pieces=[c["box"] for c in pieces], ids=[c["id"] for c in pieces], union=ub,
                                      text=pieces[0]["text"] or ("letter " + str(pieces[0]["letter"])), word=(w or {}).get("text"), word_box=(w or {}).get("box"), standing=pieces[0]["standing"]))
    removed = len(items)
    if a.controls:
        kept = []
        for (plate, pg), off in rowsets.items():
            words = words_of(off)
            for c in dyn_claims(off):
                if any(share(c["box"], k["box"]) >= 0.5 for it in items if it["plate"] == plate and it["page"] == pg for k in [dict(box=b) for b in it["pieces"]]):
                    continue
                w = next((w for w in words if share(c["box"], w["box"]) >= 0.5), None)
                if w is not None:
                    kept.append(dict(plate=plate, page=pg, role="control: a dynamic inside a word box the rule leaves a dynamic", pieces=[c["box"]], ids=[c["id"]], union=c["box"],
                                     text=c["text"] or ("letter " + str(c["letter"])), word=w["text"], word_box=w["box"], standing=c["standing"]))
        rng.shuffle(kept)
        items += kept[:a.controls]
    if len(items) > a.max:
        keep = items[:removed][:a.max - a.controls] + items[removed:]
        items = keep[:a.max]
    rng.shuffle(items)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    W = 640
    font = ImageFont.load_default(size=64)
    tiles, key, cache = [], [], {}
    for n, it in enumerate(items, 1):
        plate, pg = it["plate"], it["page"]
        u = UNIT[plate]
        if (plate, pg) not in cache:
            cache.clear()
            rows = rowsets[(plate, pg)]
            ed = CR.edition_info(rows)
            pdf = CR.LIB / ed["edition_path"]
            canvas, _v, _pws, _cells = CR.build_page(rows, pdf, pg, CM.ROOT_DEFAULT, ledger=True)
            canvas.finish()
            cache[(plate, pg)] = (canvas, np.array(render_page(str(pdf), pg, dpi=600).rgb.copy()))
        canvas, rgb = cache[(plate, pg)]
        ub = it["union"]
        whole = it["word_box"] or [ub[0] - 9 * u, ub[1], ub[2] + 9 * u, ub[3]]
        bx0, by0, bx1, by1 = min(whole[0], ub[0]), min(whole[1], ub[1]), max(whole[2], ub[2]), max(whole[3], ub[3])
        x0, x1 = max(0, int(bx0 - 1.5 * u)), int(bx1 + 1.5 * u)
        y0, y1 = max(0, int(by0 - 2.0 * u)), int(by1 + 2.0 * u)
        crop = rgb[y0:y1, x0:x1].copy()
        bit = int(CR.FINE_BIT["dynamic"])
        fam = np.asarray(canvas.fam_eff)[y0:y1, x0:x1]
        st = np.asarray(canvas.state)[y0:y1, x0:x1]
        ink = np.asarray(canvas.ink)[y0:y1, x0:x1]
        mine = ink & ((fam & bit) != 0) & (st != CR.ST_WEAK) & (st != CR.ST_NONE)
        near = np.zeros(mine.shape, bool)      # only the ink of THIS claim's boxes (the ledger's dynamic family elsewhere in the window is another claim)
        for b in it["pieces"]:
            near[max(0, int(b[1]) - y0 - 2):max(0, int(b[3]) - y0 + 2), max(0, int(b[0]) - x0 - 2):max(0, int(b[2]) - x0 + 2)] = True
        mine &= near
        crop[mine] = TINT
        im = Image.fromarray(crop)
        dr = ImageDraw.Draw(im)
        for b in it["pieces"]:
            bb = [max(0, b[0] - x0), max(0, b[1] - y0), min(im.width - 1, b[2] - x0), min(im.height - 1, b[3] - y0)]
            dr.rectangle([round(v) for v in bb], outline=TINT, width=max(1, int(u / 16)))
        im = im.resize((W, int(W * im.height / im.width)))
        tiles.append(im)
        key.append(dict(tile=n, plate=plate, page=pg, role=it["role"], claim_ids=it["ids"], boxes=[[round(v, 1) for v in b] for b in it["pieces"]], off_filed_as=it["text"],
                        standing=it["standing"], word_it_sat_in=it["word"], word_box=it["word_box"], crop_origin=[x0, y0], tinted_px=int(mine.sum())))
        im.save(out / ("tile_%02d.png" % n))
    cols = 3
    rows_n = (len(tiles) + cols - 1) // cols
    h = max(t.height for t in tiles)
    sheet = Image.new("RGB", (cols * W + (cols - 1) * 6, rows_n * (h + 80)), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for n, t in enumerate(tiles):
        x, y = (n % cols) * (W + 6), (n // cols) * (h + 80)
        d.text((x + 4, y + 2), "%d" % (n + 1), fill=(0, 0, 0), font=font)
        sheet.paste(t, (x, y + 76))
    sheet.save(out / "sheet.png")
    (out / "key.json").write_text(json.dumps(key, indent=1, default=str))
    print("removed", removed, "tiles", len(key), collections.Counter(k["role"] for k in key))


if __name__ == "__main__":
    main()
