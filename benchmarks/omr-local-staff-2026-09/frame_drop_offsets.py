"""Hypothesis 3 + the mechanism test. For every Litolff p3 far head:
 (1) how far the record box sits from its OWN ink, in the raster each arm reads
     (A = fitz undeskewed; B = gather deskewed): centre of the ink blob under the box
     vs box centre, and the fraction of the blob's pixels that fall inside the box;
 (2) how far the record staff lines (stored) sit from the printed lines in each raster
     at the head's x (median of the five);
 (3) [SUPERSEDED by frame_drop_sweep.py; the shift here has the wrong sign] the shift test: read the head on B with its box moved by exactly the (dx, dy)
     that A's frame mismatch gives it. If that reproduces A's reading, the mismatch --
     not the raster -- is what made A read differently.
"""
from __future__ import annotations
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import numpy as np, cv2
import frame_drop_arms as F
import frame_drop_experiments as X
import edge_census as ec


def ink_blob_centre(gray, box, sp):
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    m = int(round(0.6 * sp))
    win = gray[max(0, y0 - m):y1 + m, max(0, x0 - m):x1 + m]
    thr, _ = cv2.threshold(win, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    ink = (win <= thr).astype(np.uint8)
    # remove staff/ledger lines: open with a disc ~0.42 sp (as the reader does)
    d = max(3, int(round(0.42 * sp)) | 1)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d, d))
    op = cv2.morphologyEx(ink, cv2.MORPH_OPEN, k)
    num, lab, stats, cen = cv2.connectedComponentsWithStats(op)
    cx, cy = (x1 + x0) / 2 - max(0, x0 - m), (y1 + y0) / 2 - max(0, y0 - m)
    best, bd = None, 1e9
    for i in range(1, num):
        d_ = np.hypot(cen[i][0] - cx, cen[i][1] - cy)
        if stats[i, cv2.CC_STAT_AREA] > 0.3 * sp * sp and d_ < bd:
            best, bd = i, d_
    if best is None:
        return None
    comp = lab == best
    ys, xs = np.nonzero(comp)
    ox, oy = max(0, x0 - m), max(0, y0 - m)
    inside = ((xs + ox >= x0) & (xs + ox <= x1) & (ys + oy >= y0) & (ys + oy <= y1)).mean()
    return dict(dx=float(xs.mean() + ox - (x0 + x1) / 2), dy=float(ys.mean() + oy - (y0 + y1) / 2),
                inside=float(inside), area=int(comp.sum()))


def line_offset(gray, stored, box):
    """median over the five stored lines of (printed line row - stored row), the printed row
    measured by the reader's own local routine."""
    lines = F.FH.frame_lines_for_head(gray, stored, box)
    return float(np.median(np.array(lines) - np.array(sorted(stored))))


if __name__ == "__main__":
    L = F.load()
    M, Mi = X.rot(L)
    heads2, pbs2, sl2, mbox, mlines = X.mapped(L, Mi)
    shp = L["D"]["shapes"][F.PAGE]
    shape = dict(width_sp=shp["width_sp"], height_sp=shp["height_sp"], tilt_deg=shp["tilt_deg"])
    sk = lambda s: "staff/" + "/".join(s.split("/")[1:4])
    far = [h for h in L["D"]["far"] if h["page"] == F.PAGE]
    # shifted-box arm: B raster, each far head's box moved by A's mismatch (deskew -> original frame is the
    # inverse of what the record frame needs, so A reads the box (dx,dy) away from where B reads it).
    fb = F.FH.FarHeadPage(L["gray_B"], L["heads"], L["page_boxes"], L["staff_lines"])
    fb.adopt(shape, "scorer")
    fa = F.FH.FarHeadPage(L["gray_A"], L["heads"], L["page_boxes"], L["staff_lines"])
    fa.adopt(shape, "scorer")
    rows = []
    for h in far:
        sp = h["spacing"]
        b = h["box"]
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        # A reads the record box on the undeskewed raster: the head is really at map(box centre)
        nx, ny = X.map_pt(Mi, cx, cy)
        mis_dx, mis_dy = nx - cx, ny - cy
        ia = ink_blob_centre(L["gray_A"], b, sp)
        ib = ink_blob_centre(L["gray_B"], b, sp)
        st = L["staff_lines"][sk(h["subject"])]
        lo_a, lo_b = line_offset(L["gray_A"], st, b), line_offset(L["gray_B"], st, b)
        # shifted-box read: B raster, box moved by the mismatch; lines at the shifted x
        sb = (b[0] + mis_dx, b[1] + mis_dy, b[2] + mis_dx, b[3] + mis_dy)
        rs = fb.read(h["subject"], sb, h["cls"], st)
        ra = fa.read(h["subject"], b, h["cls"], st)
        rb = fb.read(h["subject"], b, h["cls"], st)
        rows.append(dict(s=h["subject"], truth=h["truth"], mis=(round(mis_dx, 1), round(mis_dy, 1)),
                         ia=ia, ib=ib, lo_a=lo_a, lo_b=lo_b, A=ra["pos"], B=rb["pos"], Bshift=rs["pos"]))
    print("subject            mismatch(dx,dy)   A: ink-off(dx,dy) inside | B: ink-off(dx,dy) inside | line-off A/B | reads A B B-shifted ref")
    for r in rows:
        f = lambda i: ("n/a" if i is None else f"({i['dx']:+5.1f},{i['dy']:+5.1f}) {i['inside']:.2f}")
        print(f"{r['s']:18} {r['mis']!s:14} A:{f(r['ia'])} | B:{f(r['ib'])} | {r['lo_a']:+.1f}/{r['lo_b']:+.1f} | {r['A']!s:>4} {r['B']!s:>4} {r['Bshift']!s:>4} {r['truth']}")
    def med(k, side, key):
        v = [r[side][key] for r in rows if r[side] is not None]
        return float(np.median(np.abs(v))), float(np.max(np.abs(v)))
    for side in ("ia", "ib"):
        print(side, "|dx| med/max", med(None, side, "dx"), "|dy| med/max", med(None, side, "dy"),
              "inside-box fraction mean", np.mean([r[side]["inside"] for r in rows if r[side]]))
    print("line offset A  median/max", np.median([r["lo_a"] for r in rows]), np.max(np.abs([r["lo_a"] for r in rows])))
    print("line offset B  median/max", np.median([r["lo_b"] for r in rows]), np.max(np.abs([r["lo_b"] for r in rows])))
    same = sum(1 for r in rows if r["Bshift"] == r["A"])
    print("B-with-A's-box-mismatch reproduces A's reading on", same, "of", len(rows),
          "| B equals A on", sum(1 for r in rows if r["B"] == r["A"]))
    print("B-shifted tally", ec.tally([ec.verdict(r["Bshift"], r["truth"]) for r in rows]))
