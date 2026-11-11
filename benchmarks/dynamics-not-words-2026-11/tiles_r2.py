"""ROADMAP 2.301 r1: 12 blind tiles of the page-claim replay (`replay_claims`), the claimed ink TINTED, one thin box, nothing else drawn.

    python3 benchmarks/dynamics-not-words-2026-11/tiles_r2.py --out DIR [--seed 2301]

Both arms (flag `OMR_WORD_OWNS_ITS_INK` OFF and ON) are replayed on this tree for Litolff p8 and Brahms p0, p14 (saved gather rows, the real master cell map, no OCR); the ink whose
KIND the ledger moves between the arms names the places that CHANGED. SEEDED RULE: (1) every marking holding a changed place comes first (its word tile, and its dynamic's tile when
the moved ink was the dynamic's); (2) then a seeded draw of dynamics the flag did not touch (compound or lone), at least 2 on Litolff. The tinted ink is the ink the ledger gives the
tile's KIND (ON arm) anywhere in the window, never the claim's rectangle (so a letter of another mark that is wrongly blue shows); the thin box is the extent of ALL the pieces of the
marking's claim (a word of two pieces is boxed whole: 2.296 r1 tile 3 boxed one piece and cut the window mid-word). Window: 12 staff spaces wide or the box plus 2, the claim's height
+- 2.5 spaces. Sheet: 3 columns, large numbers, no insets; key.json beside it. Nothing of ours is written on a tile.
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
LIBR = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records")
PAGES = [("litolff", "claim-readout-slices-litolff-p8-main", 8, 15.75),
         ("brahms", "claim-readout-slices-2284b-r2-brahms.on.gathered", 0, 32.0),
         ("brahms", "claim-readout-slices-brahms-p14-main", 14, 32.0)]
TINT = (0, 112, 255)


def markings(claims):
    """`{owner_row: {"word": [rects], "dynamic": [rects], "text": str}}` of the replay's claim rows (a marking = the direction word row and its split dynamics)."""
    out = collections.defaultdict(lambda: {"word": [], "dynamic": [], "text": None})
    for c in claims:
        if c["source"] == "direction_word":
            m = out[c["owner_row"]]
            m["word"].append(c["box"])
            m["text"] = c["text"]
        elif c["source"] == "dynamic_letters" and c.get("compound_of"):
            out[c["compound_of"]]["dynamic"].append(c["box"])
    return out


