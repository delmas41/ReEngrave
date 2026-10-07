"""lane-arc-not-a-line: tiles for Sean + working sheets.  Each tile = the arc box's WHOLE STAFF in its bar, the arc candidate in ORANGE,
the staff line(s) it coincides with in MAGENTA (drawn on the page's own ink rows, re-measured locally), the verdict in WORDS.
Every drawn line is checked against the page's pixel rows and the worst offset printed on the tile.

  python3 arc_not_a_line_sheet.py <out.png> <cols> <tile_w> <tag:subject[:note]> ...      tag = brahms | litolff
"""
from __future__ import annotations
import json, pickle, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from frame import render_page_matching_gather
from tools.library.score_library import library_root

ED = library_root() / "editions"
PDF = {"brahms": ED / "brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
       "litolff": ED / "beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"}
PKL = {"brahms": "/private/tmp/claude-501/arc/brh.pkl", "litolff": "/private/tmp/claude-501/arc/lit.pkl"}
FONT = "/System/Library/Fonts/Helvetica.ttc"
ORANGE, MAGENTA = (255, 120, 0), (220, 0, 200)
_page, _data, _rows = {}, {}, {}


def font(n):
    return ImageFont.truetype(FONT, n)


def gray(tag, page):
    if (tag, page) not in _page:
        _page[(tag, page)] = cv2.cvtColor(np.asarray(render_page_matching_gather(PDF[tag], page, 600).rgb), cv2.COLOR_RGB2GRAY)
    return _page[(tag, page)]


def data(tag):
    if tag not in _data:
        d = pickle.load(open(PKL[tag], "rb"))
        D = dict(arc={}, lines={}, sp={}, name={}, kind={}, cell={})
        for o in d["obs"]:
            q, s = o["quantity"], o["subject"]
            if q == "arc_box":
                D["arc"][s] = o
            elif q == "staff_lines":
                D["lines"][s] = [float(v) for v in o["value"]]
            elif q == "staff_spacing":
                D["sp"][s] = float(o["value"])
        for v in d["verdicts"]:
            if v["quantity"] == "instrument" and v["outcome"] == "decided" and v.get("value"):
                D["name"][v["subject"]] = v["value"]["name"] if isinstance(v["value"], dict) else str(v["value"])
        _data[tag] = D
        _rows[tag] = json.load(open(HERE / f"out/arc_ink_{tag}.json"))["rows"]
    return _data[tag], _rows[tag]


def wrap(text, f, width, dr):
    out, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if dr.textlength(t, font=f) <= width:
            cur = t
        else:
            out.append(cur); cur = w
    out.append(cur)
    return out


def tile(tag, arc, note, tile_w, n):
    D, rows = data(tag)
    o = D["arc"][arc]
    b = o["detail"]["bbox_page_px"]
    _, page, sysi, st = arc.split("/")[:4]
    page = int(page)
    staff = f"staff/{page}/{sysi}/{st}"
    sp = D["sp"][staff]
    G = gray(tag, page)
    ly = D["lines"][staff]
    x0, x1 = int(b[0] - 2 * sp), int(b[2] + 2 * sp)
    y0, y1 = int(min(ly[0], b[1]) - 2.5 * sp), int(max(ly[-1], b[3]) + 2.5 * sp)
    x0, y0 = max(0, x0), max(0, y0)
    crop = cv2.cvtColor(G[y0:y1, x0:x1], cv2.COLOR_GRAY2BGR)
    sc = min(1.0, tile_w / crop.shape[1])
    big = cv2.resize(crop, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
    im = Image.new("RGB", (tile_w, big.shape[0] + 150), "white")
    im.paste(Image.fromarray(cv2.cvtColor(big, cv2.COLOR_BGR2RGB)), (0, 0))
    dr = ImageDraw.Draw(im)
    fx = lambda x: (x - x0) * sc
    fy = lambda y: (y - y0) * sc
    # staff lines inside the box, snapped to page ink rows locally (columns of the box), residual printed
    resid, drawn = [], 0
    all_ys = [y for k, v in D['lines'].items() if k.startswith(f'staff/{page}/') for y in v]
    for y in all_ys:
        if b[1] - 0.15 * sp <= y <= b[3] + 0.15 * sp:
            xs0, xs1 = int(b[0]), int(b[2])
            rws = [r for r in range(int(y) - 6, int(y) + 7) if (G[r, xs0:xs1] < 128).mean() >= 0.5]
            if rws:
                r = min(rws, key=lambda r: abs(r - y)); resid.append(r - y)
                dr.line([(fx(b[0]), fy(r + 0.5)), (fx(b[2]), fy(r + 0.5))], fill=MAGENTA, width=3); drawn += 1
            else:
                resid.append(None)
    dr.rectangle([fx(b[0]), fy(b[1]), fx(b[2]), fy(b[3])], outline=ORANGE, width=3)
    r = rows.get(arc)
    f = font(13)
    wsp = (b[2] - b[0]) / sp
    hsp = (b[3] - b[1]) / sp
    txt = (f"{n}. {tag} page {page} system {int(sysi) + 1}, {D['name'].get('staff/%d/%d/%s' % (page, int(sysi), st)) or 'unnamed staff'} "
           f"(staff {int(st) + 1}).  The detector called this a {o['value']} (score {o['score']:.2f}); the box is {wsp:.1f} spaces wide, {hsp:.1f} tall.")
    if r:
        txt += (f"  With every staff line taken out, {r['coverage'] * 100:.0f}% of its columns still hold curved ink; "
                f"{r['lines_in_box']} staff line(s) (any staff) run through it.")
    if note:
        txt += "  " + note
    y = big.shape[0] + 3
    for ln in wrap(txt, f, tile_w - 8, dr):
        dr.text((4, y), ln, fill=(0, 0, 0), font=f); y += 16
    ok = [abs(v) for v in resid if v is not None]
    dr.text((4, y + 1), f"orange = arc candidate; magenta = the staff line it coincides with ({drawn} drawn on ink rows, worst offset "
            f"{(max(ok) if ok else 0):.1f}px, {sum(v is None for v in resid)} with no ink to check)", fill=(70, 70, 70), font=font(10))
    return im


def main(out, cols, tile_w, *specs):
    if len(specs) == 1 and specs[0].endswith('.json'):
        specs = json.load(open(specs[0]))
    ims = []
    for i, s in enumerate(specs, 1):
        parts = s.split(":", 2)
        ims.append(tile(parts[0], parts[1], parts[2] if len(parts) > 2 else "", int(tile_w), i))
    cols = int(cols)
    rows_ = [ims[i:i + cols] for i in range(0, len(ims), cols)]
    W = int(tile_w) * cols + 8 * (cols - 1)
    H = sum(max(t.size[1] for t in r) for r in rows_) + 8 * (len(rows_) - 1)
    sheet = Image.new("RGB", (W, H), "white")
    y = 0
    for r in rows_:
        for j, t in enumerate(r):
            sheet.paste(t, (j * (int(tile_w) + 8), y))
        y += max(t.size[1] for t in r) + 8
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print("saved", out, sheet.size)


if __name__ == "__main__":
    main(*sys.argv[1:4], *sys.argv[4:])
