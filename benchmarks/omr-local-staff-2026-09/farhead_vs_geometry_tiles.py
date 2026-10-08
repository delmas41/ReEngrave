"""lane-farhead-vs-geometry (2026-10-07), step 2: ONE tile per sampled disagreement between the note-first reader and plain
geometry, each its OWN image `out/print/farhead_vs_geometry/tile_NN.png` (one column, 1400 px wide, text >= 18 px), and
`questions.txt` with ONE plain question per tile.  GATHER+ADJUDICATE verdicts only; READ ONLY (extract + replay + names).

  python3 farhead_vs_geometry_tiles.py <dir with <doc>-20261007-day.json, rep_<doc>.json, names_<doc>.json> [--seed 20261008]

Sample (seeded): from the decided Litolff far heads the two readings DIFFER on and exactly one fails Sean's through-or-edge
check on the grid rows (`farhead_vs_geometry.py`): 3 where the READER fails on the grid but passes on its own measured rows
(the grid's extrapolated-ledger artefact), 3 where the reader fails on both, 6 where GEOMETRY fails on the grid and the
reader passes.  Heads whose owner verdict is another staff, or that the not-a-note verdict calls a non-note, are left out
(a different lane's question).
Drawing: RED = the line the READER's answer names, BLUE = the line GEOMETRY's answer names, each 1 px across the whole crop;
both are placed on the page's MEASURED ledger rows (`offbox_check.Rows(lines, rungs)`) so neither is drawn off the print by
a one-staff-space extrapolation.  ORANGE corner brackets = the note.  CONTROL: each drawn line is re-measured against the
ink rows beside the head and the offset printed (a line drawn where no line is printed shows it).
"""
from __future__ import annotations
import collections, json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import offbox_check as C
import overnight_1004_report as R
import truth_set_2_44c as ts
from frame import render_page_matching_gather

OUT = HERE.parents[1] / "out/print/farhead_vs_geometry"
TAG = "20261007-day"
W = 1400
RED, BLUE, ORANGE, PURPLE = (230, 0, 0), (0, 70, 255), (255, 140, 0), (170, 0, 200)
FONT = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 21)
FONT_B = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24, index=1)
ORD = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th", 6: "6th"}


def named_line(p):
    return p if p % 2 == 0 else (p + 1 if p < 0 else p - 1)


def words(p, colour):
    """one answer in plain words, tied to its colour."""
    if p % 2 == 0:
        return f"ON the {colour} line"
    return f"in the space just beyond the {colour} line, further from the staff"


def ledger_words(p):
    if p < 0:
        n = (-p) // 2 if p % 2 == 0 else (-p - 1) // 2
        side = "above"
    else:
        n = (p - 8) // 2 if p % 2 == 0 else (p - 9) // 2
        side = "below"
    if p % 2 == 0:
        return f"the {ORD.get(n, str(n) + 'th')} ledger line {side} the staff" if n > 0 else "a staff line"
    return f"the space {side} the {ORD.get(n, str(n) + 'th')} ledger line" if n > 0 else f"the space just {side} the staff"


def pool(d, doc):
    data = json.loads((Path(d) / f"{doc}-{TAG}.json").read_text())
    rep = json.loads((Path(d) / f"rep_{doc}.json").read_text())["heads"]
    names = json.loads((Path(d) / f"names_{doc}.json").read_text())
    out = []
    for s, g in data["glyphs"].items():
        if not R.is_far(g) or "box" not in g or "geo" not in g:
            continue
        np_ = g.get("np") or {}
        m = rep.get(s)
        if np_.get("outcome") != "decided" or not m or not m.get("repro") or not m.get("lines") or m.get("line_y") is None:
            continue
        filing = "staff/" + "/".join(s.split("/")[1:4])
        own = g.get("own") or {}
        if own.get("outcome") == "decided" and own.get("value") not in (None, filing):
            continue
        nan = g.get("nan") or {}
        if nan.get("outcome") == "decided" and nan.get("reason") != "notehead":
            continue                      # the not-a-note verdict calls it something else: another lane's question
        p, q = int(round(float(np_["value"]))), R.geo_pos(g)
        if p == q:
            continue
        grid = C.Rows(m["lines"])
        own_rows = C.Rows(m["lines"], m["rungs"])
        rg, gg = C.passes(p, g["box"], grid), C.passes(q, g["box"], grid)
        if rg == gg:
            continue
        rown = C.passes(p, g["box"], own_rows)
        grp = ("reader_fails_grid_passes_own_rows" if rown else "reader_fails_both_rows") if not rg else "geometry_fails_grid"
        w = g["box"][2] - g["box"][0]
        out.append(dict(subject=s, doc=doc, page=R.page_of(s), box=g["box"], reader=p, geo=q, grp=grp, m=m, filing=filing,
                        name=names.get(filing), width=w))
    return out


