"""ROADMAP 2.311 -- 12 RED BARS AT RANDOM (6 per plate) as blind tiles for Sean, and a key of what our record held.

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/note-loss-funnel-2026-11/redbars_tiles.py \
        --lit LIT.facts.json --lit-record LIT.record.json --bra BRA.facts.json --bra-record BRA.record.json \
        --out out/print/2.311-redbars --key out/print/2.311-redbars-key.json

Population: every red-marked bar of the exported file on the frozen sample's count pages (`redbars.red_bars`: does not add up,
unread/empty, held, partial red gap; the same 309 Litolff / 276 Brahms the 2.311 count used), Brahms page 0 left out (already judged).
Drawn with random.Random(2311002) from the list sorted by (page, system, staff, cell): 6 Litolff, then 6 Brahms. Not by cause.
Tile: the page as rendered for the record (600 dpi), that ONE staff (5.5 staff spaces above and below its lines, half a bar either
side), ONE thin orange box = the bar's cell (its x range) on its own staff (2.5 spaces above and below the lines); nothing else drawn.
The key (what the record held, the meter in force from the exported MusicXML, the record's own first cause) is written OUTSIDE.
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import xml.etree.ElementTree as ET

import numpy as np
from pathlib import Path

from PIL import Image, ImageDraw

from checksheet import page_image
from redbars import run as red_run
from tools.omr.staged.record_io import load_record

ORANGE = (255, 140, 0)
SAMPLE = json.load(open("benchmarks/lane-report/sample.json"))


def staff_geometry(rec_path: str, wanted: set) -> dict:
    """staff lines, spacing and the bar's cell box, read from the saved record (reads only)."""
    r = load_record(rec_path)
    obs = r.get("record", r)["observations"]
    out = collections.defaultdict(dict)
    pages = {int(w.split("/")[1]) for w in wanted}
    ps = collections.defaultdict(dict)
    for o in obs:
        q, s = o.get("quantity"), o.get("subject", "")
        if q in ("staff_lines", "staff_extent") and s.startswith("staff/") and int(s.split("/")[1]) in pages:
            ps[s]["lines" if q == "staff_lines" else "extent"] = json.loads(o["value"]) if isinstance(o["value"], str) else o["value"]
        if q == "staff_lines" and s in wanted:
            out[s]["lines"] = json.loads(o["value"]) if isinstance(o["value"], str) else o["value"]
        elif q == "staff_extent" and s in wanted:
            out[s]["extent"] = json.loads(o["value"]) if isinstance(o["value"], str) else o["value"]
        elif q == "cell_box" and s in wanted:
            out[s]["cell"] = json.loads(o["value"]) if isinstance(o["value"], str) else o["value"]
    out["_page_staves"] = dict(ps)
    return out


def meters_by_part(xml: str) -> dict:
    """{(part, measure number): 'beats/beat-type' in force at the START of that bar} from the exported MusicXML."""
    root = ET.fromstring(xml)
    out = {}
    for part in root.findall("part"):
        cur = None
        for m in part.findall("measure"):
            t = m.find("attributes/time")
            if t is not None and t.find("beats") is not None:
                cur = "%s/%s" % (t.find("beats").text, t.find("beat-type").text)
            out[(part.get("id"), m.get("number"))] = cur
    return out


def f_glyphs(f: dict, pre: str):
    return [(k, g) for k, g in f["glyphs"].items() if k.startswith(pre)]


def bar_marks(f: dict, b: dict) -> dict:
    pre = "glyph/%d/%d/%d/%d/" % (b["page"], b["system"], b["staff"], b["cell"])
    written = {h["rg"]: h for h in f["written"] if h.get("rg", "").startswith(pre)}
    marks = []
    kinds = collections.Counter()
    for k, g in f["glyphs"].items():
        if not k.startswith(pre):
            continue
        if not (g["head"] or g["rest"]):
            kinds[g["cls"]] += 1
            continue
        v = g.get("v") or {}
        d = v.get("duration") or {}
        m = dict(glyph=k, cls=g["cls"], kind="rest" if g["rest"] else "note head", box=[round(x, 1) for x in g["box"]], fate=g["fate"],
                 duration=dict(outcome=d.get("outcome"), reason=d.get("reason"), value=d.get("value")))
        for q in ("notehead_is_not_a_notehead", "rest_is_not_a_rest", "glyph_owner", "pitch"):
            if q in v:
                m[q] = dict(outcome=v[q].get("outcome"), value=v[q].get("value"), reason=v[q].get("reason"))
        h = written.get(k)
        if h is not None:
            m["written"] = dict(type=h["type"], dots=len((h.get("sub") or {}).get("dot") or []), pitch=h["pitch"], measure=h["measure"])
            m["status"] = "GUESSED (written blue)" if h["blue"] else "READ (written plain)"
        elif g["fate"] in ("written", "written_relocated"):
            m["status"] = "fate says %s but no written row carries this glyph key (merged into a chord/other row)" % g["fate"]
        else:
            m["status"] = "not written: %s" % g["fate"]
        marks.append(m)
    # written marks keyed to this bar whose glyph key is another cell's (relocated) are listed too
    return dict(marks=marks, other_ink_in_cell=dict(kinds))


