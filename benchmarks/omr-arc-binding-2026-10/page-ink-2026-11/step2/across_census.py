"""2.274 step 2: arcs of the OFF and ON files that join two systems (glyph keys on two systems), and the witnessed runs that ended at a system's edge.

    python3 across_census.py WORKDIR SLICEDIR plate:p,p [plate:p,p ...]
"""
import collections
import sys
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import arcs as A  # noqa: E402
import measure_first as M  # noqa: E402


def main():
    work, slices = sys.argv[1], sys.argv[2]
    tot = collections.Counter()
    for spec in sys.argv[3:]:
        plate, pg = spec.split(":")
        for p in [int(x) for x in pg.split(",")]:
            off, on, extra, boxes, runs = M.load(work, slices, plate, [p])
            for tag, arcs in (("OFF", off), ("ON", on)):
                for a in arcs:
                    s, t = A.staff_of(a["start"]), A.staff_of(a["stop"])
                    if s and t and s[0] == p and s[1] != t[1]:
                        tot[tag + " arcs across a system break"] += 1
            for v in extra:
                for e in v["detail"]["runs"]:
                    if e.get("edge"):
                        tot["witnessed runs at a system's edge (offered to the join)"] += 1
    print(dict(tot))


if __name__ == "__main__":
    main()