def ink_offset(gray, y, box, sp):
    """px from row y to the nearest inked row-run (>= 60 % of the flank columns dark) within 0.8 sp; None if none."""
    thr = min(int(np.percentile(gray[int(y - 2 * sp):int(y + 2 * sp), int(box[0] - 3 * sp):int(box[2] + 3 * sp)], 25) + 40), 140)
    best = None
    for x0, x1 in ((int(box[0] - 0.8 * sp), int(box[0] - 0.05 * sp)), (int(box[2] + 0.05 * sp), int(box[2] + 0.8 * sp))):
        x0 = max(0, x0)
        rows = [r for r in range(int(y - 0.8 * sp), int(y + 0.8 * sp) + 1) if 0 <= r < gray.shape[0] and (gray[r, x0:x1] <= thr).mean() >= 0.5]
        runs, cur = [], []
        for r in rows:
            if cur and r == cur[-1] + 1:
                cur.append(r)
            else:
                if cur:
                    runs.append(cur)
                cur = [r]
        if cur:
            runs.append(cur)
        for c in runs:
            o = abs(float(np.mean(c)) - y)
            best = o if best is None or o < best else best
    return best


def text_lines(draw, x, y, lines, fill=(0, 0, 0), font=FONT, step=30):
    for t in lines:
        draw.text((x, y), t, fill=fill, font=font)
        y += step
    return y


