"""2.274 step 2: per witnessed run, what the binder did and what the OFF file already writes.

    python3 measure_first.py WORKDIR SLICEDIR PLATE PAGE[,PAGE...] [--json OUT]

WORKDIR = a lane-report `work/` (OFF and ON MusicXML + `<plate>.on.extra.json`), SLICEDIR = the injected slices (`build_inject.py`).
Prints, for the pages: witnessed runs; written / abstained by reason; of the written, OFF already `whole` / `cut_or_short` / `same_notes_other_kind` / `none`;
OFF arcs that ON no longer has (and whether a written run overlaps each: one that no run overlaps would be a bug); ON arcs OFF did not have.
"""
import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3]))

import arcs as A  # noqa: E402
from tools.omr.staged import lane_report as L  # noqa: E402


def load(workdir, slicedir, plate, pages):
    wd = pathlib.Path(workdir)
    off = A.arcs_of_xml((wd / ("%s.off.musicxml" % plate)).read_text())
    on = A.arcs_of_xml((wd / ("%s.on.musicxml" % plate)).read_text())
    extra = json.loads((wd / ("%s.on.extra.json" % plate)).read_text())
    boxes, runs = {}, {}
    with open(pathlib.Path(slicedir) / plate / "observations.jsonl") as fh:
        for line in fh:
            if '"glyph_box"' not in line and '"page_arc"' not in line:
                continue
            o = json.loads(line)
            if o["quantity"] == "glyph_box":
                b = (o.get("detail") or {}).get("bbox_page_px")
                if b:
                    boxes[o["subject"]] = dict(page=L.page_of(o["subject"]), box=[float(x) for x in b])
            elif o["quantity"] == "page_arc" and o["value"] == "run":
                d = o["detail"]
                runs[(L.page_of(o["subject"]), d["ordinal"])] = d
    pg = set(pages)
    extra = [v for v in extra if int(v["subject"].split("/")[1]) in pg]
    return off, on, extra, boxes, runs


def summarize(plate, pages, workdir, slicedir):
    off, on, extra, boxes, runs = load(workdir, slicedir, plate, pages)
    recs = A.per_run(extra, off, boxes, runs)
    out = collections.OrderedDict()
    out["witnessed_runs"] = len(recs)
    out["status"] = dict(collections.Counter(r["status"] for r in recs))
    out["abstain_why"] = dict(collections.Counter(r["why"] for r in recs if r["status"] == "abstained"))
    out["written_by_kind"] = dict(collections.Counter(r["kind"] for r in recs if r["status"] == "written"))
    out["written_vs_OFF"] = dict(collections.Counter(r["off"] for r in recs if r["status"] == "written"))
    out["abstained_with_an_OFF_arc_over_it"] = sum(1 for r in recs if r["status"] == "abstained" and r["off_overlap"])
    out["abstained_with_no_OFF_arc_over_it"] = sum(1 for r in recs if r["status"] == "abstained" and not r["off_overlap"])
    out["closest_ends_used"] = sum(len(r["closest"] or ()) for r in recs if r["status"] == "written")
    # arcs of the two files, on the counted pages
    def page_of_arc(a):
        s = A.staff_of(a["start"])
        return None if s is None else s[0]
    pg = set(pages)
    off_p = [a for a in off if page_of_arc(a) in pg]
    on_p = [a for a in on if page_of_arc(a) in pg]
    lost, gained, _kept = A.diff_arcs(off_p, on_p, boxes)
    lost_k = [(a["kind"], a["start"], a["stop"]) for a in lost]
    gained_k = [(a["kind"], a["start"], a["stop"]) for a in gained]
    written = [r for r in recs if r["status"] == "written"]

    def under_a_written_run(k):
        kind, s, t = k
        a = dict(kind=kind, start=s, stop=t)
        sp = A.span_of(a, boxes)
        st = A.staff_of(s)
        if not sp or not st:
            return False
        for r in written:
            if r["page"] == st[0] and tuple(r["staff"]) == (st[1], st[2]) and min(sp[1], r["x1"]) - max(sp[0], r["x0"]) > 0.5 * min(sp[1] - sp[0], r["x1"] - r["x0"]):
                return True
        return False
    out["arcs_OFF"] = dict(collections.Counter(a["kind"] for a in off_p))
    out["arcs_ON"] = dict(collections.Counter(a["kind"] for a in on_p))
    out["OFF_arcs_not_in_ON"] = dict(collections.Counter(k[0] for k in lost_k))
    out["OFF_arcs_not_in_ON_and_under_no_written_run"] = [list(k) for k in lost_k if not under_a_written_run(k)]
    out["ON_arcs_not_in_OFF"] = dict(collections.Counter(k[0] for k in gained_k))
    return out, recs


if __name__ == "__main__":
    argv = sys.argv[1:]
    jout = None
    if "--json" in argv:
        i = argv.index("--json")
        jout = argv[i + 1]
        del argv[i:i + 2]
    workdir, slicedir, plate, pages = argv[0], argv[1], argv[2], [int(x) for x in argv[3].split(",")]
    for p in pages:
        s, _recs = summarize(plate, [p], workdir, slicedir)
        print("== %s p%d" % (plate, p))
        for k, v in s.items():
            print("  %-48s %s" % (k, v))
    s, recs = summarize(plate, pages, workdir, slicedir)
    if jout:
        json.dump(dict(summary=s, runs=recs), open(jout, "w"), indent=1, default=str)
