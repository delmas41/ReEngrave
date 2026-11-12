"""ROADMAP 2.304: blind tiles of the READ words that change between the OFF and ON arms (gained / lost / text changed), from two `owned_probe.py` outputs per plate.

    python3 benchmarks/text-reader-owned-ink-2026-11/tiles_2304.py --off litolff=P.json brahms=P.json --on litolff=P.json brahms=P.json --rec litolff=REC brahms=REC --pdf litolff=PDF brahms=PDF --out DIR [--max 12]

One tile per changed place: the page's own pixels (cut with pdftoppm at 600 dpi), one staff of the system (its five lines and the word's room, 6 spaces either side of the word), ONE thin box sized
to the whole word (the OCR candidate that was READ), nothing else drawn: no text, no arrow, no tint. key.json (beside the sheet) names plate / page / staff / bar / box / OFF reading / ON reading /
kind; nothing in the sheet says which arm read what.
"""
import argparse
import collections
import json
import os
import pathlib
import random
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
UNIT = {"litolff": 15.75, "brahms": 32.0}


def accepted(path):
    out = {}
    for pg in json.load(open(path)):
        by = collections.defaultdict(list)
        for r in pg["readings"]:
            by[r["candidate"]].append(r)
        for cd in pg["candidates"]:
            acc = sorted({r["accepted"] for r in by.get(cd["i"], []) if r["accepted"]})
            if acc:
                out.setdefault((pg["page"], cd["staff"], cd["measure"]), []).append(dict(box=cd["box"], text=acc))
    return out


def staff_lines(rec_path):
    from tools.omr.staged.record_io import load_record
    res = load_record(rec_path)
    rec = res.get("record", res)
    out = {}
    for r in rec["observations"]:
        if r["quantity"] == "staff_lines":
            m = r["subject"].split("/")
            out[(int(m[1]), int((r.get("detail") or {}).get("page_staff_index", -1)))] = r["value"]
    return out


def main():
    ap = argparse.ArgumentParser()
    for k in ("--off", "--on", "--rec", "--pdf"):
        ap.add_argument(k, nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max", type=int, default=12)
    ap.add_argument("--seed", type=int, default=2188)
    a = ap.parse_args()
    from PIL import Image, ImageDraw, ImageFont
    kv = lambda xs: dict(x.split("=", 1) for x in xs)  # noqa: E731
    off, on, rec, pdf = kv(a.off), kv(a.on), kv(a.rec), kv(a.pdf)
    items = []
    for plate in off:
        A, B = accepted(off[plate]), accepted(on[plate])
        sl = staff_lines(rec[plate])
        for k in sorted(set(A) | set(B)):
            x, y = A.get(k), B.get(k)
            tx, ty = sorted(t for c in (x or []) for t in c["text"]), sorted(t for c in (y or []) for t in c["text"])
            if tx == ty:
                continue
            kind = "gained" if not x else ("lost" if not y else "text changed")
            src = (y or x)[0]
            items.append(dict(plate=plate, page=k[0], staff=k[1], measure=k[2], box=src["box"], off=tx, on=ty, kind=kind, lines=sl.get((k[0], k[1]))))
    random.Random(a.seed).shuffle(items)
    items = items[:a.max]
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tiles, key = [], []
    for n, it in enumerate(items, 1):
        sp = UNIT[it["plate"]]
        b = it["box"]
        lines = it["lines"] or [b[1], b[3]]
        x0, x1 = int(b[0] - 6 * sp), int(b[2] + 6 * sp)
        y0, y1 = int(min(lines[0], b[1]) - 1.5 * sp), int(max(lines[-1], b[3]) + 1.5 * sp)
        png = out / ("raw_%02d" % n)
        subprocess.run(["pdftoppm", "-r", "600", "-f", str(it["page"] + 1), "-l", str(it["page"] + 1), "-x", str(max(0, x0)), "-y", str(max(0, y0)), "-W", str(x1 - max(0, x0)),
                        "-H", str(y1 - max(0, y0)), "-png", "-singlefile", pdf[it["plate"]], str(png)], check=True)
        im = Image.open(str(png) + ".png").convert("RGB")
        os.remove(str(png) + ".png")
        d = ImageDraw.Draw(im)
        d.rectangle([b[0] - max(0, x0), b[1] - max(0, y0), b[2] - max(0, x0), b[3] - max(0, y0)], outline=(220, 30, 30), width=2)
        tiles.append(im)
        key.append(dict(tile=n, plate=it["plate"], page=it["page"], staff=it["staff"], bar=it["measure"], box=[round(float(v), 1) for v in b], kind=it["kind"], off_read=it["off"], on_read=it["on"]))
    cols, W = 3, 760
    rows = []
    for i in range(0, len(tiles), cols):
        row = tiles[i:i + cols]
        rs = [t.resize((W, max(1, int(t.height * W / t.width)))) for t in row]
        h = max(r.height for r in rs) + 44
        canvas = Image.new("RGB", (cols * (W + 16), h), (255, 255, 255))
        for j, r in enumerate(rs):
            canvas.paste(r, (j * (W + 16) + 8, 40))
            ImageDraw.Draw(canvas).text((j * (W + 16) + 12, 8), str(i + j + 1), fill=(0, 0, 0), font=ImageFont.load_default(size=28) if hasattr(ImageFont, "load_default") else None)
        rows.append(canvas)
    sheet = Image.new("RGB", (rows[0].width, sum(r.height for r in rows)), (255, 255, 255)) if rows else Image.new("RGB", (10, 10), (255, 255, 255))
    yy = 0
    for r in rows:
        sheet.paste(r, (0, yy))
        yy += r.height
    sheet.save(out / "sheet.png")
    json.dump(key, open(out / "key.json", "w"), indent=1)
    print("tiles", len(tiles), "->", out)


main()
