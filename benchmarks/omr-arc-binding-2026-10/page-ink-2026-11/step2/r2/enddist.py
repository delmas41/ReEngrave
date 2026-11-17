"""2.274 step 2 r2 measure-first (d): how far from the ink's own end is the head a written run's end was bound to?

    python3 enddist.py WORKDIR SLICEDIR plate:p,p [plate:p ...] [--list MIN]

`distance_spaces` is the binder's own (|dx| + |dy| from the ink end to the head's centre, in spaces). Printed as a histogram over the written runs' ends by category; `--list MIN` prints
the runs with an end at MIN spaces or more (for a crop look).
"""
import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[4]))
import arcs as A  # noqa: E402
import measure_first as M  # noqa: E402

BINS = [0, 1, 2, 3, 4, 6, 99]


def main():
    argv = sys.argv[1:]
    lst = None
    if "--list" in argv:
        i = argv.index("--list")
        lst = float(argv[i + 1])
        del argv[i:i + 2]
    work, slices = argv[:2]
    tab = collections.defaultdict(collections.Counter)
    rows = []
    for spec in argv[2:]:
        plate, pg = spec.split(":")
        for p in [int(x) for x in pg.split(",")]:
            off, on, extra, boxes, runs = M.load(work, slices, plate, [p])
            recs = A.per_run(extra, off, boxes, runs)
            by = {}
            for v in extra:
                for r in (v.get("detail") or {}).get("runs") or ():
                    by[(int(v["subject"].split("/")[1]), r.get("ordinal"), r.get("piece"))] = r
            for r in recs:
                if r["status"] != "written":
                    continue
                e = by.get((p, r["ordinal"], r.get("piece")))
                cat = {"whole": "whole", "none": "new"}.get(r.get("off"), "replaced")
                for side in ("left", "right"):
                    d = ((e or {}).get(side) or {}).get("distance_spaces")
                    if d is None:
                        continue
                    for lo, hi in zip(BINS, BINS[1:]):
                        if lo <= d < hi:
                            tab[cat]["%d-%d" % (lo, hi)] += 1
                    if lst is not None and d >= lst:
                        rows.append((plate, p, r["ordinal"], side, d, cat))
    keys = ["%d-%d" % b for b in zip(BINS, BINS[1:])]
    for cat in ("whole", "new", "replaced"):
        print("%-9s" % cat, "  ".join("%s:%d" % (k, tab[cat].get(k, 0)) for k in keys))
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
