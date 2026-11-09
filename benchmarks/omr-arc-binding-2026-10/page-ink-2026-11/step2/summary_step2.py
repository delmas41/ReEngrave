"""2.274 step 2: the per-page and pooled readout of a lane-report work dir (witnessed runs, written / abstained, what OFF had, arcs lost and gained).

    python3 summary_step2.py WORKDIR SLICEDIR OUT.json plate:p,p [plate:p,p ...]
"""
import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import measure_first as M  # noqa: E402

KEYS = ("witnessed_runs", "status", "abstain_why", "written_by_kind", "written_vs_OFF", "abstained_with_an_OFF_arc_over_it", "abstained_with_no_OFF_arc_over_it", "closest_ends_used",
        "arcs_OFF", "arcs_ON", "OFF_arcs_not_in_ON", "ON_arcs_not_in_OFF")


def add(acc, s):
    for k in KEYS:
        v = s[k]
        if isinstance(v, dict):
            acc.setdefault(k, collections.Counter()).update(v)
        else:
            acc[k] = acc.get(k, 0) + v
    acc.setdefault("lost_under_no_written_run", []).extend(s["OFF_arcs_not_in_ON_and_under_no_written_run"])


def show(tag, s):
    print("== " + tag)
    for k in KEYS + ("lost_under_no_written_run",):
        v = s.get(k, s.get("OFF_arcs_not_in_ON_and_under_no_written_run") if k == "lost_under_no_written_run" else None)
        print("  %-42s %s" % (k, dict(v) if isinstance(v, collections.Counter) else v))


def main():
    work, slices, out = sys.argv[1], sys.argv[2], sys.argv[3]
    res = {}
    pooled = {}
    for spec in sys.argv[4:]:
        plate, pg = spec.split(":")
        acc = {}
        for p in [int(x) for x in pg.split(",")]:
            s, _recs = M.summarize(plate, [p], work, slices)
            show("%s p%d" % (plate, p), s)
            res["%s p%d" % (plate, p)] = {k: (dict(v) if isinstance(v, collections.Counter) else v) for k, v in s.items()}
            add(acc, s)
            add(pooled, s)
        show("%s pooled" % plate, acc)
    show("ALL pooled", pooled)
    json.dump({"pages": res, "pooled": {k: (dict(v) if isinstance(v, collections.Counter) else v) for k, v in pooled.items()}}, open(out, "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
