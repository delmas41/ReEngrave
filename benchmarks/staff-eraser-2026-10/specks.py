"""ROADMAP 2.206 (read-only): a measure of each eraser variant that does NOT use the line model the 'band' variant erases by
(reach.py's overcut is circular for 'band'). usage: specks.py PLATE OUT.json PAGE...

Per cell and variant:
  specks   connected components of the erased raster of area < SPECK_SP2 whose centre is within 0.3 sp of a staff line and that
           were NOT a separate component of the binary (new fragments the erase made: line remnants, nibbled marks).
  cleared  share of ink in the rows +-1 px of each nominal line that the variant removed (as the 2a12ac501 commit measured).
  pieces   number of components >= SPECK_SP2 (a mark cut in two counts twice).
"""
import json, sys, time
import cv2
import numpy as np
sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/staff-eraser-2026-10")
import reach as R  # noqa: E402
from tools.omr.staged import gather as G, pipeline  # noqa: E402

SPECK_SP2 = 0.02


def comps(ink, sp):
    n, lab, st, cen = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
    return n, lab, st, cen


def main():
    plate, out = sys.argv[1], sys.argv[2]
    pages = [int(a) for a in sys.argv[3:]]
    res = {}
    for pg in pages:
        pws, cells = pipeline.prepare_pages(R.PDF[plate], [pg], dpi=600)[0]
        loc = G.gather_geometry(G.Log(), pws)
        for c in cells:
            key = loc.get(c.staff_index)
            ys = list(c.staff_line_ys_canonical or [])
            if key is None or len(ys) < 2:
                continue
            ck = "%d/%s/%s/%s" % (pg, key[0], key[1], c.measure_index)
            ink0 = c.binary == 0
            row = {}
            for v in R.VARIANTS:
                er, diag, sp = R.erase_variant(c.binary, ys, v)
                ink = er == 0
                n, lab, st, cen = comps(ink, sp)
                small = st[1:, cv2.CC_STAT_AREA] < SPECK_SP2 * sp * sp
                near = np.min(np.abs(cen[1:, 1][:, None] - np.array(ys)[None, :]), axis=1) <= 0.3 * sp
                # new = a small component whose pixels were part of a LARGER component of the binary
                n0, lab0, st0, _ = comps(ink0, sp)
                new = 0
                for j in np.nonzero(small & near)[0] + 1:
                    yy, xx = np.nonzero(lab == j)
                    if st0[lab0[yy[0], xx[0]], cv2.CC_STAT_AREA] > st[j, cv2.CC_STAT_AREA]:
                        new += 1
                rows = np.zeros(ink0.shape[0], bool)
                for y in ys:
                    rows[max(0, int(round(y)) - 1):int(round(y)) + 2] = True
                line_ink = ink0[rows].sum()
                cleared = float((ink0[rows] & ~ink[rows]).sum() / line_ink) if line_ink else None
                row[v] = dict(specks=int(new), cleared=cleared, pieces=int((~small).sum()))
            res[ck] = row
        print(plate, pg, len(res), time.strftime("%H:%M:%S"), flush=True)
        json.dump(res, open(out, "w"))


if __name__ == "__main__":
    main()
