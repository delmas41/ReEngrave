"""2.274 step 2 r2 measure-first (b): the largest bridged gap of each witnessed run, by category, on the pages named (develop pages for choosing; every page for the readout).

    python3 gapdist.py WORKDIR SLICEDIR plate:p,p [plate:p ...]
"""
import collections
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[4]))
import arcs as A  # noqa: E402
import measure_first as M  # noqa: E402

BINS = [(0, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, 2.5), (2.5, 3.5), (3.5, 99)]


def maxgap(row):
    sp = row["space_page_px"]
    pts = row["points"]
    g = [(b[0] - a[0]) / sp for a, b in zip(pts, pts[1:])]
    return max(g) if g else 0.0


def main():
    work, slices = sys.argv[1:3]
    tab = collections.defaultdict(collections.Counter)
    for spec in sys.argv[3:]:
        plate, pg = spec.split(":")
        for p in [int(x) for x in pg.split(",")]:
            off, on, extra, boxes, runs = M.load(work, slices, plate, [p])
            for r in A.per_run(extra, off, boxes, runs):
                cat = {"whole": "whole", "none": "new"}.get(r.get("off"), "replaced") if r["status"] == "written" else "abstained"
                mg = maxgap(runs[(p, r["ordinal"])])
                for lo, hi in BINS:
                    if lo <= mg < hi:
                        tab[cat]["%.1f-%.1f" % (lo, hi)] += 1
    for cat in ("whole", "new", "replaced", "abstained"):
        print("%-10s" % cat, "  ".join("%s:%d" % (k, tab[cat].get(k, 0)) for k in ["%.1f-%.1f" % b for b in BINS]))


if __name__ == "__main__":
    main()
