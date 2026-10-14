import fitz, numpy as np
_cache = {}
def page_gray(pdf, page, dpi=600):
    k = (pdf, page, dpi)
    if k not in _cache:
        doc = fitz.open(pdf); p = doc[page]
        pix = p.get_pixmap(dpi=dpi, colorspace=fitz.csGRAY, alpha=False)
        a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
        _cache[k] = a
    return _cache[k]

def stem_side(gray, rect, space, thr=140):
    """'up' / 'down' / 'none' read off the raster: a vertical ink run >= 1.6 spaces leaving the head from its right edge
    (up) or left edge (down). Independent of the record's own stem reading."""
    x0, y0, x1, y1 = [int(round(v)) for v in rect]; w = x1-x0
    H, W = gray.shape
    def run_len(xs, going_up):
        best = 0
        for x in xs:
            if x < 0 or x >= W: continue
            n = 0; y = (y0 + y1)//2
            step = -1 if going_up else 1
            # start from head edge, count dark pixels continuously (allow 2 px gaps)
            y = y0 if going_up else y1
            gap = 0
            while 0 <= y < H and n < 6*space:
                if gray[y, x] < thr: n += 1; gap = 0
                else:
                    gap += 1
                    if gap > 3: break
                y += step
            best = max(best, n)
        return best
    rx = range(x1 - int(0.30*w), x1 + int(0.12*w) + 1)
    lx = range(x0 - int(0.12*w), x0 + int(0.30*w) + 1)
    up = run_len(rx, True); dn = run_len(lx, False)
    cand = [(up, "up"), (dn, "down")]
    cand.sort(reverse=True)
    if cand[0][0] >= 1.6*space and cand[0][0] > 1.3*cand[1][0]: return cand[0][1], up, dn
    if cand[0][0] >= 1.6*space: return "both?", up, dn
    return "none", up, dn
