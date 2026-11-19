"""ROADMAP 2.321 small test -- crops for OUR look (stem directions) and BLIND tiles for Sean (research doc §7 questions 1 and 3).

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/voice-line-of-time-2026-11/cuts.py DIR LOOK_DIR TILE_DIR KEY.json

LOOK (rule 7, our look, not truth): up to 20 columns where two different decided stems at one place were READ pointing the same way, drawn with
random.Random(2321) from the list sorted by place; one thin orange box round both events' heads; numbered sheet. Key in LOOK_DIR/look-key.json.

TILES (blind; one staff; nothing drawn but one thin orange box the size of the bar; the bar and its neighbours on that staff, cut from the page raster):
  Q3 -- a bar with a split (an up stem and a down stem at one place), after which only up-stem notes follow and no rest at all is printed after it:
        4 drawn with random.Random(2321003) from the pool sorted by place.
  Q1 -- a bar with a split after which single-stem notes follow, no "a 2" read in the bar: 4 drawn with random.Random(2321001) from the pool minus
        the Q3 picks. Bars already cut for 2.314-voice-questions are left out.
"""
import json
import random
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from checksheet import page_image

ORANGE = (255, 140, 0)
A2 = re.compile(r"\b(a|zu)\s*2\b", re.I)


def load(D):
    out = []
    for plate in ("litolff", "brahms"):
        p = D / ("%s.json" % plate)
        if p.exists():
            out += json.load(open(p))["rows"]
    return out


def ubox(boxes):
    boxes = [b for b in boxes if b]
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)] if boxes else None


def ev_boxes(e):
    if e["kind"] == "rest":
        return [e.get("page_box")]
    return [h.get("page_box") for h in e.get("heads") or ()]


def staff_geo(r):
    sp = r["spacing"] or 20.0
    top = r["top_line"]
    if top is None and r["cell_box"]:
        top = r["cell_box"][1]
    return top, top + 4 * sp, sp


def cut(r, box, x0, x1, extra_v=None, width=1100):
    im = page_image(r["plate"], r["page"])
    top, bot, sp = staff_geo(r)
    y0, y1 = top - 4.5 * sp, bot + 4.5 * sp
    if extra_v:
        y0, y1 = min(y0, extra_v[0] - 1.0 * sp), max(y1, extra_v[1] + 1.0 * sp)
    X0, Y0, X1, Y1 = int(x0), int(y0), int(x1), int(y1)
    canvas = Image.new("RGB", (X1 - X0, Y1 - Y0), (255, 255, 255))
    sx0, sy0, sx1, sy1 = max(0, X0), max(0, Y0), min(im.width, X1), min(im.height, Y1)
    canvas.paste(im.crop((sx0, sy0, sx1, sy1)), (sx0 - X0, sy0 - Y0))
    s = width / canvas.width
    crop = canvas.resize((width, int(round(canvas.height * s))), Image.LANCZOS)
    ImageDraw.Draw(crop).rectangle([round((box[0] - X0) * s), round((box[1] - Y0) * s), round((box[2] - X0) * s), round((box[3] - Y0) * s)],
                                   outline=ORANGE, width=2)
    return crop, dict(crop_origin=[X0, Y0], scale=round(s, 4), box_page_px=[round(v, 1) for v in box])


def sheet(tiles, out, labels=None, cols=2):
    W = max(t.width for t in tiles)
    rows = (len(tiles) + cols - 1) // cols
    rh = [max(t.height for t in tiles[k * cols:(k + 1) * cols]) for k in range(rows)]
    sh = Image.new("RGB", (cols * (W + 12) + 12, sum(h + 30 for h in rh) + 12), (255, 255, 255))
    d = ImageDraw.Draw(sh)
    y = 12
    for k in range(rows):
        for c in range(cols):
            i = k * cols + c
            if i < len(tiles):
                x = 12 + c * (W + 12)
                d.text((x, y + 4), labels[i] if labels else str(i + 1), fill=(0, 0, 0))
                sh.paste(tiles[i], (x, y + 22))
        y += rh[k] + 30
    sh.save(out)


def place(r):
    return (r["plate"], r["page"], r["system"], r["staff"], r["cell"])


def tol_of(r):
    ws = [h["w"] for e in r["events"] for h in e.get("heads") or () if h.get("w")]
    return sum(ws) / len(ws) if ws else 30.0


def dirs(e):
    return {h.get("dir_read") or h.get("dir") for h in e.get("heads") or ()}


def split_shape(r):
    """(x of the last split, events after it) where a split is an up stem and a down stem at one place; else None."""
    ev, tol = r["events"], tol_of(r)
    xs = []
    for c in r["stem_pair_columns"]:
        a, b = set(c["read_a"]), set(c["read_b"])
        if {frozenset(a), frozenset(b)} == {frozenset({"up"}), frozenset({"down"})}:
            xs.append(max(ev[c["i"]]["x"], ev[c["j"]]["x"]))
    for i, j in r.get("divisi_idx") or ():
        xs.append(max(ev[i]["x"], ev[j]["x"]))
    if not xs:
        return None
    sx = max(xs)
    after = [e for e in ev if e["x"] > sx + tol]
    return sx, after


def single_stems(r, after):
    tol = tol_of(r)
    ch = [e for e in after if e["kind"] == "chord"]
    return [e for e in ch if not any(o is not e and abs(o["x"] - e["x"]) <= tol for o in ch)] if ch else []