def main() -> None:
    ap = argparse.ArgumentParser()
    for n in ("lit", "lit-record", "bra", "bra-record", "out", "key"):
        ap.add_argument("--" + n, required=True)
    ap.add_argument("--seed", type=int, default=2311002)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    chosen, facts = [], {}
    for plate, fp, rp in (("litolff", a.lit, a.lit_record), ("brahms", a.bra, a.bra_record)):
        f = json.load(open(fp))
        facts[plate] = (f, rp)
        pages = set(SAMPLE["plates"][plate]["pages"])
        allbars = red_run(f, pages)
        pool = [b for b in allbars if not (plate == "brahms" and b["page"] == 0)]
        pool.sort(key=lambda b: (b["page"], b["system"], b["staff"], b["cell"]))
        print(plate, "all red bars", len(allbars), "pool", len(pool))
        chosen += [(plate, len(allbars), len(pool), b) for b in rng.sample(pool, 6)]
    wanted = {}
    for plate, _, _, b in chosen:
        wanted.setdefault(plate, set()).add("staff/%d/%d/%d" % (b["page"], b["system"], b["staff"]))
        wanted[plate].add("cell/%d/%d/%d/%d" % (b["page"], b["system"], b["staff"], b["cell"]))
    geo = {p: staff_geometry(facts[p][1], wanted[p]) for p in wanted}
    meters = {p: meters_by_part(facts[p][0]["xml"]) for p in facts}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tiles, key = [], []
    for n, (plate, nall, npool, b) in enumerate(chosen, 1):
        g = geo[plate]
        st = g["staff/%d/%d/%d" % (b["page"], b["system"], b["staff"])]
        cell = g["cell/%d/%d/%d/%d" % (b["page"], b["system"], b["staff"], b["cell"])]["cell"]
        lines = st["lines"]
        sp = (lines[4] - lines[0]) / 4.0
        im = page_image(plate, b["page"])
        W_OUT = 1250
        ext = st["extent"]
        # (c) box: barline to barline (snap the cell edge to the dark barline column on THIS staff), staff lines +- 1 space
        gray = np.asarray(im.convert("L"))
        ya, yb = int(lines[0]), int(lines[4])

        def snap(x):
            xs = range(max(0, int(x - 1.2 * sp)), min(gray.shape[1], int(x + 1.2 * sp)))
            fr = {xx: float((gray[ya:yb, xx] < 128).mean()) for xx in xs}
            best = max(fr.values())
            if best < 0.9:
                return x, False
            cols = [xx for xx in xs if fr[xx] >= 0.9 * best and fr[xx] > 0.8]
            # the contiguous dark run nearest the cell edge
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
        # (a) height: this staff's own ink whole, never past the midpoint to the neighbour unless its own head/ledger stack needs it
        stv = [v for k, v in g["_page_staves"].items() if "lines" in v and "extent" in v and v["lines"] != lines
               and v["extent"][0] < bx1 and v["extent"][1] > bx0]
        above = [v["lines"][4] for v in stv if v["lines"][4] < lines[0]]
        below = [v["lines"][0] for v in stv if v["lines"][0] > lines[4]]
        up_nb, dn_nb = (max(above) if above else None), (min(below) if below else None)
        top = (lines[0] + up_nb) / 2 if up_nb is not None else lines[0] - 8 * sp
        bot = (lines[4] + dn_nb) / 2 if dn_nb is not None else lines[4] + 8 * sp
        pre = "glyph/%d/%d/%d/%d/" % (b["page"], b["system"], b["staff"], b["cell"])
        own = [gl for k, gl in f_glyphs(facts[plate][0], pre) if (gl["head"] or gl["rest"]) and not (gl["fate"] or "").startswith(
            ("owned_by_another", "not_a_notehead:belongs_to_a_nearer"))]
        lg = [gl for k, gl in f_glyphs(facts[plate][0], pre) if gl["cls"] == "ledgerLine"
              and any(o["box"][0] - sp <= (gl["box"][0] + gl["box"][2]) / 2 <= o["box"][2] + sp for o in own)]
        need_top = min([o["box"][1] for o in own + lg] + [lines[0]]) - 0.6 * sp
        need_bot = max([o["box"][3] for o in own + lg] + [lines[4]]) + 0.6 * sp
        capt = (up_nb + 0.5 * sp) if up_nb is not None else need_top
        capb = (dn_nb - 0.5 * sp) if dn_nb is not None else need_bot
        top = min(top, need_top)      # its own heads/ledger stack whole, even when they stand over the neighbour's staff
        bot = max(bot, need_bot)
        top, bot = min(top, lines[0] - 3 * sp), max(bot, lines[4] + 3 * sp)
        # (b) width: the bar plus a full neighbouring bar (or 40% of the system) each side, whichever is smaller
        w = bx1 - bx0
        side = min(max(w, 6 * sp), 0.4 * (ext[1] - ext[0]))
        cw, ch = (bx1 - bx0) + 2 * side, bot - top
        if cw < 2.2 * ch:                       # never a sliver: widen to a 2.2 : 1 window
            side += (2.2 * ch - cw) / 2
            cw = 2.2 * ch
        if cw > 2.7 * ch:                       # a wide bar: more height (more of the page above and below), so it is not a strip
            extra = (cw / 2.7 - ch) / 2
            top, bot, ch = top - extra, bot + extra, cw / 2.7
        cx = (bx0 + bx1) / 2
        X0, X1, Y0, Y1 = int(cx - cw / 2), int(cx + cw / 2), int(top), int(bot)
        canvas = Image.new("RGB", (X1 - X0, Y1 - Y0), (255, 255, 255))
        sx0, sy0, sx1, sy1 = max(0, X0), max(0, Y0), min(im.width, X1), min(im.height, Y1)
        canvas.paste(im.crop((sx0, sy0, sx1, sy1)), (sx0 - X0, sy0 - Y0))
        x0, y0 = X0, Y0
        s = W_OUT / canvas.width
        crop = canvas.resize((W_OUT, int(round(canvas.height * s))), Image.LANCZOS)
        ImageDraw.Draw(crop).rectangle([round((bx0 - x0) * s), round((by0 - y0) * s), round((bx1 - x0) * s), round((by1 - y0) * s)],
                                       outline=ORANGE, width=2)
        crop.save(out / ("tile_%02d.png" % n))
        tiles.append(crop)
        f = facts[plate][0]
        mk = bar_marks(f, b)
        key.append(dict(
            tile=n, plate=plate, page=b["page"], system=b["system"], staff=b["staff"], cell=b["cell"], part=b["part"],
            measure=b["measure"], box_page_px=[round(bx0, 1), round(by0, 1), round(bx1, 1), round(by1, 1)],
            crop_origin=[x0, y0], scale=round(s, 4), crop_h_staff_spaces=round((bot - top) / sp, 1), barline_snapped=[s0, s1], cell_box_raw=cell, staff_lines=lines, staff_space=round(sp, 2),
            meter_in_force_xml=meters[plate].get((b["part"], str(b["measure"]))), want_quarters=b.get("want_quarters"),
            red_kind=b["kind"], also_in=b.get("also", []), red_words=b.get("words") or b.get("why"),
            counted_quarters=b.get("counted_quarters"), partial_gap_quarters=b.get("gap_quarters"),
            first_cause=b["cause"], first_cause_reason=b["why"],
            pool=dict(all_red_bars=nall, drawn_from=npool), **mk))
    cols, W = 2, 1250
    fit = []
    for t in tiles:
        k = min(1.0, W / t.width)
        fit.append(t.resize((int(t.width * k), int(t.height * k)), Image.LANCZOS) if k < 1 else t)
    rows = (len(fit) + cols - 1) // cols
    rh = [max(t.height for t in fit[r * cols:(r + 1) * cols]) for r in range(rows)]
    sheet = Image.new("RGB", (cols * (W + 12) + 12, sum(h + 34 for h in rh) + 12), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    y = 12
    for r in range(rows):
        for c in range(cols):
            i = r * cols + c
            if i >= len(fit):
                continue
            x = 12 + c * (W + 12)
            d.text((x, y + 4), "%d" % (i + 1), fill=(0, 0, 0))
            sheet.paste(fit[i], (x, y + 22))
        y += rh[r] + 34
    sheet.save(out / "sheet.png")
    (out / "README.md").write_text(
        "# 2.311 red bars, drawn at random\n\nTwelve pieces of the printed page, one staff each. ONE thin orange box = one bar. "
        "Nothing else is drawn.\n\n**Question, for every tile:** What is printed in the boxed bar? (rests, notes with their "
        "values, or empty; anything you cannot read.)\n\nAnswer by tile number.\n")
    Path(a.key).write_text(json.dumps(key, indent=1, default=str))
    print("tiles", len(tiles))


if __name__ == "__main__":
    main()
