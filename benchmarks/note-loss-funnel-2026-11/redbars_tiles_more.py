"""ROADMAP 2.311 -- 24 MORE RANDOM RED BARS (12 per plate) as blind tiles for Sean, two sheets of 12, drawn exactly like `redbars_tiles.py`.

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/note-loss-funnel-2026-11/redbars_tiles_more.py \
        --lit LIT.facts.json --lit-record LIT.record.json --bra BRA.facts.json --bra-record BRA.record.json \
        --ranking benchmarks/note-loss-funnel-2026-11/redbar-ranking.json --out out/print/2.311-redbars

Population: every red-marked bar of the exported file on the count pages (the 309 Litolff / 276 Brahms of `redbars.red_bars`), Brahms page 0 and
the 12 bars of `out/print/2.311-redbars-key.json` left out. random.Random(2311005): 12 Litolff then 12 Brahms, from the list sorted by
(page, system, staff, cell). Sheet b = Litolff 1-6 then Brahms 1-6 of the draw; sheet c = Litolff 7-12 then Brahms 7-12. Not by cause.
Tile (same as the 12 before): one staff, the bar barline to barline in one thin orange box on THIS staff only, a full neighbouring bar either side,
this staff's own heads and ledger lines whole, 1250 px wide, two to a row. The keys (outside the folders) carry the classifier's row for each bar.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from checksheet import page_image
from redbars import run as red_run
from redbars_tiles import ORANGE, SAMPLE, bar_marks, f_glyphs, meters_by_part, staff_geometry


def draw_tile(plate, f, geo, b, nout=1250):
    g = geo
    st = g["staff/%d/%d/%d" % (b["page"], b["system"], b["staff"])]
    cell = g["cell/%d/%d/%d/%d" % (b["page"], b["system"], b["staff"], b["cell"])]["cell"]
    lines = st["lines"]
    sp = (lines[4] - lines[0]) / 4.0
    im = page_image(plate, b["page"])
    ext = st["extent"]
    gray = np.asarray(im.convert("L"))
    ya, yb = int(lines[0]), int(lines[4])

    def snap(x):
        xs = range(max(0, int(x - 1.2 * sp)), min(gray.shape[1], int(x + 1.2 * sp)))
        fr = {xx: float((gray[ya:yb, xx] < 128).mean()) for xx in xs}
        best = max(fr.values())
        if best < 0.9:
            return x, False
        cols = [xx for xx in xs if fr[xx] >= 0.9 * best and fr[xx] > 0.8]
        c0 = min(cols, key=lambda xx: abs(xx - x))
        lo = hi = c0
        while lo - 1 in cols:
            lo -= 1
        while hi + 1 in cols:
            hi += 1
        return (lo + hi) / 2.0, True
    bx0, s0 = snap(cell[0])
    bx1, s1 = snap(cell[2])
    by0, by1 = lines[0] - 1.0 * sp, lines[4] + 1.0 * sp
    stv = [v for k, v in g["_page_staves"].items() if "lines" in v and "extent" in v and v["lines"] != lines
           and v["extent"][0] < bx1 and v["extent"][1] > bx0]
    above = [v["lines"][4] for v in stv if v["lines"][4] < lines[0]]
    below = [v["lines"][0] for v in stv if v["lines"][0] > lines[4]]
    up_nb, dn_nb = (max(above) if above else None), (min(below) if below else None)
    top = (lines[0] + up_nb) / 2 if up_nb is not None else lines[0] - 8 * sp
    bot = (lines[4] + dn_nb) / 2 if dn_nb is not None else lines[4] + 8 * sp
    pre = "glyph/%d/%d/%d/%d/" % (b["page"], b["system"], b["staff"], b["cell"])
    own = [gl for k, gl in f_glyphs(f, pre) if (gl["head"] or gl["rest"]) and not (gl["fate"] or "").startswith(
        ("owned_by_another", "not_a_notehead:belongs_to_a_nearer"))]
    lg = [gl for k, gl in f_glyphs(f, pre) if gl["cls"] == "ledgerLine"
          and any(o["box"][0] - sp <= (gl["box"][0] + gl["box"][2]) / 2 <= o["box"][2] + sp for o in own)]
    need_top = min([o["box"][1] for o in own + lg] + [lines[0]]) - 0.6 * sp
    need_bot = max([o["box"][3] for o in own + lg] + [lines[4]]) + 0.6 * sp
    top = min(top, need_top)
    bot = max(bot, need_bot)
    top, bot = min(top, lines[0] - 3 * sp), max(bot, lines[4] + 3 * sp)
    w = bx1 - bx0
    side = min(max(w, 6 * sp), 0.4 * (ext[1] - ext[0]))
    cw, ch = (bx1 - bx0) + 2 * side, bot - top
    if cw < 2.2 * ch:
        side += (2.2 * ch - cw) / 2
        cw = 2.2 * ch
    if cw > 2.7 * ch:
        extra = (cw / 2.7 - ch) / 2
        top, bot, ch = top - extra, bot + extra, cw / 2.7
    cx = (bx0 + bx1) / 2
    X0, X1, Y0, Y1 = int(cx - cw / 2), int(cx + cw / 2), int(top), int(bot)
    canvas = Image.new("RGB", (X1 - X0, Y1 - Y0), (255, 255, 255))
    sx0, sy0, sx1, sy1 = max(0, X0), max(0, Y0), min(im.width, X1), min(im.height, Y1)
    canvas.paste(im.crop((sx0, sy0, sx1, sy1)), (sx0 - X0, sy0 - Y0))
    s = nout / canvas.width
    crop = canvas.resize((nout, int(round(canvas.height * s))), Image.LANCZOS)
    ImageDraw.Draw(crop).rectangle([round((bx0 - X0) * s), round((by0 - Y0) * s), round((bx1 - X0) * s), round((by1 - Y0) * s)], outline=ORANGE, width=2)
    return crop, dict(box_page_px=[round(bx0, 1), round(by0, 1), round(bx1, 1), round(by1, 1)], crop_origin=[X0, Y0], scale=round(s, 4),
                      crop_h_staff_spaces=round((bot - top) / sp, 1), barline_snapped=[s0, s1], cell_box_raw=cell, staff_lines=lines, staff_space=round(sp, 2))


def sheet(tiles, path, cols=2, W=1250):
    fit = [t.resize((int(t.width * min(1.0, W / t.width)), int(t.height * min(1.0, W / t.width))), Image.LANCZOS) if t.width > W else t for t in tiles]
    rows = (len(fit) + cols - 1) // cols
    rh = [max(t.height for t in fit[r * cols:(r + 1) * cols]) for r in range(rows)]
    sh = Image.new("RGB", (cols * (W + 12) + 12, sum(h + 34 for h in rh) + 12), (255, 255, 255))
    d = ImageDraw.Draw(sh)
    y = 12
    for r in range(rows):
        for c in range(cols):
            i = r * cols + c
            if i >= len(fit):
                continue
            x = 12 + c * (W + 12)
            d.text((x, y + 4), "%d" % (i + 1), fill=(0, 0, 0))
            sh.paste(fit[i], (x, y + 22))
        y += rh[r] + 34
    sh.save(path)


def main() -> None:
    ap = argparse.ArgumentParser()
    for n in ("lit", "lit-record", "bra", "bra-record", "ranking", "out"):
        ap.add_argument("--" + n, required=True)
    ap.add_argument("--seed", type=int, default=2311005)
    ap.add_argument("--only", help="comma list of 'b' / 'c': redraw only those sheets")
    a = ap.parse_args()
    rank = json.load(open(a.ranking))
    cls = {(r["plate"], r["page"], r["system"], r["staff"], r["cell"]): r for r in rank["bars"]}
    old = {(k["plate"], k["page"], k["system"], k["staff"], k["cell"]) for k in json.load(open("out/print/2.311-redbars-key.json"))}
    rng = random.Random(a.seed)
    chosen, facts = [], {}
    for plate, fp, rp in (("litolff", a.lit, a.lit_record), ("brahms", a.bra, a.bra_record)):
        f = json.load(open(fp))
        facts[plate] = (f, rp)
        pages = set(SAMPLE["plates"][plate]["pages"])
        pool = [b for b in red_run(f, pages) if not (plate == "brahms" and b["page"] == 0)
                and (plate, b["page"], b["system"], b["staff"], b["cell"]) not in old]
        pool.sort(key=lambda b: (b["page"], b["system"], b["staff"], b["cell"]))
        print(plate, "pool", len(pool))
        chosen += [(plate, len(pool), b) for b in rng.sample(pool, 12)]
    wanted = {}
    for plate, _, b in chosen:
        wanted.setdefault(plate, set()).add("staff/%d/%d/%d" % (b["page"], b["system"], b["staff"]))
        wanted[plate].add("cell/%d/%d/%d/%d" % (b["page"], b["system"], b["staff"], b["cell"]))
    geo = {p: staff_geometry(facts[p][1], wanted[p]) for p in wanted}
    meters = {p: meters_by_part(facts[p][0]["xml"]) for p in facts}
    lit, bra = [c for c in chosen if c[0] == "litolff"], [c for c in chosen if c[0] == "brahms"]
    sheets = {"b": lit[:6] + bra[:6], "c": lit[6:] + bra[6:]}
    only = set(a.only.split(",")) if a.only else set(sheets)
    for name, items in sheets.items():
        if name not in only:
            continue
        out = Path(a.out + "-" + name)
        out.mkdir(parents=True, exist_ok=True)
        tiles, key = [], []
        for n, (plate, npool, b) in enumerate(items, 1):
            f = facts[plate][0]
            crop, geom = draw_tile(plate, f, geo[plate], b)
            crop.save(out / ("tile_%02d.png" % n))
            tiles.append(crop)
            r = cls[(plate, b["page"], b["system"], b["staff"], b["cell"])]
            key.append(dict(tile=n, plate=plate, page=b["page"], system=b["system"], staff=b["staff"], cell=b["cell"], part=b["part"], measure=b["measure"],
                            meter_in_force_xml=meters[plate].get((b["part"], str(b["measure"]))), want_quarters=b.get("want_quarters"),
                            counted_quarters=b.get("counted_quarters"), red_kind=b["kind"], also_in=b.get("also", []),
                            classifier_row=r["row"], classifier_reason=r["reason"], classifier_detail=r["detail"],
                            old_first_cause=b["cause"], old_first_cause_reason=b["why"], pool=dict(drawn_from=npool), **geom, **bar_marks(f, b)))
        sheet(tiles, out / "sheet.png")
        (out / "README.md").write_text(
            "# 2.311 red bars, drawn at random (sheet %s)\n\nTwelve pieces of the printed page, one staff each. ONE thin orange box = one bar. "
            "Nothing else is drawn.\n\n**Question, for every tile:** What is printed in the boxed bar? (rests, notes with their values, or empty; anything "
            "you cannot read.)\n\nAnswer by tile number.\n" % name)
        Path(a.out + "-" + name + "-key.json").write_text(json.dumps(key, indent=1, default=str))
        print("sheet", name, len(tiles), [round(t.height) for t in tiles])


if __name__ == "__main__":
    main()
