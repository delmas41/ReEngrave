"""2.274 step 2 r2 measure-first (b): the bridged GAPS of each witnessed run and what stands in them.

    python3 gaps.py WORKDIR SLICEDIR PLATE PAGE[,PAGE]

A run's thinned points are one per ~2 columns where ink was tracked; a stretch of columns with no ink (the tracker bridged a blanked head, a stem, a barline, a dynamic) shows as
a jump in x. For each such gap of >= MINGAP spaces: the noteheads of the run's staff whose centre lies in the gap (+- 0.6 sp) and within 3 sp of the run's y there, and the
run's slope change across the gap. Printed beside the run's category (whole / replaced / new / abstained, from the per-run record) so the signature of 'two arcs meet at a note'
can be read against the cases a look called right or wrong.
"""
import json
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[4]))
import arcs as A  # noqa: E402
import measure_first as M  # noqa: E402
import look as LK  # noqa: E402

MINGAP = 0.5


def run_gaps(row, heads, st):
    sp = row["space_page_px"]
    pts = row["points"]
    out = []
    sh = [(k, b) for k, b in heads.items() if A.staff_of(k) and A.staff_of(k)[1:] == st]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        gx = b[0] - a[0]
        if gx < MINGAP * sp:
            continue
        inh = []
        for k, hb in sh:
            cx = (hb[0] + hb[2]) / 2
            cy = (hb[1] + hb[3]) / 2
            ymid = (a[1] + b[1]) / 2
            if a[0] - 0.6 * sp <= cx <= b[0] + 0.6 * sp and abs(cy - ymid) <= 4.5 * sp:
                inh.append(k.split("/", 3)[3])
        # turn: slope before (over the 1.5 sp before the gap) vs after
        def slope(j0, j1):
            p, q = pts[j0], pts[j1]
            return math.degrees(math.atan2(q[1] - p[1], max(1e-6, q[0] - p[0])))
        j0 = max(0, i - 4)
        j1 = min(len(pts) - 1, i + 5)
        out.append(dict(x0=round(a[0]), x1=round(b[0]), gap_sp=round(gx / sp, 2), heads=inh, bridge_deg=round(slope(i, i + 1), 1), before_deg=round(slope(j0, i), 1),
                        after_deg=round(slope(i + 1, j1), 1)))
    return out


def main():
    work, slices, plate, pg = sys.argv[1:5]
    for p in [int(x) for x in pg.split(",")]:
        off, on, extra, boxes, runs = M.load(work, slices, plate, [p])
        recs = A.per_run(extra, off, boxes, runs)
        heads = LK.heads_of(slices, plate, p)
        for r in recs:
            cat = {"whole": "whole", "none": "new"}.get(r.get("off"), "replaced") if r["status"] == "written" else "abstained"
            row = runs[(p, r["ordinal"])]
            gs = run_gaps(row, heads, tuple(r["staff"]))
            gs = [g for g in gs if g["gap_sp"] >= 1.0]
            print("p%d run %3d %-9s x %d-%d  %s" % (p, r["ordinal"], cat, r["x0"], r["x1"], json.dumps(gs)))


if __name__ == "__main__":
    main()
