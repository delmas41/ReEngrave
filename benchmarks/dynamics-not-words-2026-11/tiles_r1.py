"""ROADMAP 2.296 measure (c): 12 blind tiles, ink the ledger now gives a DYNAMIC (or a WORD) TINTED, one thin box at the claim's extent, nothing else drawn.

    python3 benchmarks/dynamics-not-words-2026-11/tiles_r1.py --on litolff=REC brahms=REC [--off litolff=REC brahms=REC] --out OUTDIR [--seed 2188]

SEEDED RULE (random.Random(seed), pools sorted before the draw):
  1. every mark LOST or CHANGED in the exported file by the flag (the lane report's `report.json` changes, passed as --changes JSON; none = none) comes first;
  2. then dynamics NEWLY OWNED AS DYNAMICS (an ON claim that carries `compound_of`: a marking's dynamic, split out of its word): 2 of them from Litolff
     where Litolff has any, the rest across both plates, at least 2 of the compounds being on Brahms p14 / Litolff ('p dolce', 'p cresc. f', 'sempre piu p');
  3. then 3 WORD tiles: the word's own claim of a split marking (what the word still owns: `legato`, `dolce`), tinted as a word;
  4. then 2 CONTROLS: a lone dynamic claim the flag did not touch (Brahms p0, in Sean's own page-pass labels as `f`).
Window: 12 staff spaces wide, the claim's height +- 2.5 spaces (one staff, or the gap between two). The tinted ink is the ink the ledger's ONE settle gives that kind
(`claim_readout` ledger canvas, a dynamic claim named a dynamic: `kind_patch`), never the claim's rectangle; the thin box is the claim's extent, never wider than the tile.
Sheet: 3 columns, large numbers, no insets. Key one level above the tiles folder. Nothing of ours is written on a tile.
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


def claims_of(rows, pages):
    """`{page: [claim row]}` of the page-wide word-owner claims (READ) of `rows`."""
    from tools.omr.staged import claim_readout as CR
    out = collections.defaultdict(list)
    for o in rows["observations"]:
        d = o.get("detail") or {}
        if o.get("quantity") != "claimed_area" or d.get("owner") != "word" or d.get("standing", "READ") != "READ":
            continue
        v = o.get("value")
        if not (isinstance(v, list) and len(v) == 4 and all(isinstance(t, (int, float)) for t in v)):
            continue
        pg = CR.page_of_subject(o["subject"])
        if pg in pages:
            out[pg].append(o)
    return out


def select(plate_rows, pages_of, seed, changes):
    rng = random.Random(seed)
    new_dyn, words, lone = [], [], []
    for plate, rows in plate_rows.items():
        for pg, cl in claims_of(rows, set(pages_of[plate])).items():
            for o in cl:
                d = o["detail"]
                it = dict(plate=plate, page=pg, row=o["id"], box=[float(t) for t in o["value"]], text=d.get("text") or d.get("detector_letter"))
                if d.get("source") == "dynamic_letters" and d.get("compound_of"):
                    new_dyn.append(dict(it, kind="dynamic", what="a marking's dynamic, split out of its word", compound_of=d["compound_of"]))
                elif d.get("source") == "direction_word" and d.get("dynamic_left_out"):
                    words.append(dict(it, kind="word", what="the word of a split marking (what the word still owns)", text=d.get("text")))
                elif d.get("source") == "dynamic_letters" and d.get("lone") and plate == "brahms" and pg == 0 and not d.get("compound_of"):
                    lone.append(dict(it, kind="dynamic", what="control: a lone dynamic claim the flag did not touch"))
    pick = [dict(c, role="changed in the file") for c in changes][:12]

    def draw(pool, n, role, want=None):
        pool = sorted(pool, key=lambda it: (it["plate"], it["page"], it["box"]))
        rng.shuffle(pool)
        got = []
        for it in pool:
            if len(got) >= n:
                break
            if any(it["plate"] == p["plate"] and it["page"] == p["page"] and abs(it["box"][0] - p["box"][0]) < 40 and abs(it["box"][1] - p["box"][1]) < 60
                   for p in pick):
                continue
            got.append(dict(it, role=role))
            pick.append(got[-1])
        return got
    room = 12 - len(pick)
    lit = [d for d in new_dyn if d["plate"] == "litolff"]
    if room > 0:
        draw(lit, min(2, room, len(lit)), "newly a dynamic")
    room = 12 - len(pick)
    nd = max(0, min(room - 5, room))
    if nd > 0:
        draw([d for d in new_dyn if not any(d is p or d["row"] == p["row"] for p in pick)], nd, "newly a dynamic")
    room = 12 - len(pick)
    if room > 2:
        draw(words, min(3, room - 2), "word of a split marking")
    room = 12 - len(pick)
    if room > 0:
        draw(lone, room, "control")
    rng.shuffle(pick)
    return pick


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--on", nargs="+", required=True)
    ap.add_argument("--pages", nargs="+", required=True, help="plate=p,p")
    ap.add_argument("--changes", default=None, help="a JSON list of items {plate, page, box, text, kind, what} the flag lost / changed in the file")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=2188)
    a = ap.parse_args()
    from PIL import Image, ImageDraw, ImageFont
    from tools.omr.staged import claim_readout as CR
    from tools.omr.staged import cell_map as CM
    from tools.omr.staged import lane_report as LR
    from tools.omr.preprocessing import render_page
    import kind_patch
    kind_patch.apply()
    pages_of = {kv.split("=")[0]: [int(x) for x in kv.split("=")[1].split(",")] for kv in a.pages}
    srcs = {kv.split("=")[0]: CR.cut_record(pathlib.Path(kv.split("=", 1)[1])) for kv in a.on}
    plate_rows = {p: CR.read_rows(s, pages_of[p]) for p, s in srcs.items()}
    changes = json.loads(pathlib.Path(a.changes).read_text()) if a.changes else []
    items = select(plate_rows, pages_of, a.seed, changes)
    out = pathlib.Path(a.out)
    tdir = out / "tiles"
    tdir.mkdir(parents=True, exist_ok=True)
    for f in tdir.glob("*"):
        f.unlink()
    W = 640
    font = ImageFont.load_default(size=64)
    tiles, key = [], []
    cache = {}
    for n, it in enumerate(items, 1):
        plate, pg = it["plate"], it["page"]
        if (plate, pg) not in cache:
            cache.clear()
            rows = plate_rows[plate]
            ed = CR.edition_info(rows)
            pdf = CR.LIB / ed["edition_path"]
            canvas, _v, _pws, _cells = CR.build_page(rows, pdf, pg, CM.ROOT_DEFAULT, ledger=True)
            canvas.finish()
            rgb = np.array(render_page(str(pdf), pg, dpi=600).rgb.copy())
            cache[(plate, pg)] = (canvas, rgb)
        canvas, rgb = cache[(plate, pg)]
        u = UNIT[plate]
        bx = it["box"]
        cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
        x0, x1 = max(0, int(cx - 6 * u)), int(cx + 6 * u)
        y0, y1 = max(0, int(min(cy - 3.5 * u, bx[1] - 2.5 * u))), int(max(cy + 3.5 * u, bx[3] + 2.5 * u))
        crop = rgb[y0:y1, x0:x1].copy()
        bit = int(CR.FINE_BIT[it["kind"]])
        fam = np.asarray(canvas.fam_eff)[y0:y1, x0:x1]
        st = np.asarray(canvas.state)[y0:y1, x0:x1]
        ink = np.asarray(canvas.ink)[y0:y1, x0:x1]
        mine = ink & ((fam & bit) != 0) & (st != CR.ST_WEAK) & (st != CR.ST_NONE)
        crop[mine] = TINT
        im = Image.fromarray(crop)
        dr = ImageDraw.Draw(im)
        bb = [max(0, bx[0] - x0), max(0, bx[1] - y0), min(im.width - 1, bx[2] - x0), min(im.height - 1, bx[3] - y0)]
        dr.rectangle([round(v) for v in bb], outline=TINT, width=max(1, int(u / 16)))
        im = im.resize((W, int(W * im.height / im.width)))
        im.save(tdir / ("tile_%02d.png" % n))
        tiles.append(im)
        key.append({k: v for k, v in it.items()} | dict(tile=n, crop_origin=[x0, y0], tinted_px=int(mine.sum()), tint="the ink the ledger gives %s" % it["kind"]))
    cols = 3
    rows_n = (len(tiles) + cols - 1) // cols
    h = max(t.height for t in tiles)
    sheet = Image.new("RGB", (cols * W + (cols - 1) * 6, rows_n * (h + 80)), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for n, t in enumerate(tiles):
        x, y = (n % cols) * (W + 6), (n // cols) * (h + 80)
        d.text((x + 4, y + 2), "%d" % (n + 1), fill=(0, 0, 0), font=font)
        sheet.paste(t, (x, y + 76))
    sheet.save(tdir / "sheet.png")
    (tdir / "README.md").write_text(
        "# 2.296 tiles\n\nEach picture is a piece of a scanned score page. The blue ink is the ink we claim for ONE mark, and the thin blue box is the extent "
        "of that claim; nothing else is drawn.\n\n**Question, for every tile:** is the blue ink a dynamic or a word -- which one exactly (for example sf, p, dolce)? "
        "Is anything of another mark blue?\n\nAnswer by tile number.\n")
    (out / "key.json").write_text(json.dumps(key, indent=1, default=str))
    print("tiles", len(key), collections.Counter(k["role"] for k in key))


main()
