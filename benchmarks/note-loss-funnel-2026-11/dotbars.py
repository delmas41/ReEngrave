"""ROADMAP 2.311 small test, parts 4 and 6 -- red bars short by exactly one dot, and the 12 blind tiles "is the boxed note dotted?".
Reads SAVED facts / extra of the frozen-sample gather (`lit-a`, `bra-a`); nothing is re-gathered.

    PYTHONPATH=RANKING_LIB:.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/note-loss-funnel-2026-11/dotbars.py \
        --lit LIT.facts.json --lit-extra LIT.extra.json --bra BRA.facts.json --bra-extra BRA.extra.json \
        --ranking redbar-ranking.json --out-json dotbars-results.json [--look DIR] [--tiles OUT_DIR --key KEY.json]

RANKING_LIB holds `redbars.py`, `redbar_classify.py` (and `redbar-ranking.json`) from branch origin/lane-2.311-redbar-ranking.

POPULATIONS (Brahms page 0 left out of both: already judged, see dotcount.py):
  BARS    the red bars the ranking filed as `sum_short_dot_*` (a plain written note whose half-value fills the shortfall EXACTLY, with
          dot evidence right of the head); one candidate note per bar (the first of the subset that fills it).
  INK     every plain READ written note (no dot) with a dot-sized ink piece that has NO detector box right of it, on the count pages.
Seeds: 2311101 (the look sample of 20 BARS), 2311102 (6 INK tiles), 2311103 (6 BARS tiles).
Tile: the page as rendered (600 dpi), ONE staff (3.5 spaces above and below (more if the note stands on ledger lines), 28 spaces wide, the note a third from the left), one thin
orange box = the head plus the space to its right where a dot would stand (head left edge to 2.0 spaces beyond its right edge, 0.6 space
above and below). Nothing else drawn. Key (what our file held) is written OUTSIDE the folder.
"""
from __future__ import annotations

import argparse
import collections
import json
import random
from pathlib import Path

from PIL import Image, ImageDraw

import redbar_classify as RC
from checksheet import page_image

SAMPLE = json.load(open("benchmarks/lane-report/sample.json"))
ORANGE = (255, 140, 0)


def bar_of(rg):
    p = rg.split("/")
    return (int(p[1]), int(p[2]), int(p[3]), int(p[4]))


def candidates(ctx, b):
    """the plain written notes (and the subset) whose half-value fills the bar's shortfall -> list of written rows, evidence."""
    key = (b["page"], b["system"], b["staff"], b["cell"])
    sp = ctx.sp(key)
    rows = RC._rows(ctx, b)
    notes = [w for w in rows if w["kind"] == "note"]
    plain = [w for w in notes if not w.get("blue")]
    want, got = b.get("want"), b.get("counted") or []
    short = [c for c in got if c < want - 1e-6]
    need = round(want - (max(short) if len(short) == len(got) else min(short)), 6)
    cands = []
    for w in plain:
        d = RC._dur(w)
        if d is None or (w.get("sub") or {}).get("dot"):
            continue
        ev = RC._near_dot_evidence(ctx, key, w, sp)
        if ev:
            cands.append((w, d / 2.0, ev))
    hit = RC._subset_hits(cands, need)
    return [(h[0], h[2]) for h in hit] if hit else []


def tile_box(w, sp):
    b = w["box"]
    return [b[0], b[1] - 0.6 * sp, b[2] + 2.0 * sp, b[3] + 0.6 * sp]


def crop_for(plate, page, lines, w, sp, width, draw_box=True, wide_sp=28):
    im = page_image(plate, page)
    b = tile_box(w, sp)
    x0 = int(b[0] - wide_sp / 3.0 * sp)
    x1 = int(x0 + wide_sp * sp)
    y0, y1 = min(lines[0] - 3.5 * sp, b[1] - 1.0 * sp), max(lines[4] + 3.5 * sp, b[3] + 1.0 * sp)
    if y1 - y0 < 10.3 * sp:          # never a sliver: at least 450 px tall at the tile width
        mid = (y0 + y1) / 2.0
        y0, y1 = mid - 5.15 * sp, mid + 5.15 * sp
    y0, y1 = int(y0), int(y1)
    x0, x1 = max(0, x0), min(im.width, x1)
    crop = im.crop((x0, y0, x1, y1)).copy()
    if draw_box:
        s = width / crop.width
        crop = crop.resize((width, int(crop.height * s)), Image.LANCZOS)
        ImageDraw.Draw(crop).rectangle([(b[0] - x0) * s, (b[1] - y0) * s, (b[2] - x0) * s, (b[3] - y0) * s], outline=ORANGE, width=3)
    return crop


