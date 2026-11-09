"""2.274 step 2 r2: list the runs of a page by status / OFF relation (development aid).

    python3 listruns.py WORKDIR SLICEDIR PLATE PAGE[,PAGE] [--only replaced|new|whole|abstained]
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[4]))
import arcs as A  # noqa: E402
import measure_first as M  # noqa: E402


def main():
    argv = sys.argv[1:]
    only = None
    if "--only" in argv:
        i = argv.index("--only")
        only = argv[i + 1]
        del argv[i:i + 2]
    work, slices, plate, pg = argv[:4]
    for p in [int(x) for x in pg.split(",")]:
        off, on, extra, boxes, runs = M.load(work, slices, plate, [p])
        recs = A.per_run(extra, off, boxes, runs)
        for r in recs:
            cat = {"whole": "whole", "none": "new"}.get(r.get("off"), "replaced") if r["status"] == "written" else "abstained"
            if only and cat != only:
                continue

            def cx(k):
                b = boxes[k]["box"]
                return round((b[0] + b[2]) / 2)
            offs = ["%s %d-%d" % (a["kind"][0], cx(a["start"]), cx(a["stop"])) for a in r["off_overlap"]]
            print("p%d run %3d %-9s %-5s staff %s x %d-%d  %s  heads %s-%s  OFF %s  %s" % (p, r["ordinal"], cat, r.get("kind") or "-", r["staff"], r["x0"], r["x1"], r.get("why") or "",
                                                                                           cx(r["start"]) if r.get("start") else "-", cx(r["stop"]) if r.get("stop") else "-", offs, r.get("closest") or ""))


if __name__ == "__main__":
    main()
