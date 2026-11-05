"""Crop a page region with the cache-served production detector boxes drawn thin (green = head classes, blue = others).
usage: python3 crop.py DOC PAGE X0 Y0 X1 Y1 OUT.png [scale]"""
import sys
import numpy as np, cv2
import pagecache as pc, cachelook as cl


def make(doc, pg, x0, y0, x1, y1, out, scale=3, mark=None):
    pws, cells, local = pc.page(doc, pg)
    names = cl.class_names()
    rgb = pws.page.rgb
    crop = rgb[int(y0):int(y1), int(x0):int(x1)].copy()
    if crop.ndim == 2:
        crop = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
    crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    import recordrows as rr
    for o in rr.rows(doc, pg):
        n = o['value'][0]
        bb = o['detail'].get('bbox_page_px')
        if 'notehead' not in n or not bb:
            continue
        if bb[2] < x0 or bb[0] > x1 or bb[3] < y0 or bb[1] > y1:
            continue
        col = (0, 160, 0) if o['reader'] == 'detector' else (200, 0, 200)
        cv2.rectangle(crop, (int((bb[0] - x0) * scale), int((bb[1] - y0) * scale)), (int((bb[2] - x0) * scale), int((bb[3] - y0) * scale)), col, 1)
    for c in ():
        bx = c.bbox_page_px
        if bx[2] < x0 or bx[0] > x1 or bx[3] < y0 or bx[1] > y1:
            continue
        isz, o = cl.lookup(c, confs=(0.25,))
        if 0.25 not in o:
            continue
        for b in cl.serve(c, o[0.25][0], o[0.25][1]):
            n = names[b[0]]
            ax0, ay0 = cl.to_page(c, b[2], b[3]); ax1, ay1 = cl.to_page(c, b[4], b[5])
            if ax1 < x0 or ax0 > x1 or ay1 < y0 or ay0 > y1:
                continue
            if not any(t in n for t in ('notehead', 'ledger')):
                continue
            col = (0, 160, 0) if 'notehead' in n else (200, 120, 0)
            p0 = (int((ax0 - x0) * scale), int((ay0 - y0) * scale)); p1 = (int((ax1 - x0) * scale), int((ay1 - y0) * scale))
            cv2.rectangle(crop, p0, p1, col, 1)
    if mark:
        for (mx, my, lab) in mark:
            cv2.circle(crop, (int((mx - x0) * scale), int((my - y0) * scale)), 3, (0, 0, 255), -1)
    cv2.imwrite(out, crop)


if __name__ == '__main__':
    d, p = sys.argv[1], int(sys.argv[2])
    x0, y0, x1, y1 = map(float, sys.argv[3:7])
    make(d, p, x0, y0, x1, y1, sys.argv[7], float(sys.argv[8]) if len(sys.argv) > 8 else 3)
