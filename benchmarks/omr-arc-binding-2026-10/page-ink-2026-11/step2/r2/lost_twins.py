"""2.274 step 2 r2: of the OFF arcs the ON file does not have, how many have a TWIN in OFF (another OFF arc on the same note columns, i.e. the same arc written once per chord member) -- a lost
twin is the 'one mark, one arc' effect, not a lost arc.

    python3 lost_twins.py WORKDIR SLICEDIR plate:p,p [plate:p ...]
"""
import collections
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[4]))
import arcs as A  # noqa: E402
import measure_first as M  # noqa: E402


def main():
    work, slices = sys.argv[1:3]
    tot = collections.Counter()
    for spec in sys.argv[3:]:
        plate, pg = spec.split(":")
        pages = [int(x) for x in pg.split(",")]
        off, on, extra, boxes, runs = M.load(work, slices, plate, pages)
        pset = set(pages)
        pg_of = lambda a: (A.staff_of(a["start"]) or [None])[0]
        offp = [a for a in off if pg_of(a) in pset]
        onp = [a for a in on if pg_of(a) in pset]
        lost, gained, kept = A.diff_arcs(offp, onp, boxes)
        for a in lost:
            twin = any(b is not a and b["kind"] == a["kind"] and A.same_end(a["start"], b["start"], boxes) and A.same_end(a["stop"], b["stop"], boxes) for b in offp)
            tot["lost"] += 1
            tot["lost_with_an_OFF_twin" if twin else "lost_without_a_twin"] += 1
            if not twin:
                print("no twin:", plate, a["kind"], a["start"], a["stop"])
    print(dict(tot))


if __name__ == "__main__":
    main()
