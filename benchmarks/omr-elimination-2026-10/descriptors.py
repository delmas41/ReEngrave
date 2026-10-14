"""ROADMAP 2.120 -- the four coarse descriptors of ONE mark, on the PAGE raster. DESIGN ONLY.
Unit = a box + the ink inside it (never a connected component). Staff geometry = the truth page's own
measure cells (product cutter lines, per bar = measured locally). Placed against the NEAREST staff at
the subject's x. (Rebuilt verbatim 2026-10-14 after the /private/tmp wipe.)"""
import fitz
import numpy as np

DARK = 140
IN_PAD_SP = 0.5
NEAR_MAX_SP = 8.0
KEYSLOT_SP = 9.0
HEADER_SP = 14.0
BARHEAD_SP = 5.0
BARTAIL_SP = 4.0
EDGE_SP = 0.6
MARGIN_SP = 0.3
_cache = {}


def page_gray(pdf, page, dpi=600):
    k = (str(pdf), page, dpi)
    if k not in _cache:
        doc = fitz.open(str(pdf))
        pix = doc[page].get_pixmap(dpi=dpi, colorspace=fitz.csGRAY, alpha=False)
        _cache[k] = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    return _cache[k]


class StaffModel:
    def __init__(self, page):
        self.cells = []
        for c in page["cells"]:
            if c.get("kind") != "measure" or not c.get("staff_line_ys"):
                continue
            x0, y0, x1, y1 = c["rect"]
            ky = (y1 - y0) / c["canonical_h"]
            lines = sorted(y0 + v * ky for v in c["staff_line_ys"])
            self.cells.append(dict(id=c["id"], system=c["system"], staff=c["staff"], measure=c["measure"],
                                   x0=x0, x1=x1, lines=lines, sp=float(np.mean(np.diff(lines)))))
        self.first, self.last, self.sys_x0 = {}, {}, {}
        for c in self.cells:
            s = c["system"]
            self.first[s] = min(self.first.get(s, 10**9), c["measure"])
            self.last[s] = max(self.last.get(s, -1), c["measure"])
        for c in self.cells:
            if c["measure"] == self.first[c["system"]]:
                self.sys_x0[c["system"]] = min(self.sys_x0.get(c["system"], 1e9), c["x0"])

    def nearest(self, cx, cy):
        pool = [c for c in self.cells if c["x0"] <= cx <= c["x1"]]
        if not pool:
            pool = [c for c in self.cells if c["measure"] == self.first[c["system"]]] if cx < min(
                self.sys_x0.values()) else self.cells
            pool = sorted(pool, key=lambda c: min(abs(cx - c["x0"]), abs(cx - c["x1"])))[:60]

        def vdist(c):
            t, b = c["lines"][0], c["lines"][-1]
            return 0.0 if t <= cy <= b else min(abs(cy - t), abs(cy - b))
        return min(pool, key=vdist)


def stem_side(gray, rect, space):
    x0, y0, x1, y1 = [int(round(v)) for v in rect]
    w = x1 - x0
    H, W = gray.shape

    def run_len(xs, going_up):
        best = 0
        for x in xs:
            if x < 0 or x >= W:
                continue
            n, gap = 0, 0
            step = -1 if going_up else 1
            y = y0 if going_up else y1
            while 0 <= y < H and n < 6 * space:
                if gray[y, x] < DARK:
                    n += 1
                    gap = 0
                else:
                    gap += 1
                    if gap > 3:
                        break
                y += step
            best = max(best, n)
        return best
    up = run_len(range(x1 - int(0.30 * w), x1 + int(0.12 * w) + 1), True)
    dn = run_len(range(x0 - int(0.12 * w), x0 + int(0.30 * w) + 1), False)
    cand = sorted([(up, "up"), (dn, "down")], reverse=True)
    if cand[0][0] >= 1.6 * space and cand[0][0] > 1.3 * cand[1][0]:
        return cand[0][1]
    if cand[0][0] >= 1.6 * space:
        return "both?"
    return "none"


def describe(rect, gray, model):
    x0, y0, x1, y1 = rect
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    c = model.nearest(cx, cy)
    sp = c["sp"]
    top, bot = c["lines"][0], c["lines"][-1]
    if top - IN_PAD_SP * sp <= cy <= bot + IN_PAD_SP * sp:
        loc, out_sp = "IN", 0.0
    else:
        out_sp = (top - cy if cy < top else cy - bot) / sp
        loc = "NEAR" if out_sp <= NEAR_MAX_SP else "FAR"
    step = (bot - cy) / (sp / 2)
    s = c["system"]
    first = c["measure"] == model.first[s]
    last = c["measure"] == model.last[s]
    if cx < model.sys_x0[s] - MARGIN_SP * sp:
        zone = "MARGIN"
    elif first and cx < c["x0"] + KEYSLOT_SP * sp:
        zone = "KEYSLOT"
    elif first and cx < c["x0"] + HEADER_SP * sp:
        zone = "HEADER"
    elif last and cx > c["x1"] - BARTAIL_SP * sp:
        zone = "BARTAIL"
    elif cx < c["x0"] + BARHEAD_SP * sp:
        zone = "BARHEAD"
    else:
        zone = "BODY"
    edge = min(abs(cx - c["x0"]), abs(cx - c["x1"])) <= EDGE_SP * sp
    H, W = gray.shape
    ix0, iy0 = max(0, int(round(x0))), max(0, int(round(y0)))
    ix1, iy1 = min(W, max(ix0 + 1, int(round(x1)))), min(H, max(iy0 + 1, int(round(y1))))
    win = gray[iy0:iy1, ix0:ix1]
    fill = float((win < DARK).mean()) if win.size else None
    # centre 40% x 40% window (G3 interior proxy)
    bw, bh = ix1 - ix0, iy1 - iy0
    cwin = gray[iy0 + int(0.3 * bh):iy0 + max(int(0.7 * bh), int(0.3 * bh) + 1),
                ix0 + int(0.3 * bw):ix0 + max(int(0.7 * bw), int(0.3 * bw) + 1)]
    cfill = float((cwin < DARK).mean()) if cwin.size else None
    return dict(w=(x1 - x0) / sp, h=(y1 - y0) / sp, fill=fill, cfill=cfill, loc=loc, out_sp=out_sp, step=step,
                zone=zone, edge=edge, sp_px=sp, cell=c["id"], stem=stem_side(gray, rect, sp))
