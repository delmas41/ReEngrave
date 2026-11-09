"""2.274 step 2 r2 measure-first (b): does a run TOUCH a notehead in its interior?

    python3 touch.py WORKDIR SLICEDIR plate:p,p [plate:p ...]

For each written run: for every notehead of its staff whose centre x lies strictly inside the run (>= 1.5 sp from either end of the ink), the vertical distance in spaces from the
head box's near edge (the edge facing the arc: top of the head for a cap, bottom for a cup) to the run's trace at the head's x. The smallest such distance per run is the
`touch`: two arcs meeting at a note touch it (small), an arc passing over notes keeps clear of them. Printed by category with the distribution.
"""
import bisect
import collections
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[4]))
import arcs as A  # noqa: E402
import measure_first as M  # noqa: E402
import look as LK  # noqa: E402

BINS = [(-9, 0.0), (0.0, 0.4), (0.4, 0.8), (0.8, 1.2), (1.2, 2.0), (2.0, 99)]


def touch_of(row, heads, st, margin_sp=1.5):
    sp = row["space_page_px"]
    pts = row["points"]
    xs = [p[0] for p in pts]
    ce = row.get("core_ends") or [pts[0], pts[-1]]
    xa, xb = ce[0][0], ce[1][0]
    cap = row["sagitta_spaces"] < 0
    best = None
    for k, hb in heads.items():
        s = A.staff_of(k)
        if not s or s[1:] != st:
            continue
        cx = (hb[0] + hb[2]) / 2
        if not (xa + margin_sp * sp < cx < xb - margin_sp * sp):
            continue
        i = bisect.bisect_left(xs, cx)
        if i <= 0 or i >= len(xs):
            continue
        t = (cx - xs[i - 1]) / max(1e-6, xs[i] - xs[i - 1])
        y = pts[i - 1][1] + t * (pts[i][1] - pts[i - 1][1])
        d = (hb[1] - y) / sp if cap else (y - hb[3]) / sp           # cap: head below the arc: gap = head top - arc y
        if best is None or d < best[0]:
            best = (d, k)
    return best


def main():
    work, slices = sys.argv[1:3]
    tab = collections.defaultdict(collections.Counter)
    lst = collections.defaultdict(list)
    for spec in sys.argv[3:]:
        plate, pg = spec.split(":")
        for p in [int(x) for x in pg.split(",")]:
            off, on, extra, boxes, runs = M.load(work, slices, plate, [p])
            heads = LK.heads_of(slices, plate, p)
            for r in A.per_run(extra, off, boxes, runs):
                cat = {"whole": "whole", "none": "new"}.get(r.get("off"), "replaced") if r["status"] == "written" else "abstained"
                t = touch_of(runs[(p, r["ordinal"])], heads, tuple(r["staff"]))
                key = "no_interior_head" if t is None else None
                if t is not None:
                    for lo, hi in BINS:
                        if lo <= t[0] < hi:
                            key = "%.1f..%.1f" % (lo, hi)
                tab[cat][key] += 1
                if t is not None and t[0] < 0.8:
                    lst[cat].append((plate, p, r["ordinal"], round(t[0], 2)))
    keys = ["no_interior_head"] + ["%.1f..%.1f" % b for b in BINS]
    for cat in ("whole", "new", "replaced", "abstained"):
        print("%-10s" % cat, "  ".join("%s:%d" % (k, tab[cat].get(k, 0)) for k in keys))
    for cat in ("replaced",):
        print(cat, "touching <0.8:", lst[cat])


if __name__ == "__main__":
    main()
