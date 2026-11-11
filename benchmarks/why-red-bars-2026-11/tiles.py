"""2.291 BLIND TILES for Sean: one whole BAR on one staff per tile.

  python3 tiles.py CLASSIFIED.json BARS_litolff.json BARS_brahms.json RECORD_litolff.json RECORD_brahms.json OUTDIR

Each tile: the bar with a little of its neighbours, ONE thin orange rectangle around the bar (barline to barline, the staff band), and at the
left a small inset of the START of the same staff (clef / key / meter AS PRINTED there, nothing of ours drawn). Nothing else drawn, no text.
Question (sheet header, not on a tile): what is in this bar, in order -- and anything unusual: two voices, a triplet, a grace note, a pickup?
Key (OUTDIR/../key.json): our family, our reading, want vs counted. sheet.png: numbered montage, 2 columns.

SELECTION RULE (seeded, stated): from the RED bars of the default pages (Litolff 1,2 / Brahms 0,4) in CLASSIFIED.json, group by (family, plate);
walk the groups in a fixed order (families SHORT, VOICES, LONG, TWIN, FALSE; Litolff before Brahms), taking ONE bar from each group with
random.Random(291).choice, round after round, until 12 tiles; a group that runs dry is skipped.
"""
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from PIL import Image, ImageDraw, ImageFont   # noqa: E402

from tools.omr.staged import lane_report as LR   # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402

ORANGE = (255, 140, 0)
_PG = {}


def page_img(plate, page):
    k = (plate, page)
    if k not in _PG:
        _PG.clear()
        _PG[k] = Image.fromarray(render_page(str(LR.LIB / LR.PLATES[plate]["pdf"]), page, dpi=600).rgb).convert("RGB")
    return _PG[k]


def tile(plate, b, extent_left, W=640):
    u = LR.PLATES[plate]["unit"]
    p = b["key"][0]
    im = page_img(plate, p)
    x0, _y0, x1, _y1 = b["cell_box"]
    ys = b["staff_lines"]
    top, bot = min(ys), max(ys)
    vp = 6.0 if plate == "brahms" else 4.0
    y_a, y_b = int(top - vp * u), int(bot + vp * u)
    main = im.crop((int(x0 - 1.2 * u), y_a, int(x1 + 1.2 * u), y_b)).copy()
    d = ImageDraw.Draw(main)
    pad = 0.3 * u
    d.rectangle([x0 - (x0 - 1.2 * u) , int(top - 2.2 * u) - y_a, x1 - (x0 - 1.2 * u), int(bot + 2.2 * u) - y_a], outline=ORANGE, width=max(2, int(u / 8)))
    inset = im.crop((int(extent_left), y_a, int(extent_left + 12 * u), y_b)).copy()
    sc_main = W / main.width
    main = main.resize((W, int(main.height * sc_main)), Image.LANCZOS)
    inset = inset.resize((int(inset.width * sc_main), int(inset.height * sc_main)), Image.LANCZOS)
    t = Image.new("RGB", (inset.width + 12 + main.width, main.height), (255, 255, 255))
    t.paste(inset, (0, 0))
    t.paste(main, (inset.width + 12, 0))
    ImageDraw.Draw(t).line([(inset.width + 5, 0), (inset.width + 5, t.height)], fill=(150, 150, 150), width=1)
    return t


def main():
    cls_f, bl, bb, rl, rb, out = sys.argv[1:7]
    out = pathlib.Path(out)
    (out / "tiles").mkdir(parents=True, exist_ok=True)
    cls = json.load(open(cls_f))
    bars = {"litolff": {tuple(b["key"]): b for b in json.load(open(bl))}, "brahms": {tuple(b["key"]): b for b in json.load(open(bb))}}
    ext = {}
    for plate, rf in (("litolff", rl), ("brahms", rb)):
        r = json.load(open(rf))
        for o in r["observations"]:
            if o["quantity"] == "staff_extent":
                p = o["subject"].split("/")
                ext[(plate,) + tuple(int(x) for x in p[1:4])] = o["value"][0]
    defpages = {"litolff": {1, 2}, "brahms": {0, 4}}
    groups = {}
    for c in cls:
        if c["key"][0] in defpages[c["plate"]]:
            groups.setdefault((c["family"], c["plate"]), []).append(c)
    rng = random.Random(291)
    order = [(f, p) for f in ("SHORT", "VOICES", "LONG", "TWIN", "FALSE") for p in ("litolff", "brahms")]
    picks = []
    pools = {k: list(v) for k, v in groups.items()}
    while len(picks) < 12 and any(pools.get(k) for k in order):
        for k in order:
            if len(picks) >= 12:
                break
            if pools.get(k):
                c = rng.choice(pools[k])
                pools[k].remove(c)
                picks.append(c)
    rng.shuffle(picks)
    key = []
    ims = []
    for i, c in enumerate(picks, 1):
        b = bars[c["plate"]][tuple(c["key"])]
        el = ext[(c["plate"], b["key"][0], b["key"][1], b["key"][2])]
        t = tile(c["plate"], b, el)
        name = "tile_%02d.png" % i
        t.save(out / "tiles" / name)
        ims.append(t)
        ev = ["%s %s%s" % ("rest" if q["kind"] == "rest" else "note", q["beats"], " (blue)" if q["status"] == "GUESSED" else "") for q in b["red_rows"]]
        key.append({"tile": i, "file": name, "plate": c["plate"], "page": b["key"][0], "system": b["key"][1], "staff": b["key"][2], "cell": b["key"][3],
                    "measure": b["measure"], "our_family": c["family"], "meter_in_force_ours": "%s" % (b.get("meter") or {}).get("value", {}),
                    "want_quarters": c["want"], "counted_quarters_per_voice": c["counted"], "our_events_in_order": ev, "why_red": b["why"]})
    json.dump(key, open(out / "key.json", "w"), indent=1, default=str)
    cols = 2
    W = max(t.width for t in ims)
    rows = (len(ims) + cols - 1) // cols
    rh = [max(t.height for t in ims[r * cols:(r + 1) * cols]) + 20 for r in range(rows)]
    sh = Image.new("RGB", (cols * (W + 10) + 10, sum(rh) + 10), (255, 255, 255))
    d = ImageDraw.Draw(sh)
    y = 6
    for r in range(rows):
        for c in range(cols):
            i = r * cols + c
            if i >= len(ims):
                break
            x = 10 + c * (W + 10)
            d.text((x, y), "%d" % (i + 1), fill=(0, 0, 0))
            sh.paste(ims[i], (x, y + 16))
        y += rh[r]
    sh.save(out / "sheet.png")
    print("tiles", len(ims), "->", out)


main()