def union(rects):
    return [min(r[0] for r in rects), min(r[1] for r in rects), max(r[2] for r in rects), max(r[3] for r in rects)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=2301)
    a = ap.parse_args()
    from PIL import Image, ImageDraw, ImageFont
    from tools.omr.staged import claim_readout as CR
    from tools.omr.staged import lane_report as LR
    from tools.omr.preprocessing import render_page
    import ledger_probe as LP
    import ledger_diff as LD
    flag = "OMR_WORD_OWNS_ITS_INK"
    items, drawn_pool = [], []
    pages = {}
    for plate, slc, pg, unit in PAGES:
        sd = LIBR / slc
        c_off, g_off = LP.canvas_of(plate, sd, pg, {flag: "0"})
        m_off, names = LD.kind_map(c_off)
        del c_off
        canvas, got = LP.canvas_of(plate, sd, pg, {flag: "1"})
        m_on, _ = LD.kind_map(canvas)
        import cv2
        moved = m_off != m_on
        n, lab, st, _c = cv2.connectedComponentsWithStats(moved.astype(np.uint8), connectivity=8)
        regions = []
        for k in range(1, n):
            x, y, w, h, area = (int(v) for v in st[k])
            if area >= 6:
                sub = lab[y:y + h, x:x + w] == k
                fa = collections.Counter(names[v - 1] if v else "-" for v in m_off[y:y + h, x:x + w][sub].tolist())
                fb = collections.Counter(names[v - 1] if v else "-" for v in m_on[y:y + h, x:x + w][sub].tolist())
                regions.append(dict(box=[x, y, x + w, y + h], px=area, a=dict(fa), b=dict(fb)))
        mk = markings(got["claims"])
        pages[(plate, pg)] = (canvas, unit, sd)
        for reg in regions:
            cx, cy = (reg["box"][0] + reg["box"][2]) / 2, (reg["box"][1] + reg["box"][3]) / 2
            hit = None
            for oid, m in mk.items():
                for r in m["word"] + m["dynamic"]:
                    if r[0] - 2 <= cx <= r[2] + 2 and r[1] - 2 <= cy <= r[3] + 2:
                        hit = oid
                        break
                if hit:
                    break
            if hit is None:
                items.append(dict(plate=plate, page=pg, kind="word", box=reg["box"], text=None, role="changed place (no marking holds it)", region=reg))
                continue
            m = mk[hit]
            it = dict(plate=plate, page=pg, kind="word", box=union(m["word"]), text=m["text"], role="changed: the word of a marking", region=reg, marking=hit)
            if not any(i.get("marking") == hit and i["plate"] == plate and i["kind"] == "word" for i in items):
                items.append(it)
            if m["dynamic"] and "dynamic" in reg["a"] and not any(i.get("marking") == hit and i["plate"] == plate and i["kind"] == "dynamic" for i in items):
                items.append(dict(plate=plate, page=pg, kind="dynamic", box=union(m["dynamic"]), text=m["text"], role="changed: the same marking's dynamic", region=reg, marking=hit))
        for oid, m in mk.items():
            for r in m["dynamic"]:
                drawn_pool.append(dict(plate=plate, page=pg, kind="dynamic", box=r, text=m["text"], role="a dynamic the flag did not move", marking=oid))
        for c in got["claims"]:
            if c["source"] == "dynamic_letters" and not c.get("compound_of"):
                drawn_pool.append(dict(plate=plate, page=pg, kind="dynamic", box=c["box"], text=None, role="a dynamic the flag did not move (lone)", marking=None))
        del got
    items = items[:12]
    rng = random.Random(a.seed)
    pool = sorted([d for d in drawn_pool if not any(d["plate"] == i["plate"] and d["page"] == i["page"] and abs(d["box"][0] - i["box"][0]) < 60 and abs(d["box"][1] - i["box"][1]) < 80 for i in items)],
                  key=lambda d: (d["plate"], d["page"], d["box"]))
    rng.shuffle(pool)
    lit = [d for d in pool if d["plate"] == "litolff"][:2]
    pick = list(items)
    for d in lit:
        if len(pick) < 12:
            pick.append(d)
    for d in pool:
        if len(pick) >= 12:
            break
        if d in pick or any(d["plate"] == p["plate"] and d["page"] == p["page"] and abs(d["box"][0] - p["box"][0]) < 60 and abs(d["box"][1] - p["box"][1]) < 80 for p in pick):
            continue
        pick.append(d)
    rng.shuffle(pick)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("tile_*.png"):
        f.unlink()
    W = 640
    font = ImageFont.load_default(size=72)
    tiles, key, rgbs = [], [], {}
    for n, it in enumerate(pick, 1):
        canvas, u, sd = pages[(it["plate"], it["page"])]
        pdf = LR.LIB / LR.PLATES[it["plate"]]["pdf"]
        if (it["plate"], it["page"]) not in rgbs:
            rgbs[(it["plate"], it["page"])] = np.array(render_page(str(pdf), it["page"], dpi=600).rgb.copy())
        rgb = rgbs[(it["plate"], it["page"])]
        bx = it["box"]
        cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
        half = max(6 * u, (bx[2] - bx[0]) / 2 + 1.0 * u)
        x0, x1 = max(0, int(cx - half)), int(cx + half)
        y0, y1 = max(0, int(min(cy - 3.5 * u, bx[1] - 2.5 * u))), int(max(cy + 3.5 * u, bx[3] + 2.5 * u))
        crop = rgb[y0:y1, x0:x1].copy()
        bit = int(CR.FINE_BIT[it["kind"]])
        fam = np.asarray(canvas.fam_eff)[y0:y1, x0:x1]
        stt = np.asarray(canvas.state)[y0:y1, x0:x1]
        ink = np.asarray(canvas.ink)[y0:y1, x0:x1]
        mine = ink & ((fam & bit) != 0) & (stt != CR.ST_WEAK) & (stt != CR.ST_NONE)
        crop[mine] = TINT
        im = Image.fromarray(crop)
        dr = ImageDraw.Draw(im)
        bb = [max(0, bx[0] - x0), max(0, bx[1] - y0), min(im.width - 1, bx[2] - x0), min(im.height - 1, bx[3] - y0)]
        dr.rectangle([round(v) for v in bb], outline=TINT, width=max(1, int(u / 16)))
        im = im.resize((W, int(W * im.height / im.width)))
        im.save(out / ("tile_%02d.png" % n))
        tiles.append(im)
        key.append({k: v for k, v in it.items()} | dict(tile=n, crop_origin=[x0, y0], tinted_px=int(mine.sum()), tint="the ink the ledger gives %s (flag ON)" % it["kind"]))
    cols = 3
    rows_n = (len(tiles) + cols - 1) // cols
    h = max(t.height for t in tiles)
    sheet = Image.new("RGB", (cols * W + (cols - 1) * 6, rows_n * (h + 90)), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for n, t in enumerate(tiles):
        x, y = (n % cols) * (W + 6), (n // cols) * (h + 90)
        d.text((x + 4, y + 2), "%d" % (n + 1), fill=(0, 0, 0), font=font)
        sheet.paste(t, (x, y + 86))
    sheet.save(out / "sheet.png")
    (out / "key.json").write_text(json.dumps(key, indent=1, default=str))
    print("tiles", len(key), collections.Counter(k["role"] for k in key))


if __name__ == "__main__":
    main()
