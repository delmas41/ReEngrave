"""2.300 BLIND TILES for Sean: one whole BAR on one staff per tile; nothing of ours drawn but a thin orange box around the bar.

  PYTHONPATH=. python3 benchmarks/one-chord-one-event-2026-11/tiles.py CMP_litolff.json CMP_brahms.json OFF_litolff.json OFF_brahms.json OUTDIR

Question (README + sheet header, not on a tile): "What is in this bar, in order? Which notes are played together as one chord?"

SELECTION RULE (seeded, stated): random.Random(2300). Pools from the OFF-vs-ON comparison (`compare.py`): A = bars that STOPPED being red; B = bars
that BECAME red or partial (all of them, listed even if none); C = bars holding a chord whose written value changed (not already in A or B).
Order: round-robin over the plates, A first (at most 7), then ALL of B (at most 4), then C, then more A, until 12 tiles. Then shuffled (seed 2300)
so the order tells nothing.

THE BOX: the bar from barline to barline (the cell's page box), tall enough for the staff, two spaces above and below, and every head or rest
either arm wrote in the bar (nothing cut), kept off the neighbouring staves (halfway to the next staff's lines). The caption line above the tile is text:
page, system, staff, bar and the meter in force, which is the one printed on the plate's OPENING page (2/4 Litolff, 6/8 Brahms; read off page 1 / page 0 of
each plate by eye on a render: every system of both plates prints it; no meter change is on the sampled pages in our reading).
"""
import json
import os
import pathlib
import random
import sys

os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from tools.omr.staged import conservation as C  # noqa: E402
from tools.omr.staged import lane_report as LR  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402

ORANGE = (255, 140, 0)
METER = {"litolff": "2/4", "brahms": "6/8"}


def font(n):
    for p in ("/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf"):
        try:
            return ImageFont.truetype(p, n)
        except OSError:
            continue
    return ImageFont.load_default()


def cell_info(plate, pages):
    """GATHER rows only (no stages): cell page boxes, staff lines per staff, every glyph's page box."""
    from tools.omr.staged import export as E
    rows = C.load_pages(plate, pages, C.DEFAULT_TAG)
    log, _ = RR.rebuild_gather(rows)
    rec = log.to_json()
    cells, staves, glyphs = {}, {}, {}
    for o in rec["observations"]:
        q, s = o["quantity"], o["subject"]
        if q == "cell_box":
            p = s.split("/")
            cells[tuple(int(x) for x in p[1:5])] = o["value"]
        elif q == Q.STAFF_LINES:
            p = s.split("/")
            staves[tuple(int(x) for x in p[1:4])] = o["value"]
        elif q == Q.GLYPH_BOX:
            b = (o.get("detail") or {}).get("bbox_page_px")
            if b and len(b) == 4:
                glyphs[s] = [float(v) for v in b]
    return cells, staves, glyphs


_PG = {}


def page_img(plate, page):
    k = (plate, page)
    if k not in _PG:
        _PG.clear()
        _PG[k] = Image.fromarray(render_page(str(LR.LIB / LR.PLATES[plate]["pdf"]), page, dpi=600).rgb).convert("RGB")
    return _PG[k]


def draw_tile(plate, key, info, off_bar, on_bar):
    cells, staves, glyphs = info
    u = LR.PLATES[plate]["unit"]
    p, sy, st, ce = key
    x0, _y0, x1, _y1 = cells[key]
    ys = staves[(p, sy, st)]
    top, bot = min(ys), max(ys)
    y_a, y_b = top - 2.2 * u, bot + 2.2 * u
    gl = []
    for bar in (off_bar, on_bar):
        for e in bar["events"]:
            for h in e["heads"]:
                if h.get("glyph") in glyphs:
                    gl.append(glyphs[h["glyph"]])
            if e.get("rest") in glyphs:
                gl.append(glyphs[e["rest"]])
    for g in gl:
        y_a, y_b = min(y_a, g[1] - 0.3 * u), max(y_b, g[3] + 0.3 * u)
        x0, x1 = min(x0, g[0] - 0.3 * u), max(x1, g[2] + 0.3 * u)
    # keep off the neighbouring staves: halfway to the next staff's lines (any staff on this page/system overlapping in x is a neighbour)
    for k2, ys2 in staves.items():
        if k2[:2] != (p, sy) or k2[2] == st:
            continue
        t2, b2 = min(ys2), max(ys2)
        if t2 > bot:
            y_b = min(y_b, (bot + t2) / 2.0)
        elif b2 < top:
            y_a = max(y_a, (b2 + top) / 2.0)
    im = page_img(plate, p)
    pad = 1.0 * u
    crop = im.crop((int(x0 - pad), int(y_a - pad), int(x1 + pad), int(y_b + pad))).copy()
    d = ImageDraw.Draw(crop)
    w = max(2, int(u / 10))
    d.rectangle([int(x0 - (x0 - pad)), int(y_a - (y_a - pad)), int(x1 - (x0 - pad)), int(y_b - (y_a - pad))], outline=ORANGE, width=w)
    W = 900
    sc = W / crop.width
    crop = crop.resize((W, max(1, int(crop.height * sc))), Image.LANCZOS)
    cap = "%s  page %d  system %d  staff %d  bar %d     meter %s" % (plate.capitalize(), p, sy, st, ce, METER[plate])
    f = font(26)
    t = Image.new("RGB", (W, crop.height + 40), (255, 255, 255))
    ImageDraw.Draw(t).text((6, 6), cap, fill=(0, 0, 0), font=f)
    t.paste(crop, (0, 40))
    return t