def main():
    ap = argparse.ArgumentParser()
    for n in ("lit", "lit-extra", "bra", "bra-extra", "ranking", "out-json"):
        ap.add_argument("--" + n, required=True)
    ap.add_argument("--look")
    ap.add_argument("--tiles")
    ap.add_argument("--key")
    a = ap.parse_args()
    rank = json.load(open(a.ranking))["bars"]
    ctxs, facts = {}, {}
    for plate, fp, ep in (("litolff", a.lit, a.lit_extra), ("brahms", a.bra, a.bra_extra)):
        f = json.load(open(fp))
        facts[plate] = f
        ctxs[plate] = RC.Ctx(plate, f, json.load(open(ep)), set(SAMPLE["plates"][plate]["pages"]))
    out = dict(bars={}, ink={})
    # BARS
    bars = [b for b in rank if b["row"].startswith("sum_short_dot") and not (b["plate"] == "brahms" and b["page"] == 0)]
    bars.sort(key=lambda b: (b["plate"], b["page"], b["system"], b["staff"], b["cell"]))
    out["bars"]["n_all_incl_p0"] = sum(1 for b in rank if b["row"].startswith("sum_short_dot"))
    out["bars"]["n_pool"] = len(bars)
    out["bars"]["by_row"] = {"%s/%s" % k: v for k, v in collections.Counter((b["plate"], b["row"]) for b in bars).most_common()}
    for b in bars:
        b["cand"] = candidates(ctxs[b["plate"]], b)
    out["bars"]["no_candidate_recovered"] = sum(1 for b in bars if not b["cand"])
    # INK
    ink = []
    for plate, ctx in ctxs.items():
        for rg, ws in ctx.written.items():
            if not rg:
                continue
            for w in ws:
                if w["kind"] != "note" or w.get("blue") or (w.get("sub") or {}).get("dot") or RC._dur(w) is None:
                    continue
                key = bar_of(rg)
                if plate == "brahms" and key[0] == 0:
                    continue
                if key[0] not in ctx.pages:
                    continue
                sp = ctx.sp(key)
                if sp and RC._near_dot_evidence(ctx, key, w, sp) == "ink_never_boxed":
                    ink.append(dict(plate=plate, page=key[0], key=key, w=w))
    ink.sort(key=lambda r: (r["plate"], r["key"], r["w"]["box"][0]))
    out["ink"]["n_plain_read_notes_with_unboxed_dot_ink"] = len(ink)
    out["ink"]["by_plate"] = dict(collections.Counter(r["plate"] for r in ink))
    in_bar = {(b["plate"], b["page"], b["system"], b["staff"], b["cell"]) for b in bars}
    out["ink"]["of_which_in_a_dot_short_red_bar"] = sum(1 for r in ink if (r["plate"],) + tuple(r["key"]) in in_bar)
    # the look sample
    rng = random.Random(2311101)
    look = rng.sample(bars, min(20, len(bars)))
    out["bars"]["look_sample"] = [dict(plate=b["plate"], bar=[b["page"], b["system"], b["staff"], b["cell"]], row=b["row"],
                                       cand=[c[0]["rg"] for c in b["cand"]]) for b in look]
    if a.look:
        Path(a.look).mkdir(parents=True, exist_ok=True)
        for n, b in enumerate(look, 1):
            if not b["cand"]:
                continue
            ctx = ctxs[b["plate"]]
            key = (b["page"], b["system"], b["staff"], b["cell"])
            lines = ctx.lines[key[:3]]
            sp = ctx.sp(key)
            c = crop_for(b["plate"], b["page"], lines, b["cand"][0][0], sp, 1000)
            d = ImageDraw.Draw(c)
            d.text((6, 4), "%d %s p%d cell %s %s" % (n, b["plate"], b["page"], key[1:], b["row"]), fill=(200, 0, 0))
            c.save("%s/look_%02d.png" % (a.look, n))
    # the tiles
    if a.tiles:
        r2, r3 = random.Random(2311102), random.Random(2311103)
        barkeys = {(b["plate"], b["page"], b["system"], b["staff"], b["cell"]) for b in bars}
        ink_pool = [r for r in ink if (r["plate"],) + tuple(r["key"]) not in barkeys]
        pick_ink = r2.sample(ink_pool, 6)
        pick_bar = r3.sample([b for b in bars if b["cand"]], 6)
        items = [dict(set="ink", plate=r["plate"], page=r["page"], key=r["key"], w=r["w"], row=None) for r in pick_ink] + \
                [dict(set="bar", plate=b["plate"], page=b["page"], key=(b["page"], b["system"], b["staff"], b["cell"]), w=b["cand"][0][0],
                      row=b["row"]) for b in pick_bar]
        order = list(range(12))
        random.Random(2311104).shuffle(order)       # the two sets are mixed, so the order says nothing
        W = 1250
        Path(a.tiles).mkdir(parents=True, exist_ok=True)
        keyrows, ims = [], []
        for n, i in enumerate(order, 1):
            it = items[i]
            ctx = ctxs[it["plate"]]
            lines = ctx.lines[tuple(it["key"][:3])]
            sp = ctx.sp(it["key"])
            c = crop_for(it["plate"], it["page"], lines, it["w"], sp, W)
            assert c.height >= 450, (n, c.height)
            c.save("%s/tile_%02d.png" % (a.tiles, n))
            ims.append(c)
            keyrows.append(dict(tile=n, set=it["set"], plate=it["plate"], page=it["page"], bar=list(it["key"]), glyph=it["w"]["rg"],
                                written=dict(type=it["w"]["type"], dots=0, blue=False, pitch=it["w"].get("pitch")), red_bar_row=it["row"],
                                note="we wrote this note plain and READ; the question is whether it is dotted"))
        hmax = max(c.height for c in ims)
        sheet = Image.new("RGB", (2 * W + 30, ((len(ims) + 1) // 2) * (hmax + 30) + 10), (255, 255, 255))
        d = ImageDraw.Draw(sheet)
        for n, c in enumerate(ims):
            x, y = 10 + (n % 2) * (W + 10), 10 + (n // 2) * (hmax + 30)
            sheet.paste(c, (x, y))
            d.text((x, y + c.height + 4), "tile %d" % (n + 1), fill=(0, 0, 0))
        sheet.save("%s/sheet.png" % a.tiles)
        json.dump(dict(seeds=dict(look=2311101, ink=2311102, bar=2311103, order=2311104), tiles=keyrows), open(a.key, "w"), indent=1, default=str)
        out["tiles"] = [dict(k) for k in keyrows]
    json.dump(out, open(a.out_json, "w"), indent=1, default=str)
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("look_sample",)} for k, v in out.items() if k != "tiles"}, indent=1, default=str))


if __name__ == "__main__":
    main()
