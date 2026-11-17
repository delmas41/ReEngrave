"""2.274 step 2: for the tiles of a key.json, what the OFF file wrote over the same run (the arcs it replaced), by the notes' x positions.

    python3 off_for_tiles.py WORKDIR SLICEDIR KEY.json [tile,tile,...]
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import arcs as A  # noqa: E402
import measure_first as M  # noqa: E402


def main():
    work, slices, key = sys.argv[1], sys.argv[2], json.load(open(sys.argv[3]))
    want = {int(x) for x in sys.argv[4].split(",")} if len(sys.argv) > 4 else None
    cache = {}
    for k in key:
        if want and k["tile"] not in want:
            continue
        plate, page = k["plate"], k["page"]
        if (plate, page) not in cache:
            cache[(plate, page)] = M.load(work, slices, plate, [page])
        off, on, extra, boxes, runs = cache[(plate, page)]
        recs = A.per_run(extra, off, boxes, runs)
        r = next(x for x in recs if x["ordinal"] == k["run"])

        def cx(key_):
            b = boxes[key_]["box"]
            return round((b[0] + b[2]) / 2)
        print("tile %2d %-9s %s p%d run %d (%s, x %d-%d): ON %s %d -> %d" % (k["tile"], k["category"], plate, page, k["run"], r["status"], r["x0"], r["x1"], k["kind"], cx(k["start"]), cx(k["stop"])))
        for a in r["off_overlap"]:
            print("        OFF %s %d -> %d" % (a["kind"], cx(a["start"]), cx(a["stop"])))


if __name__ == "__main__":
    main()
