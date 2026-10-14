"""2.115: ink-centroid re-centre candidate, page frame. usage: centroid_probe.py OUT.json"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, "."); sys.path.insert(0, "benchmarks/omr-head-recentre-2026-10")
import explore as X
from tools.omr.staged import gather as G
from tools.omr.staged.geometry import STANDARD_HEAD_WIDTH_SPACES as SW, STANDARD_HEAD_HEIGHT_SPACES as SHH

def centroid(raw, cx, cy, sp, iters=3, vwin=0.8, hwin=0.7, lock_x=True):
    """mean-shift of the ink centroid (line rows and stem columns left out) from (cx, cy). Returns dict or None."""
    ink = raw == 0
    H, W = ink.shape
    R = int(3.2 * sp)
    X0, X1 = max(0, int(cx - R)), min(W, int(cx + R)); Y0, Y1 = max(0, int(cy - R)), min(H, int(cy + R))
    sub = ink[Y0:Y1, X0:X1].copy()
    if sub.size == 0: return None
    # line rows: ink both sides beyond a head (0.78..0.98 sp either side of the current centre), at least 0.6 each
    def line_rows(xc):
        lo_l, hi_l = int(round(xc - 0.98*sp)) - X0, int(round(xc - 0.78*sp)) - X0
        lo_r, hi_r = int(round(xc + 0.78*sp)) - X0, int(round(xc + 0.98*sp)) - X0
        l = sub[:, max(0, lo_l):max(0, hi_l)]; r = sub[:, max(0, lo_r):max(0, hi_r)]
        if l.shape[1] == 0 or r.shape[1] == 0: return np.zeros(sub.shape[0], bool)
        return (l.mean(axis=1) >= 0.6) & (r.mean(axis=1) >= 0.6)
    # stem columns: ink pixels whose vertical run is > 1.7 sp
    runlen = np.zeros(sub.shape, int)
    for x in range(sub.shape[1]):
        col = sub[:, x]
        if not col.any(): continue
        d = np.diff(np.concatenate([[0], col.astype(np.int8), [0]]))
        for s, e in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
            runlen[s:e, x] = e - s
    stem = runlen > 1.7*sp
    ex, ey = cx, cy
    for _ in range(iters):
        lr = line_rows(ex)
        m = sub & ~stem & ~lr[:, None]
        yy, xx = np.mgrid[0:sub.shape[0], 0:sub.shape[1]]
        win = (np.abs(xx + X0 - ex) <= hwin*sp) & (np.abs(yy + Y0 - ey) <= vwin*sp)
        pts = m & win
        n = int(pts.sum())
        if n < 0.15*sp*sp: return None
        nx, ny = float((xx[pts]).mean() + X0), float((yy[pts]).mean() + Y0)
        if abs(ny-ey) < 0.2 and (lock_x or abs(nx-ex) < 0.2): ex, ey = (ex if lock_x else nx), ny; break
        ex, ey = (ex if lock_x else nx), ny
    return dict(dx_sp=round((ex-cx)/sp, 3), dy_sp=round((ey-cy)/sp, 3), n=n, lines=int(lr.sum()))

if __name__ == "__main__":
    res = json.load(open(sys.argv[1]))
    rast = {"brahms": X.raster(X.BRA, 0), "litolff": X.raster(X.LIT, 1)}
    out = []
    for h in res:
        m = min(h["wr"], h["hr"])
        if m >= 1.05: continue
        x0, y0, x1, y1 = h["box"]; cx, cy = (x0+x1)/2, (y0+y1)/2
        sp = h["sp"]; raw = rast[h["page"]]
        c = centroid(raw, cx, cy, sp)
        h["centroid"] = c
        std = lambda ccx, ccy: (ccx-0.5*SW*sp, ccy-0.5*SHH*sp, SW*sp, SHH*sp)
        def rd(b):
            r = G.notehead_ink_under(raw, b); o = G.notehead_ink_off_line(raw, b, sp)
            return [None if r is None else r["windows"]["center"], None if o is None else o["windows"]["center"]]
        h["read_box"] = rd((x0, y0, x1-x0, y1-y0))
        if c: h["read_new"] = rd(std(cx+c["dx_sp"]*sp, cy+c["dy_sp"]*sp))
        out.append(h)
    Path(sys.argv[2]).write_text(json.dumps(out))
    t = [h for h in out if h["key"] == "glyph/1/0/9/11/1"]
    print("tile13", t)
