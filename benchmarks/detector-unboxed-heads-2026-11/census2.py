"""CENSUS 2 ('census' label). Hollow dyad heads with NO notehead box of any reader in the 20261103-night record.

Candidate = an enclosed white hole (census.holes) with area >= 0.2 sp^2 whose centre is in the SAME COLUMN (|dx| <= 0.3 sp) of a boxed hollow-class
head and 0.8..1.4 sp above/below it (a third: the interval two heads of one column stand at, page-facts / box_kind HOLE_MIN_STEPS), and which no
record notehead box (any reader) covers.  Every candidate is then CONFIRMED BY EYE on a crop before it counts (CLAUDE rule 7).
Output: census2-<doc>.json.   usage: python3 census2.py DOC PAGE [PAGE...]"""
import json
import sys
sys.path.insert(0, 'benchmarks/detector-unboxed-heads-2026-11')
import census as cs
import pagecache as pc
import recordrows as rr


def run(doc, pg):
    pws, cells, local = pc.page(doc, pg)
    hs, sp = cs.holes(pws)
    boxes = [(o['value'][0], o['detail']['bbox_page_px'], o['reader'], o['subject']) for o in rr.rows(doc, pg)
             if 'notehead' in o['value'][0] and o['detail'].get('bbox_page_px')]

    def inside(h, bb, pad=0):
        return bb[0] - pad <= h['cx'] <= bb[2] + pad and bb[1] - pad <= h['cy'] <= bb[3] + pad
    out = []
    for h in hs:
        if h['area_sp2'] < 0.2 or any(inside(h, bb, 2) for n, bb, r, s in boxes):
            continue
        for n, bb, r, s in boxes:
            if 'Half' not in n:
                continue
            bcx, bcy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
            dx, dy = (h['cx'] - bcx) / sp, (h['cy'] - bcy) / sp
            if abs(dx) <= 0.3 and 0.8 <= abs(dy) <= 1.4:
                out.append(dict(doc=doc, page=pg, cx=round(h['cx'], 1), cy=round(h['cy'], 1), area_sp2=h['area_sp2'], sp=round(sp, 2),
                                nearest_box=s, nearest_class=n, nearest_reader=r, dx_sp=round(dx, 2), dy_sp=round(dy, 2)))
                break
    return out


if __name__ == '__main__':
    doc = sys.argv[1]
    allc = []
    for p in sys.argv[2:]:
        c = run(doc, int(p))
        print(doc, p, len(c), flush=True)
        allc += c
    json.dump(allc, open('benchmarks/detector-unboxed-heads-2026-11/census2-%s.json' % doc, 'w'), indent=1)