def main():
    cl, cb, ol, ob, out = sys.argv[1:6]
    out = pathlib.Path(out)
    (out / "tiles").mkdir(parents=True, exist_ok=True)
    cmps = {"litolff": json.load(open(cl)), "brahms": json.load(open(cb))}
    offs = {"litolff": {tuple(b["key"]): b for b in json.load(open(ol))["bars"]},
            "brahms": {tuple(b["key"]): b for b in json.load(open(ob))["bars"]}}
    ons = {}
    for plate in cmps:
        ons[plate] = {tuple(b["key"]): b for b in json.load(open(cmps[plate]["_on_path"]))["bars"]}
    rng = random.Random(2300)
    pool = {"A": [], "B": [], "C": []}
    seen = set()
    for plate, c in cmps.items():
        for k, *_ in c["stopped_being_red"]:
            pool["A"].append((plate, tuple(k), "stopped_red"))
            seen.add((plate, tuple(k)))
        for k, *_ in c["became_red"] + c["became_partial"]:
            pool["B"].append((plate, tuple(k), "became_red_or_partial"))
            seen.add((plate, tuple(k)))
        for x in c["values_changed"]:
            if (plate, tuple(x["key"])) not in seen:
                pool["C"].append((plate, tuple(x["key"]), "value_changed"))
                seen.add((plate, tuple(x["key"])))
    for v in pool.values():
        rng.shuffle(v)

    def rr(items, n):
        out_, per = [], {"litolff": [i for i in items if i[0] == "litolff"], "brahms": [i for i in items if i[0] == "brahms"]}
        while len(out_) < n and (per["litolff"] or per["brahms"]):
            for pl in ("litolff", "brahms"):
                if per[pl] and len(out_) < n:
                    out_.append(per[pl].pop(0))
        return out_

    picks = rr(pool["A"], 7)
    picks += rr(pool["B"], 4)
    left = [i for i in pool["A"] if i not in picks]
    picks += rr(pool["C"], 12 - len(picks))
    picks += rr(left, 12 - len(picks))
    picks = picks[:12]
    rng.shuffle(picks)
    infos = {}
    for plate in cmps:
        infos[plate] = cell_info(plate, cmps[plate]["pages"])
    ims, key = [], []
    for i, (plate, k, cat) in enumerate(picks, 1):
        t = draw_tile(plate, k, infos[plate], offs[plate][k], ons[plate][k])
        name = "tile_%02d.png" % i
        t.save(out / "tiles" / name)
        ims.append(t)

        def ev(bar):
            return [[e["kind"], e["beats"], [(h["pitch"], h["type"]) for h in e["heads"]]] for e in bar["events"]]
        key.append({"tile": i, "file": name, "plate": plate, "page": k[0], "system": k[1], "staff": k[2], "cell": k[3], "category": cat,
                    "meter_printed": METER[plate], "off_events": ev(offs[plate][k]), "on_events": ev(ons[plate][k]),
                    "off_red": offs[plate][k]["red"], "on_red": ons[plate][k]["red"]})
    json.dump(key, open(out / "key.json", "w"), indent=1)
    cols = 2
    W = max(t.width for t in ims)
    rows = (len(ims) + cols - 1) // cols
    big = font(72)
    rh = [max(t.height for t in ims[r * cols:(r + 1) * cols]) + 90 for r in range(rows)]
    sh = Image.new("RGB", (cols * (W + 40) + 40, sum(rh) + 140), (255, 255, 255))
    d = ImageDraw.Draw(sh)
    d.text((40, 20), "What is in this bar, in order?  Which notes are played together as one chord?", fill=(0, 0, 0), font=font(40))
    y = 110
    for r in range(rows):
        for c in range(cols):
            idx = r * cols + c
            if idx >= len(ims):
                break
            x = 40 + c * (W + 40)
            d.text((x, y), str(idx + 1), fill=(200, 0, 0), font=big)
            sh.paste(ims[idx], (x, y + 85))
        y += rh[r]
    sh.save(out / "sheet.png")
    (out / "README.md").write_text(
        "# 2.300 tiles\n\nQuestion: What is in this bar, in order? Which notes are played together as one chord?\n\n"
        "Each tile is one bar of one staff, boxed in orange; the caption is text (page, system, staff, bar, the printed meter).\n"
        "key.json (one level up from tiles/) names what each arm wrote; do not open it before answering.\n"
        "Selection rule: see the docstring of benchmarks/one-chord-one-event-2026-11/tiles.py (seed 2300).\n")
    print("tiles", len(ims), {c: sum(1 for k in key if k['category'] == c) for c in ('stopped_red', 'became_red_or_partial', 'value_changed')})


main()
