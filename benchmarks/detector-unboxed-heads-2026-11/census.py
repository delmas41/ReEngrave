"""CENSUS (labelled 'census', kept apart from the named cases). MEASUREMENT ONLY.

A HOLLOW head leaves a white, head-sized slit-ellipse enclosed by ink. Holes are found on the page raster (staff lines IN, like box_kind's
`cell_ink`), and a hole is UNBOXED when no notehead box of the 20261103-night record (ANY reader: detector, rescue, split, stem-end) contains
its centre. Control: (a) the share of boxed hollow-class heads that contain >= 1 hole (must be high), (b) the share of boxed BLACK-class heads
that contain a hole (must be ~0) -- both can fail.   usage: python3 census.py DOC PAGE [PAGE...]  -> writes census-<doc>-p<page>.json"""
import json
import sys
import numpy as np
import cv2
sys.path.insert(0, 'benchmarks/detector-unboxed-heads-2026-11')
import pagecache as pc
import recordrows as rr

HOLE_AREA_SP2 = (0.05, 0.7)
HOLE_W_MAX_SP = 1.3
HOLE_H_MAX_SP = 0.95


def holes(pws):
    b = pws.page.binary
    white = (b > 127).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(white, connectivity=4)
    out = []
    spaces = {s.staff_index: np.mean(np.diff(s.line_ys)) for s in pws.staves}
    sp0 = float(np.median(list(spaces.values())))
    H, W = b.shape
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if x == 0 or y == 0 or x + w >= W or y + h >= H:
            continue
        A = a / sp0 ** 2
        if not (HOLE_AREA_SP2[0] <= A <= HOLE_AREA_SP2[1]) or w / sp0 > HOLE_W_MAX_SP or h / sp0 > HOLE_H_MAX_SP:
            continue
        if a / float(w * h) < 0.45:          # slit/ellipse fills its box; a ragged gap between strokes does not
            continue
        # near a staff (within 6 sp of its lines)
        cy, cx = cen[i][1], cen[i][0]
        near = [s for s in pws.staves if s.x_start - 5 <= cx <= s.x_end + 5 and s.top_y - 6 * sp0 <= cy <= s.bottom_y + 6 * sp0]
        if not near:
            continue
        # ink ring: >= 60% of the pixels one px outside the box are ink
        x0, y0, x1, y1 = max(0, x - 2), max(0, y - 2), min(W, x + w + 2), min(H, y + h + 2)
        ring = b[y0:y1, x0:x1] == 0
        out.append(dict(cx=float(cx), cy=float(cy), w=int(w), h=int(h), area_sp2=round(float(A), 3), sp=sp0,
                        ring_ink=round(float(ring.mean()), 2)))
    return out, sp0


def main(doc, pg):
    pws, cells, local = pc.page(doc, pg)
    hs, sp0 = holes(pws)
    boxes = []
    for o in rr.rows(doc, pg):
        n = o['value'][0]
        bb = o['detail'].get('bbox_page_px')
        if 'notehead' in n and bb:
            boxes.append((n, o['reader'], bb, o['subject']))

    def inside(cx, cy, bb, pad=0.0):
        return bb[0] - pad <= cx <= bb[2] + pad and bb[1] - pad <= cy <= bb[3] + pad
    # controls
    hol = [bx for bx in boxes if 'Half' in bx[0] or 'Whole' in bx[0]]
    blk = [bx for bx in boxes if 'Black' in bx[0]]
    c_hol = sum(any(inside(h['cx'], h['cy'], bx[2]) for h in hs) for bx in hol)
    c_blk = sum(any(inside(h['cx'], h['cy'], bx[2]) for h in hs) for bx in blk)
    un = [h for h in hs if not any(inside(h['cx'], h['cy'], bx[2], 3) for bx in boxes)]
    res = dict(doc=doc, page=pg, sp=sp0, holes=len(hs), hollow_boxes=len(hol), hollow_boxes_with_hole=c_hol, black_boxes=len(blk),
               black_boxes_with_hole=c_blk, unboxed_holes=un)
    json.dump(res, open('benchmarks/detector-unboxed-heads-2026-11/census-%s-p%d.json' % (doc, pg), 'w'), indent=1)
    print(doc, pg, 'holes', len(hs), '| hollow-class boxes %d with a hole %d | black-class boxes %d with a hole %d | UNBOXED holes %d' % (
        len(hol), c_hol, len(blk), c_blk, len(un)))
    return res


if __name__ == '__main__':
    for p in sys.argv[2:]:
        main(sys.argv[1], int(p))
