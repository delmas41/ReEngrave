"""2.274 step 2 r2 measure-first (b), the part the bridged gap does not reach: a written run with an OFF TIE (the detector's decided pair) inside it that is not the run's own pair.

    python3 tie_inside.py WORKDIR SLICEDIR plate:p,p [plate:p ...]

For each such run: the OFF tie's two heads, and `hug` = the vertical distance in spaces from the tie's heads' near edge to the run's trace at the tie's middle (a tie lies on its heads, a
slur that passes OVER a tied pair keeps clear: small `hug` = the run's ink IS the tie's ink = a chain; large = a slur over a tie). Category and the run's own kind beside.
"""
import bisect
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[4]))
import arcs as A  # noqa: E402
import measure_first as M  # noqa: E402


def main():
    work, slices = sys.argv[1:3]
    for spec in sys.argv[3:]:
        plate, pg = spec.split(":")
        for p in [int(x) for x in pg.split(",")]:
            off, on, extra, boxes, runs = M.load(work, slices, plate, [p])
            for r in A.per_run(extra, off, boxes, runs):
                if r["status"] != "written":
                    continue
                row = runs[(p, r["ordinal"])]
                xs = [q[0] for q in row["points"]]
                cap = row["sagitta_spaces"] < 0
                sp = row["space_page_px"]

                def cx(k):
                    b = boxes[k]["box"]
                    return (b[0] + b[2]) / 2
                xa, xb = sorted((cx(r["start"]), cx(r["stop"])))
                for a in r["off_overlap"]:
                    if a["kind"] != "tie" or (A.same_end(a["start"], r["start"], boxes) and A.same_end(a["stop"], r["stop"], boxes)):
                        continue
                    ta, tb = sorted((cx(a["start"]), cx(a["stop"])))
                    if ta < xa - 0.3 * sp or tb > xb + 0.3 * sp:
                        continue
                    mid = (ta + tb) / 2
                    i = min(max(1, bisect.bisect_left(xs, mid)), len(xs) - 1)
                    t = (mid - xs[i - 1]) / max(1e-6, xs[i] - xs[i - 1])
                    y = row["points"][i - 1][1] + t * (row["points"][i][1] - row["points"][i - 1][1])
                    hb = boxes[a["start"]]["box"]
                    edge = hb[1] if cap else hb[3]
                    hug = ((edge - y) if cap else (y - edge)) / sp
                    cat = {"whole": "whole", "none": "new"}.get(r.get("off"), "replaced")
                    print("%s p%d run %3d %-8s %-4s run x %d-%d  OFF tie %d-%d  hug %.2f sp" % (plate, p, r["ordinal"], cat, r["kind"], r["x0"], r["x1"], ta, tb, hug))


if __name__ == "__main__":
    main()
