"""2.274 step 2: of the written runs OFF wrote differently (`cut_or_short` / `same_notes_other_kind`), how many are an OFF TIE or arc that ends INSIDE the run (the run chains it to
more): the signature of two arcs meeting at a note read as one run. Counts only; nothing is changed by it.

    python3 chain_census.py WORKDIR SLICEDIR plate:p,p [plate:p,p ...]
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
            recs = A.per_run(extra, off, boxes, runs)
            for r in recs:
                if r["status"] != "written" or r.get("off") not in ("cut_or_short", "same_notes_other_kind"):
                    continue
                tot["replaced"] += 1

                def cx(k):
                    b = boxes[k]["box"]
                    return (b[0] + b[2]) / 2
                xs, xz = cx(r["start"]), cx(r["stop"])
                inside = [a for a in r["off_overlap"] if min(cx(a["start"]), cx(a["stop"])) >= min(xs, xz) - 5 and max(cx(a["start"]), cx(a["stop"])) <= max(xs, xz) + 5
                          and not (A.same_end(a["start"], r["start"], boxes) and A.same_end(a["stop"], r["stop"], boxes))]
                if any(a["kind"] == "tie" for a in inside):
                    tot["an OFF tie lies inside the run and is not the run's pair"] += 1
                elif inside:
                    tot["an OFF slur lies inside the run and is not the run's pair"] += 1
                else:
                    tot["no OFF arc inside the run (OFF arc reaches past an end)"] += 1
    print(dict(tot))


if __name__ == "__main__":
    main()