def main():
    D, LOOK, TILES, KEY = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
    PRIOR_KEY = Path(sys.argv[5]) if len(sys.argv) > 5 else None
    rows = load(D)
    for r in rows:
        r.setdefault("plate", "?")
    # ---- LOOK: same-way columns
    sw = []
    for r in rows:
        for c in r["stem_pair_columns"]:
            a, b = set(c["read_a"]), set(c["read_b"])
            if len(a) == 1 and a == b and "None" not in a:
                sw.append((r, c))
    sw.sort(key=lambda rc: (place(rc[0]), rc[1]["i"], rc[1]["j"]))
    pick = random.Random(2321).sample(sw, min(20, len(sw)))
    LOOK.mkdir(parents=True, exist_ok=True)
    crops, lk = [], []
    for n, (r, c) in enumerate(pick, 1):
        ea, eb = r["events"][c["i"]], r["events"][c["j"]]
        box = ubox(ev_boxes(ea) + ev_boxes(eb))
        if box is None:
            continue
        _, _, sp = staff_geo(r)
        cx = (box[0] + box[2]) / 2
        crop, geo = cut(r, [box[0] - 0.2 * sp, box[1] - 0.2 * sp, box[2] + 0.2 * sp, box[3] + 0.2 * sp], cx - 9 * sp, cx + 9 * sp, (box[1], box[3]), width=700)
        crop.save(LOOK / ("look_%02d.png" % n))
        crops.append(crop)
        lk.append(dict(n=n, place=place(r), way_read=c["read_a"][0], decided=[c["dec_a"], c["dec_b"]], verdict=r["verdict"],
                       heads=[[h["glyph"] for h in ea["heads"]], [h["glyph"] for h in eb["heads"]]], **geo))
    if crops:
        sheet(crops, LOOK / "look_sheet.png", ["%d %s p%d s%d st%d c%d" % ((k["n"],) + tuple(k["place"])) for k in lk], cols=4)
    (LOOK / "look-key.json").write_text(json.dumps(dict(population=len(sw), drawn=len(lk), seed=2321, items=lk), indent=1))
    # ---- TILES
    prior = set()
    if PRIOR_KEY and PRIOR_KEY.exists():
        for k in json.load(open(PRIOR_KEY)):
            prior.add((k["plate"], k["page"], k["system"], k["staff"], k["cell"]))
    q1, q3 = [], []
    for r in sorted(rows, key=place):
        if place(r) in prior or not r["cell_box"]:
            continue
        sh = split_shape(r)
        if not sh:
            continue
        _sx, after = sh
        singles = single_stems(r, after)
        if not singles:
            continue
        if any(A2.search(str(t)) for _x, _k, t in r["directions"]):
            continue
        q1.append(r)
        chords = [e for e in after if e["kind"] == "chord"]
        if (not any(e["kind"] == "rest" for e in after) and len(singles) == len(chords)
                and all(dirs(e) == {"up"} for e in chords)):
            q3.append(r)
    p3 = random.Random(2321003).sample(q3, min(4, len(q3)))
    rest1 = [r for r in q1 if not any(r is x for x in p3)]
    p1 = random.Random(2321001).sample(rest1, min(4, len(rest1)))
    TILES.mkdir(parents=True, exist_ok=True)
    tiles, key = [], []
    for q, picks in ((1, p1), (3, p3)):
        for r in picks:
            cb = r["cell_box"]
            w = cb[2] - cb[0]
            x0 = (r["prev_box"] or [cb[0] - 0.8 * w])[0]
            x1 = (r["next_box"] or [0, 0, cb[2] + 0.8 * w])[2]
            top, bot, sp = staff_geo(r)
            heads = ubox([b for e in r["events"] for b in ev_boxes(e)])
            v = (max(top - 4 * sp, min(top, heads[1])) if heads else top, min(bot + 4 * sp, max(bot, heads[3])) if heads else bot)
            box = [cb[0], v[0] - 1.0 * sp, cb[2], v[1] + 1.0 * sp]
            crop, geo = cut(r, box, x0 - 0.3 * sp, x1 + 0.3 * sp, v)
            tiles.append(crop)
            key.append(dict(tile=len(tiles), question=q, plate=r["plate"], page=r["page"], system=r["system"], staff=r["staff"], cell=r["cell"],
                            staff_name_read=r["name"], code_verdict=r["verdict"], written_red=r["red"], n_streams=r["n_streams"], **geo))
    for n, t in enumerate(tiles, 1):
        t.save(TILES / ("tile_%02d.png" % n))
    if tiles:
        sheet(tiles, TILES / "sheet.png")
    (TILES / "README.md").write_text(
        "# 2.321 -- two players on one staff: 8 bars, one thin orange box each (the bar)\n\n"
        "Tiles 1-4: the bar goes from split stems (one up, one down) back to single stems, with no \"a 2\" printed. "
        "After the split, are BOTH players playing the single-stem notes, or only ONE (which)?\n\n"
        "Tiles 5-8: after the split, only the upper part's notes continue and no rest is printed for the lower part. "
        "Is the lower player silent for the rest of the bar? Is that normal in this edition?\n\n"
        "Say \"cannot tell\" if so. Answer by tile number.\n")
    KEY.write_text(json.dumps(dict(seed_q1=2321001, seed_q3=2321003, pool_q1=len(q1), pool_q3=len(q3), tiles=key), indent=1))
    print("look: %d same-way columns, %d cut; tiles: Q1 pool %d, Q3 pool %d, cut %d" % (len(sw), len(lk), len(q1), len(q3), len(tiles)))


if __name__ == "__main__":
    main()
