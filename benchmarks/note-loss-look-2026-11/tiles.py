"""2.289 crops.  Two products, one cutter:

  look   -- MY crops (not for Sean): 20 per reason, seeded, the dropped box red and its twin (if any) green, a label.
  blind  -- Sean's 12 tiles: ONE staff window (for an 'owned by another staff' case the window holds BOTH staves the head could
            belong to), ONE thin orange box sized to the head, NOTHING else drawn. Key (one level above the tile folder).

    python3 benchmarks/note-loss-look-2026-11/tiles.py look  CAPDIR CLS.json OUTDIR
    python3 benchmarks/note-loss-look-2026-11/tiles.py blind CAPDIR CLS.json OUTDIR   (writes OUTDIR/tiles/ + OUTDIR/key.json)

SELECTION RULE for blind (stated, seeded 289): from CLS.json, per class, pooled over both plates, alternating plates, random.Random(289).sample
 b (barline sliver)   3 : the plates' b rows (head rows of `claimed_by:barline`)
 d (candidate lost)   5 : the d rows (owner copy not written / no twin box)
 c + e                2 : every c row and the group-twin e row, then drawn from by the same seed
 a (CONTROL)          2 : 'twin written on the owner staff' rows -- the answer we predict is 'a notehead, on the staff we gave it'
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
RED = (220, 0, 0)
GREEN = (0, 150, 0)
_CACHE = {}


def page_img(plate, page):
    k = (plate, page)
    if k not in _CACHE:
        _CACHE.clear()
        _CACHE[k] = Image.fromarray(render_page(str(LR.LIB / LR.PLATES[plate]["pdf"]), page, dpi=600).rgb).convert("RGB")
    return _CACHE[k]


def staff_span(staves, page, system, staff):
    v = staves["staff/%d/%d/%d" % (page, system, staff)]["value"]
    return min(v), max(v)


def cut(plate, row, staves, twin_box=None, annotate=False, W=480):
    im = page_img(plate, row["page"])
    u = LR.PLATES[plate]["unit"]
    b = row["box"]
    cx = (b[0] + b[2]) / 2
    keys = [(row["page"], row["system"], row["staff"])]
    if row["reason"] == "owned_by_another_staff":
        keys.append(tuple(int(v) for v in row["owner"].split("/")[1:4]))
    spans = [staff_span(staves, *k) for k in keys]
    top = min(min(s[0] for s in spans), b[1]) - 2.5 * u
    bot = max(max(s[1] for s in spans), b[3]) + 2.5 * u
    x0, x1 = max(0, int(cx - 7 * u)), int(cx + 7 * u)
    y0, y1 = max(0, int(top)), int(bot)
    crop = im.crop((x0, y0, x1, y1)).copy()
    d = ImageDraw.Draw(crop)
    pad = 3
    if annotate:
        if twin_box:
            d.rectangle([twin_box[0] - x0 - pad, twin_box[1] - y0 - pad, twin_box[2] - x0 + pad, twin_box[3] - y0 + pad], outline=GREEN, width=2)
        d.rectangle([b[0] - x0 - pad, b[1] - y0 - pad, b[2] - x0 + pad, b[3] - y0 + pad], outline=RED, width=2)
    else:
        d.rectangle([b[0] - x0 - pad, b[1] - y0 - pad, b[2] - x0 + pad, b[3] - y0 + pad], outline=ORANGE, width=max(2, int(u / 10)))
    return crop.resize((W, int(W * crop.height / crop.width)))


def sheet(tiles, labels, path, cols=2):
    W = tiles[0].width
    rows = (len(tiles) + cols - 1) // cols
    cell_h = [max(t.height for t in tiles[r * cols:(r + 1) * cols]) + 22 for r in range(rows)]
    sh = Image.new("RGB", (cols * (W + 8) + 8, sum(cell_h) + 8), (255, 255, 255))
    d = ImageDraw.Draw(sh)
    y = 8
    for r in range(rows):
        for c in range(cols):
            n = r * cols + c
            if n >= len(tiles):
                break
            x = 8 + c * (W + 8)
            d.text((x, y + 2), labels[n], fill=(0, 0, 0))
            sh.paste(tiles[n], (x, y + 18))
        y += cell_h[r]
    sh.save(path)


def load(capdir, cls):
    data = json.load(open(cls))
    staves = {p: json.load(open(pathlib.Path(capdir, p + ".staves.json"))) for p in data}
    boxes = {p: {r["sub"]: r["box"] for r in json.load(open(pathlib.Path(capdir, p + ".fates.json")))} for p in data}
    return data, staves, boxes


def look(capdir, cls, out):
    data, staves, boxes = load(capdir, cls)
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(289)
    picks = {"owned": [], "barline": []}
    for plate, rows in data.items():
        own = [r for r in rows if r["reason"] == "owned_by_another_staff"]
        bar = [r for r in rows if r["reason"] != "owned_by_another_staff" and r["head"]]
        picks["owned"] += [(plate, r) for r in rng.sample(own, 10)]
        picks["barline"] += [(plate, r) for r in (bar if len(bar) <= 7 else rng.sample(bar, 13 if plate == "brahms" else 7))]
    for name, items in picks.items():
        items = items[:20]
        for s in range(0, len(items), 10):
            tiles, labels = [], []
            for n, (plate, r) in enumerate(items[s:s + 10], s + 1):
                t = r["detail"].get("twin")
                tb = boxes[plate].get(t) if t else None
                tiles.append(cut(plate, r, staves[plate], tb, True, 420))
                labels.append("%d %s p%s s%s st%s c%s [%s]" % (n, plate, r["page"], r["system"], r["staff"], r["cell"], r["cls"]))
            sheet(tiles, labels, out / ("look_%s_%d.png" % (name, s // 10 + 1)))
    print("look sheets in", out)


def cands(capdir, cls, out):
    """MY look at every class c/d/e head row (annotated)."""
    data, staves, boxes = load(capdir, cls)
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    items = [(p, r) for p, rows in data.items() for r in rows if r["head"] and r["cls"][0] in "cde"]
    for s in range(0, len(items), 6):
        tiles, labels = [], []
        for n, (plate, r) in enumerate(items[s:s + 6], s + 1):
            t = r["detail"].get("twin")
            tiles.append(cut(plate, r, staves[plate], boxes[plate].get(t) if t else None, True, 400))
            labels.append("%d %s p%s s%s st%s c%s [%s %s]" % (n, plate, r["page"], r["system"], r["staff"], r["cell"], r["cls"][:12], r["detail"].get("twin_fate", "")))
        sheet(tiles, labels, out / ("cands_%d.png" % (s // 6 + 1)))
    print(len(items), "candidates")


def blind(capdir, cls, out):
    data, staves, boxes = load(capdir, cls)
    out = pathlib.Path(out)
    tdir = out / "tiles"
    tdir.mkdir(parents=True, exist_ok=True)
    for f in tdir.glob("*"):
        f.unlink()
    rng = random.Random(289)
    allrows = [dict(r, plate=p) for p, rows in data.items() for r in rows]
    cls_of = lambda r: r["cls"][0]
    heads = [r for r in allrows if r["head"]]
    pool_b = [r for r in heads if cls_of(r) == "b"]
    pool_d = [r for r in heads if cls_of(r) == "d"]
    pool_ce = [r for r in heads if cls_of(r) in ("c", "e")]
    pool_a = [r for r in heads if cls_of(r) == "a" and r["reason"] == "owned_by_another_staff"]

    def take(pool, n):
        # alternate plates, seeded
        by = {p: [r for r in pool if r["plate"] == p] for p in ("litolff", "brahms")}
        for p in by:
            rng.shuffle(by[p])
        out_rows, i = [], 0
        while len(out_rows) < min(n, len(pool)):
            p = ("brahms", "litolff")[i % 2]
            if by[p]:
                out_rows.append(by[p].pop())
            elif by["litolff" if p == "brahms" else "brahms"]:
                out_rows.append(by["litolff" if p == "brahms" else "brahms"].pop())
            i += 1
        return out_rows
    items = [(r, "b") for r in take(pool_b, 3)] + [(r, "d") for r in take(pool_d, 5)] + \
            [(r, "ce") for r in take(pool_ce, 2)] + [(r, "a-control") for r in take(pool_a, 2)]
    rng.shuffle(items)
    tiles, key = [], []
    for n, (r, role) in enumerate(items, 1):
        im = cut(r["plate"], r, staves[r["plate"]], None, False, 520)
        im.save(tdir / ("tile_%02d.png" % n))
        tiles.append(im)
        own = tuple(int(v) for v in r["owner"].split("/")[1:4]) if r["owner"] else None
        key.append(dict(tile=n, role=role, cls=r["cls"], reason=r["reason"], plate=r["plate"], page=r["page"], system=r["system"],
                        home_staff=r["staff"], owner_staff=(own[2] if own else None), cell=r["cell"], box=r["box"], sub=r["sub"],
                        detail=r["detail"],
                        upper_lower_note="the window holds the HOME staff and (for owned cases) the OWNER staff; the upper of the two is the smaller staff index"))
    sheet(tiles, ["%d" % (i + 1) for i in range(len(tiles))], tdir / "sheet.png", cols=3)
    (tdir / "README.md").write_text(
        "# Tiles for Sean\n\nEach picture is a piece of a scanned score page with ONE thin orange box on it and nothing else drawn. "
        "Some pictures hold two staves (one above the other); some hold one.\n\n"
        "**Question, for every tile:** is the boxed mark a notehead? If yes, which staff is it on (the upper or the lower one in "
        "the picture; in a one-staff picture just say 'yes')? If it is not a notehead, say what it is (barline, stem, flag, text, "
        "accidental piece, nothing).\n\nAnswer by tile number.\n")
    (out / "key.json").write_text(json.dumps(dict(seed=289, rule=__doc__, tiles=key), indent=1, default=str))
    print("blind tiles:", len(key), [(k["tile"], k["role"], k["plate"]) for k in key])


if __name__ == "__main__":
    {"look": look, "blind": blind, "cands": cands}[sys.argv[1]](*sys.argv[2:5])
