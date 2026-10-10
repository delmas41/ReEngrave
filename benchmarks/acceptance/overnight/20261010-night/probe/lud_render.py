#!/usr/bin/env python3
"""lud_render: one system, twice, side by side, on the print.

LEFT  = last night's reading (20261009-all): every note that went kept ->
        narrowed boxed in blue with the value it was DECIDED to be.
RIGHT = tonight's reading (20261010-night): the same notes boxed in orange with
        the candidates it is now undecided between.
Green boxes (both panels) are the opposite change, narrowed -> kept.

Coordinates are the GATHER boxes (`bbox_page_px`) of TONIGHT's record; GATHER
boxes are the same in both runs (the diff matched every note 1:1, checked in
UNDECIDED.md). The page is `preprocessing.render_page(pdf, page, dpi)` -- the
same deskewed raster the gather read. Everything drawn comes from the small
JSON lud_extract.py wrote; no record is loaded here.

Bar numbers are the EXPORTER'S bar numbers (offset(page/system) + cell + 1,
checked against the exporter's own held-bar list in lud_bars.py), NOT printed
numbers; the system's margin reading is shown only where it agreed.
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lud_bars  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402

FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
BLUE = (20, 90, 230)
ORANGE = (235, 90, 0)
GREEN = (0, 150, 70)
GREY = (110, 110, 110)
BEATS = re.compile(r"\(([\d.]+) beats?\)")
NAMES = {6: "d.whole", 4: "whole", 3: "d.half", 2: "half", 1.5: "d.qtr", 1: "qtr", 0.75: "d.8th",
         0.5: "8th", 0.375: "d.16th", 0.25: "16th", 0.1875: "d.32nd", 0.125: "32nd",
         0.09375: "d.64th", 0.0625: "64th", 0.046875: "d.128th", 0.03125: "128th"}


def name(b):
    try:
        f = float(b)
    except ValueError:
        return b
    return NAMES.get(round(f, 6), f"{f:g}")


def label_of(s):
    """why-string -> short names. 'length still open: A (x beats) | B (y beats) -- r' or 'A (x beats)'."""
    m = re.match(r"^length still open: (.*?) -- .+$", s)
    body = m.group(1) if m else s
    return "|".join(name(BEATS.search(c).group(1)) if BEATS.search(c) else c for c in body.split(" | "))


def font(px):
    return ImageFont.truetype(FONT, max(12, int(px)))


def dashed(d, box, color, width, dash=10):
    x0, y0, x1, y1 = box
    for (ax, ay, bx, by) in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
        L = max(abs(bx - ax), abs(by - ay))
        n = int(L // dash)
        for i in range(0, n, 2):
            t0, t1 = i / max(n, 1), min((i + 1) / max(n, 1), 1)
            d.line([(ax + (bx - ax) * t0, ay + (by - ay) * t0), (ax + (bx - ax) * t1, ay + (by - ay) * t1)],
                   fill=color, width=width)


class Doc:
    def __init__(self, doc, extract, scale):
        self.doc = doc
        self.ex = json.load(open(extract))
        self.dpi = self.ex["prov"]["dpi"]
        self.pdf = self.ex["prov"]["pdf"]
        self.scale = scale
        self.diff = json.load(open(lud_bars.COMPARE / f"{doc}-first-two-stages.json"))
        self.off, _nb, self.chk, _ = lud_bars.numbering(doc)
        self._pages = {}
        # changed notes by system
        self.changes = collections.defaultdict(list)
        for p in self.diff["changed_pairs"]:
            if p["family"] != "note" or tuple(p["status"]) not in (("kept", "narrowed"), ("narrowed", "kept")):
                continue
            pg, sy, st, ce, g = lud_bars.parse(p["b"])
            box = self.ex["boxes"].get(p["b"])
            if not box:
                continue
            self.changes[(pg, sy)].append({
                "key": p["b"], "staff": st, "cell": ce, "kind": "k2n" if p["status"][0] == "kept" else "n2k",
                "box": box[1:5], "last": label_of(p["why"][0][0]), "now": label_of(p["why"][1][0]),
            })

    def page(self, p):
        if p not in self._pages:
            self._pages = {p: render_page(self.pdf, p, dpi=self.dpi).rgb}
        return self._pages[p]

    def staves(self, p, s):
        out = {}
        for k, v in self.ex["staves"].items():
            m = re.match(r"^staff/(\d+)/(\d+)/(\d+)$", k)
            if m and int(m.group(1)) == p and int(m.group(2)) == s:
                out[int(m.group(3))] = v
        return out

    def cells(self, p, s, staff):
        out = {}
        for k, v in self.ex["cells"].items():
            m = re.match(r"^cell/(\d+)/(\d+)/(\d+)/(\d+)$", k)
            if m and (int(m.group(1)), int(m.group(2)), int(m.group(3))) == (p, s, staff):
                out[int(m.group(4))] = v
        return out


def draw_panel(img, region, items, side, doc, p, s, staves, cells0, sp, scale):
    """img: PIL crop already scaled. region = (x0,y0) page-px origin of the crop."""
    ox, oy = region
    d = ImageDraw.Draw(img)
    lw = max(2, int(round(sp * scale * 0.11)))
    f_lab = font(sp * scale * 0.95)
    f_bar = font(sp * scale * 1.0)
    f_st = font(sp * scale * 0.8)
    placed = []

    def to(x, y):
        return ((x - ox) * scale, (y - oy) * scale)

    # bar numbers + ticks above the top staff of the system
    top = min(v["ys"][0] for v in staves.values())
    for ce, box in sorted(cells0.items()):
        x, y = to(box[0], top - 1.6 * sp)
        if -50 < x < img.width:
            bar = doc.off.get((p, s), -1) + ce + 1
            d.line([(x, y), (x, y + 1.4 * sp * scale)], fill=GREY, width=max(2, lw // 2))
            d.text((x + 3, y - 1.1 * sp * scale), str(bar), fill=GREY, font=f_bar)
    # staff index in the left margin
    for st, v in sorted(staves.items()):
        x, y = to(v["ext"][0] - 3.8 * sp if v["ext"] else ox, v["ys"][2] - 0.4 * sp)
        if 0 <= x < img.width:
            d.text((x, y), f"st{st}", fill=GREY, font=f_st)
    # the changed notes
    for it in sorted(items, key=lambda i: (i["box"][1], i["box"][0])):
        x0, y0, x1, y1 = it["box"]
        a = to(x0, y0)
        b = to(x1, y1)
        if b[0] < 0 or a[0] > img.width or b[1] < 0 or a[1] > img.height:
            continue
        if it["kind"] == "k2n":
            col = BLUE if side == "L" else ORANGE
            text = it["last"] if side == "L" else it["now"]
        else:
            col = GREEN
            text = it["last"] if side == "L" else it["now"]
        d.rectangle([a, b], outline=col, width=lw)
        # label to the right of the box, nudged down if it collides
        tw = d.textlength(text, font=f_lab)
        lh = sp * scale * 1.05
        lx, ly = b[0] + lw + 2, a[1] - lh * 0.1
        for _ in range(6):
            r = (lx, ly, lx + tw, ly + lh)
            if not any(not (r[2] < q[0] or r[0] > q[2] or r[3] < q[1] or r[1] > q[3]) for q in placed):
                break
            ly += lh * 0.9
        placed.append((lx, ly, lx + tw, ly + lh))
        d.text((lx, ly), text, fill=col, font=f_lab, stroke_width=max(2, lw), stroke_fill=(255, 255, 255))
    return img


def compose(doc, p, s, region, out, title_extra="", only_cells=None):
    staves = doc.staves(p, s)
    items = doc.changes.get((p, s), [])
    sp = float(np.median([(v["ys"][-1] - v["ys"][0]) / 4 for v in staves.values()]))
    page = doc.page(p)
    H, W = page.shape[:2]
    x0, y0, x1, y1 = [int(round(v)) for v in region]
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    crop = Image.fromarray(page[y0:y1, x0:x1])
    sc = doc.scale
    if sc != 1:
        crop = crop.resize((int(crop.width * sc), int(crop.height * sc)), Image.BICUBIC)
    staff0 = min(staves)
    cells0 = doc.cells(p, s, staff0)
    L = draw_panel(crop.copy(), (x0, y0), items, "L", doc, p, s, staves, cells0, sp, sc)
    R = draw_panel(crop.copy(), (x0, y0), items, "R", doc, p, s, staves, cells0, sp, sc)
    gap = int(sp * sc * 2)
    eb = lambda c: doc.off.get((p, s), -1) + c + 1
    k2n = sum(1 for i in items if i["kind"] == "k2n")
    n2k = sum(1 for i in items if i["kind"] == "n2k")
    c = doc.chk.get((p, s), {})
    W2 = L.width * 2 + gap
    unit = max(15.0, min(sp * sc * 1.15, W2 / 75.0))      # body text px, so a narrow zoom still fits
    f_big, f_mid = font(unit * 1.5), font(unit)
    meas = ImageDraw.Draw(Image.new("RGB", (10, 10)))

    def wrap(text, f, maxw):
        out_l, cur = [], ""
        for w in text.split(" "):
            t = (cur + " " + w).strip()
            if meas.textlength(t, font=f) <= maxw or not cur:
                cur = t
            else:
                out_l.append(cur)
                cur = w
        out_l.append(cur)
        return out_l

    cs = sorted(doc.cells(p, s, staff0))
    if not c:
        margin = ""
    elif c.get("state") == "abstained":
        margin = f"No margin bar number was machine-read for this system; the export numbers its first bar {eb(min(doc.cells(p, s, staff0)))}."
    else:
        margin = (f"The system's margin number was machine-read {c.get('printed')}; the export numbers its first bar "
                  f"{c.get('file_number')} ({c.get('state')}).")
    lines = []   # (text, font, colour, swatch colour or None)
    for t in wrap(f"{doc.doc}  page {p}  system {s}  (export bars {eb(cs[0])}-{eb(cs[-1])}) {title_extra}", f_big, W2 - 20):
        lines.append((t, f_big, (0, 0, 0), None))
    for t in wrap(f"LEFT = LAST NIGHT 20261009-all (main 00473387).  RIGHT = TONIGHT 20261010-night (main 26fdb4d0).  "
                  f"600 dpi page pixels{'' if sc == 1 else f', drawn x{sc:g}'}.  {k2n} notes kept->narrowed"
                  f"{'' if not n2k else f' and {n2k} narrowed->kept'} on this system.  {margin}", f_mid, W2 - 20):
        lines.append((t, f_mid, (0, 0, 0), None))
    for col, txt in ((BLUE, "blue box = the note was DECIDED last night; the value it had is written beside it"),
                     (ORANGE, "orange box = the same note is UNDECIDED tonight; the values it may be are written beside it (a|b = a or b)"),
                     (GREEN, "green box = the opposite change: undecided last night, decided tonight (same box on both sides)"),
                     (GREY, "grey number = the exporter's bar number (not the printed one); stN = staff index; "
                            "8th eighth, d.8th dotted eighth, qtr quarter, 16th sixteenth")):
        for i, t in enumerate(wrap(txt, f_mid, W2 - 20 - unit * 2.2)):
            lines.append((t, f_mid, col, col if i == 0 else None))
    lh = unit * 1.35
    head = int(lh * len(lines) + 12 + unit * 2.0)
    canvas = Image.new("RGB", (W2, L.height + head), (255, 255, 255))
    canvas.paste(L, (0, head))
    canvas.paste(R, (L.width + gap, head))
    d = ImageDraw.Draw(canvas)
    y = 6
    for t, f, col, sw in lines:
        if sw is not None:
            d.rectangle([10, y + unit * 0.15, 10 + unit * 1.4, y + unit * 1.0], outline=sw, width=max(2, int(unit * 0.12)))
        d.text((10 + (unit * 2.0 if col != (0, 0, 0) else 0), y), t, fill=col, font=f)
        y += lh
    d.text((10, head - unit * 1.8), "LAST NIGHT", fill=BLUE, font=f_big)
    d.text((L.width + gap + 10, head - unit * 1.8), "TONIGHT", fill=ORANGE, font=f_big)
    canvas.save(out, optimize=True)
    return canvas.size, k2n, n2k


def system_region(doc, p, s):
    staves = doc.staves(p, s)
    sp = float(np.median([(v["ys"][-1] - v["ys"][0]) / 4 for v in staves.values()]))
    y0 = min(v["ys"][0] for v in staves.values()) - 9 * sp
    y1 = max(v["ys"][-1] for v in staves.values()) + 5 * sp
    exts = [v["ext"] for v in staves.values() if v["ext"]]
    x0 = min(e[0] for e in exts) - 6 * sp
    x1 = max(e[1] for e in exts) + 2 * sp
    return (x0, y0, x1, y1), sp


def zoom_region(doc, p, s):
    items = [i for i in doc.changes.get((p, s), []) if i["kind"] == "k2n"]
    by = collections.Counter(i["cell"] for i in items)
    best = max(by, key=lambda c: (by[c], -c))
    staves = doc.staves(p, s)
    sp = float(np.median([(v["ys"][-1] - v["ys"][0]) / 4 for v in staves.values()]))
    cells = doc.cells(p, s, min(staves))
    x0, x1 = cells[best][0] - 3 * sp, cells[best][2] + 3 * sp
    # the window of up to 4 consecutive staves holding most of that bar's changed notes
    inbar = collections.Counter(i["staff"] for i in items if i["cell"] == best)
    order = sorted(staves)
    win = max((order[j:j + 4] for j in range(len(order))), key=lambda w: sum(inbar[x] for x in w))
    y0 = staves[win[0]]["ys"][0] - 6 * sp
    y1 = staves[win[-1]]["ys"][-1] + 4 * sp
    return (x0, y0, x1, y1), best, sum(inbar[x] for x in win), win


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("doc")
    ap.add_argument("--extract", required=True)
    ap.add_argument("--systems", required=True, help="page/system,page/system,...")
    ap.add_argument("--start-index", type=int, default=1)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--zoom-scale", type=float, default=None)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    Path(a.out_dir).mkdir(parents=True, exist_ok=True)
    idx = a.start_index
    for sysspec in a.systems.split(","):
        p, s = (int(x) for x in sysspec.split("/"))
        doc = Doc(a.doc, a.extract, a.scale)
        reg, sp = system_region(doc, p, s)
        out = Path(a.out_dir) / f"system_{idx:02d}.png"
        size, k2n, n2k = compose(doc, p, s, reg, out)
        print(f"{out}: {a.doc} p{p} s{s}: {size[0]}x{size[1]} px, {k2n} k2n + {n2k} n2k drawn, "
              f"{out.stat().st_size / 1e6:.1f} MB", flush=True)
        zdoc = Doc(a.doc, a.extract, a.zoom_scale or max(a.scale, 2.0 if a.scale == 1 else a.scale))
        zdoc._pages = doc._pages
        zreg, best, nbest, win = zoom_region(zdoc, p, s)
        zout = Path(a.out_dir) / f"system_{idx:02d}_zoom.png"
        size, _, _ = compose(zdoc, p, s, zreg, zout,
                             title_extra=f"ZOOM: bar {zdoc.off[(p, s)] + best + 1}, staves {win[0]}-{win[-1]} "
                                         f"({nbest} of its newly undecided notes in view)")
        print(f"{zout}: zoom bar {zdoc.off[(p, s)] + best + 1} staves {win[0]}-{win[-1]} ({nbest} k2n in view): "
              f"{size[0]}x{size[1]} px, {zout.stat().st_size / 1e6:.1f} MB", flush=True)
        idx += 1


if __name__ == "__main__":
    main()