def tile(r, gray, no):
    box, m = r["box"], r["m"]
    own_rows = C.Rows(m["lines"], m["rungs"])
    sp = own_rows.sp
    ry = float(m["line_y"])
    gy = own_rows.y(named_line(r["geo"]))
    # crop: 30 staff spaces wide centred on the head, from above the higher drawn line to below the lower, with the staff in view
    cx = (box[0] + box[2]) / 2.0
    top, bot = own_rows.top, own_rows.bot
    ys = [ry, gy, box[1], box[3], top, bot]
    x0, x1 = int(cx - 15 * sp), int(cx + 15 * sp)
    y0, y1 = int(min(ys) - 1.6 * sp), int(max(ys) + 1.6 * sp)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(gray.shape[1], x1), min(gray.shape[0], y1)
    sc = W / float(x1 - x0)
    crop = cv2.cvtColor(gray[y0:y1, x0:x1], cv2.COLOR_GRAY2BGR)
    im = cv2.resize(crop, (W, max(1, int(round((y1 - y0) * sc)))), interpolation=cv2.INTER_NEAREST)

    def yy(y):
        return int(round((y - y0) * sc))
    checks = []
    same = abs(ry - gy) < 3.0
    for col, y, lab in (((PURPLE, ry, "PURPLE (both)"),) if same else ((BLUE, gy, "BLUE (geometry)"), (RED, ry, "RED (reader)"))):
        cv2.line(im, (0, yy(y)), (W - 1, yy(y)), (col[2], col[1], col[0]), 1)
        o = ink_offset(gray, y, box, sp)
        checks.append((no, lab, round(float(y), 1), None if o is None else round(o, 1)))
    bx0, by0, bx1, by1 = [(box[0] - x0) * sc, (box[1] - y0) * sc, (box[2] - x0) * sc, (box[3] - y0) * sc]
    L = 22
    oc = (ORANGE[2], ORANGE[1], ORANGE[0])
    for (px, py, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1), (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
        cv2.line(im, (int(px), int(py)), (int(px + dx * L), int(py)), oc, 3)
        cv2.line(im, (int(px), int(py)), (int(px), int(py + dy * L)), oc, 3)
    # staff top/bottom ticks at the left margin so the staff is named by what it is
    for y in (top, bot):
        cv2.line(im, (0, yy(y)), (14, yy(y)), (0, 160, 0), 3)
    k = r["filing"].split("/")
    staff_no = int(k[3]) + 1
    sys_no = int(k[2]) + 1
    nm = r["name"] or "(no name read)"
    head = [f"Tile {no}.  {'Litolff' if r['doc'].startswith('beet') else 'Brahms'}, PDF page {r['page']}, system {sys_no}, staff {staff_no} from the top: {nm}"]
    if same:
        q_lines = [f"RED (reader) says the note is {words(r['reader'], 'PURPLE')}  ({ledger_words(r['reader'])}).",
                   f"BLUE (geometry) says it is {words(r['geo'], 'PURPLE')}  ({ledger_words(r['geo'])})."]
        q = "Is the note ON the purple line, or in the space just beyond the purple line (further from the staff)?"
    else:
        q_lines = [f"RED (reader) says the note is {words(r['reader'], 'RED')}  ({ledger_words(r['reader'])}).",
                   f"BLUE (geometry) says it is {words(r['geo'], 'BLUE')}  ({ledger_words(r['geo'])})."]
        q = f"Is the note {words(r['reader'], 'red')}, or {words(r['geo'], 'blue')}?"
    foot_h = 30 * 3 + 20
    head_h = 40
    canvas = Image.new("RGB", (W, head_h + im.shape[0] + foot_h), (255, 255, 255))
    d = ImageDraw.Draw(canvas)
    d.text((10, 6), head[0][:110], fill=(0, 0, 0), font=FONT_B)
    canvas.paste(Image.fromarray(cv2.cvtColor(im, cv2.COLOR_BGR2RGB)), (0, head_h))
    yb = head_h + im.shape[0] + 8
    d.text((10, yb), q_lines[0], fill=RED, font=FONT)
    d.text((10, yb + 30), q_lines[1], fill=BLUE, font=FONT)
    if same:
        d.text((560, yb + 60), "(both answers name the same line, drawn PURPLE)", fill=PURPLE, font=FONT)
    d.text((10, yb + 60), "ORANGE corners = the note.  Green ticks at the left = the staff's top and bottom lines.", fill=(90, 90, 90), font=FONT)
    return canvas, q, checks


def main(d, seed):
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    P = [r for r in pool(d, "beethoven5-litolff") if r["width"] >= 8]
    g = collections.defaultdict(list)
    for r in P:
        g[r["grp"]].append(r)
    print({k: len(v) for k, v in g.items()})
    picks = []
    for grp, n in (("reader_fails_grid_passes_own_rows", 3), ("reader_fails_both_rows", 3), ("geometry_fails_grid", 6)):
        picks += rng.sample(g[grp], min(n, len(g[grp])))
    rng.shuffle(picks)
    grays = {}
    qs, allchecks, info = [], [], []
    for i, r in enumerate(picks, 1):
        key = (r["doc"], r["page"])
        if key not in grays:
            grays[key] = cv2.cvtColor(render_page_matching_gather(ts.DOCS[r["doc"]]["pdf"], r["page"], 600).rgb, cv2.COLOR_RGB2GRAY)
        img, q, ch = tile(r, grays[key], i)
        img.save(OUT / f"tile_{i:02d}.png")
        qs.append(f"{i}. {q}")
        allchecks += ch
        info.append(dict(n=i, subject=r["subject"], doc=r["doc"], group=r["grp"], reader=r["reader"], geometry=r["geo"], staff=r["name"]))
        print(i, r["subject"], r["grp"], "reader", r["reader"], "geo", r["geo"], img.size, flush=True)
    (OUT / "questions.txt").write_text("\n".join(qs) + "\n")
    (OUT / "tiles.json").write_text(json.dumps(info, indent=1))
    bad = [c for c in allchecks if c[3] is not None and c[3] > 2.0]
    none = [c for c in allchecks if c[3] is None]
    print("drawn lines", len(allchecks), "| within 2 px of ink", len(allchecks) - len(bad) - len(none), "| off ink >2 px", bad, "| no ink beside the head", none)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], int(a[a.index("--seed") + 1]) if "--seed" in a else 20261008)
