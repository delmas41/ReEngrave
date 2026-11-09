"""2.274 step 2: every witnessed run of Brahms p0 against Sean's hand arcs (printed arcs, boxes joined across a barline).

    python3 truth_runs_p0.py WORKDIR SLICEDIR [--list]

For each witnessed run: the printed arc (same staff, x extent overlapping the run's) it belongs to; for a WRITTEN run, whether its two bound heads are within REACH spaces of that
printed arc's two ends (RIGHT), and what the OFF file had for that printed arc. Prints the table and, with --list, every written run that is NOT right.
"""
import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import arcs as A  # noqa: E402
import measure_first as M  # noqa: E402
import score as S  # noqa: E402
import truth_p0 as T  # noqa: E402

SP, REACH = 32.0, 2.5


def main():
    work, slices = sys.argv[1], sys.argv[2]
    listing = "--list" in sys.argv
    off, on, extra, boxes, runs = M.load(work, slices, "brahms", [0])
    recs = A.per_run(extra, off, boxes, runs)
    printed = S.printed_arcs(SP)
    tb = json.load(open(S.TRUTH))["boxes"]
    byid = {b["id"]: b for b in tb}
    for pa in printed:
        c = byid[pa["ids"][0]]["cell_id"].split("-")
        pa["staff"] = (int(c[0][1:]), int(c[1][2:]))
        pa["kind"] = pa["cls"][0] if len(pa["cls"]) == 1 else "slur"

    def cx(k):
        b = boxes[k]["box"]
        return (b[0] + b[2]) / 2

    tab = collections.Counter()
    bad = []
    for r in recs:
        st = tuple(r["staff"])
        cand = [pa for pa in printed if pa["staff"] == st and min(pa["x1"], r["x1"]) - max(pa["x0"], r["x0"]) > 0.4 * min(pa["x1"] - pa["x0"], r["x1"] - r["x0"])]
        r["printed"] = cand
        if r["status"] == "written":
            ok = [pa for pa in cand if abs(cx(r["start"]) - pa["x0"]) <= REACH * SP and abs(cx(r["stop"]) - pa["x1"]) <= REACH * SP]
            if ok:
                tab["written_right_ends" + ("" if ok[0]["kind"] == r["kind"] else "_other_kind")] += 1
            elif cand:
                tab["written_ends_differ_from_the_printed_arc"] += 1
                bad.append(r)
            else:
                tab["written_no_printed_arc_there"] += 1
                bad.append(r)
        else:
            tab["abstained_" + ("a_printed_arc_there" if cand else "no_printed_arc")] += 1
    print(dict(tab))
    if listing:
        for r in bad:
            print("NOT RIGHT run", r["ordinal"], r["kind"], "x", round(r["x0"]), round(r["x1"]), "staff", r["staff"], "heads", round(cx(r["start"])), round(cx(r["stop"])),
                  "printed", [(round(p["x0"]), round(p["x1"]), p["kind"]) for p in r["printed"]], "OFF", r.get("off"))


if __name__ == "__main__":
    main()
