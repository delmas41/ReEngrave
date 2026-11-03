"""2.251 F cut-off, the cause question (test-2.251-f-cutoff): could the dots of an F clef be seen when they touch a head?
For every body-scan place (fcut_scan.py rows, body score >= FLOOR) look at the two line-4 spaces right of the matched body: a dot-sized
DISC (radius 0.2 sp) centred on the F line +/- 0.5 sp, at the best x within DX of the body's right edge. fill = share of the disc that is
ink, the staff lines NOT cleared (the discs sit in the spaces). ring = share of the ring 0.35-0.55 sp around it that is ink (a lone dot has
an empty ring; a dot fused to a head has part of it filled; a solid blob fills all). Measures only; builds no reader.

python3 work-2.251/fcut_dots.py PLATE SCAN.json FLOOR OUT.json
"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.getcwd(), "work-2.251"))
sys.path.insert(0, os.getcwd())
os.environ.setdefault("CLEF_INK_CACHE", "/private/tmp/claude-501/s/ink")
import scan_claims as SC  # noqa: E402
from tools.omr.staged import clef_pagewide as CP  # noqa: E402

plate, spath, floor, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
res = json.load(open(spath))


def disc(ink, cx, cy, r0, r1):
    ys, xs = np.ogrid[:ink.shape[0], :ink.shape[1]]
    R = int(r1) + 2
    y0, y1, x0, x1 = int(cy) - R, int(cy) + R + 1, int(cx) - R, int(cx) + R + 1
    if y0 < 0 or x0 < 0 or y1 > ink.shape[0] or x1 > ink.shape[1]:
        return None
    yy, xx = np.mgrid[y0:y1, x0:x1]
    d = np.hypot(yy - cy, xx - cx)
    m = (d <= r1) & (d >= r0)
    sub = ink[y0:y1, x0:x1]
    return float(sub[m].mean()) if m.any() else None


rows = []
for pr in res:
    pg = pr["page"]
    sc = [r for r in pr["scan"] if r["score"] >= floor]
    if not sc:
        continue
    ink = SC.page_ink(plate, pg)
    st = {(s, li): t for s, li, t, cells in SC.staves_of(plate, pg)}
    for r in sc:
        t = st[(r["system"], r["staff"])]
        lines = [float(v) for v in t["line_ys"]]
        sp = r["sp"]
        ll = CP.local_lines(ink, lines, sp, r["box"][2])
        yf = ll[1]
        best = None
        x1 = r["box"][2]
        for dx in np.arange(-0.3 * sp, 1.6 * sp, 1.0):
            cx = x1 + dx
            up = disc(ink, cx, yf - 0.5 * sp, 0, 0.2 * sp)
            lo = disc(ink, cx, yf + 0.5 * sp, 0, 0.2 * sp)
            if up is None or lo is None:
                continue
            f = min(up, lo)
            if best is None or f > best[0]:
                ru = disc(ink, cx, yf - 0.5 * sp, 0.35 * sp, 0.55 * sp)
                rl = disc(ink, cx, yf + 0.5 * sp, 0.35 * sp, 0.55 * sp)
                best = (f, max(ru, rl), float(dx / sp))
        if best:
            rows.append({**{k: r[k] for k in ("score", "page", "system", "staff", "cell", "x", "near")}, "fill": round(best[0], 3), "ring": round(best[1], 3), "dx": round(best[2], 2)})
    print("page", pg, file=sys.stderr, flush=True)
json.dump(rows, open(out, "w"))
