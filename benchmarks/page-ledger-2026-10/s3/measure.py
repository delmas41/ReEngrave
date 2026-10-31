"""2.240 step 2 round 2 measure: what the ledger-evidence filter, the hairpin witness and the arc owner change, per plate, from two gathered records
(OFF = OMR_PAGE_OWNER off: the plain ledger readings; ON = on: filtered readings).

    OMR_SPLIT_JOINS=<as gathered> python3 benchmarks/page-ledger-2026-10/s3/measure.py PLATE OFF.record.json ON.record.json [--cell-map master] [--tiles DIR]

Three owner arms over the SAME page marks: O = OFF record's rows, no hairpin witness (round 1's behaviour); F = ON record's rows (filtered ledger
evidence), no hairpin; H = ON rows + the hairpin witness (the whole of round 2). Prints counts; writes s3/<plate>.json.
"""
import argparse
import collections
import json
import pathlib
import sys

from tools.omr.staged import cell_map as CM
from tools.omr.staged import claim_readout as CR
from tools.omr.staged import page_marks as PM
from tools.omr.staged import page_owner as PO

OUT = pathlib.Path(__file__).parent


def filter_rows(record):
    """Every owner-ledger row of the ON record that dropped a rung: by word, and whether the reading changed."""
    by_word, changed, rows = collections.Counter(), [], 0
    src = CR.resolve_source(str(record))
    if not (src / "observations.jsonl").exists():
        return {"owner_ledger_rows": 0, "rows_that_dropped_a_rung": 0, "rungs_dropped_by_word": {}, "readings_changed": 0, "rows": []}
    for kind in ("observations", "abstentions"):
        for line in open(src / ("%s.jsonl" % kind)):
            if '"far_head_owner_ledger"' not in line:
                continue
            o = json.loads(line)
            if o.get("quantity") != "far_head_owner_ledger":
                continue
            d = o.get("detail") or {}
            rows += 1
            drop = d.get("not_ledger_dropped") or []
            if not drop:
                continue
            for _y, w in drop:
                by_word[w] += 1
            fits = kind == "observations"
            pos = o.get("value") if fits else None
            changed.append({"subject": o["subject"], "candidate": d.get("candidate"), "dropped": drop, "fits_now": fits, "pos_now": pos,
                            "fits_before": d.get("unfiltered_fits"), "pos_before": d.get("unfiltered_pos"),
                            "reading_changed": (fits != bool(d.get("unfiltered_fits"))) or (fits and pos != d.get("unfiltered_pos"))})
    return {"owner_ledger_rows": rows, "rows_that_dropped_a_rung": len(changed), "rungs_dropped_by_word": dict(by_word),
            "readings_changed": sum(1 for c in changed if c["reading_changed"]), "rows": changed}


def arms(record, pages, cm_root, pdf, arm_hairpin):
    """{members[0]: owner dict} per page mark over the record's pages, with / without the hairpin witness; plus the spans."""
    src = CR.resolve_source(str(record))
    rows_all = CR.read_rows(src, pages)
    res, spans_all = {}, {}
    for pg in pages:
        prows = {k: [r for r in v if CR.page_of_subject(r.get("subject", "")) in (None, pg)] for k, v in rows_all.items()}
        pws, cells, local, views, _v = PM.page_views(prows, pdf, pg, cm_root)
        ink = pws.page.binary == 0
        boxes = PM.boxes_from_rows(prows, pg, cells, local, views, ink)
        marks = PM.link(boxes, pieces=True)
        frames = PO.staff_frames(cells, local)
        sp = PO.page_spans(marks, boxes, PO._rows_of(prows, "system_arc"), PO._rows_of(prows, "wedge_box"))
        own = PO.owners(marks, boxes, frames, PO.SliceRows(prows), PO.hairpin_boxes(sp["spans"]) if arm_hairpin else ())
        PO.assign_arc_owners(sp["spans"], own, frames)
        for r in own.values():
            res[r["members"][0]] = dict(page=pg, family=r["family"], status=r["status"], owner=r["owner"], reason=r["reason"], box=r["box"],
                                        candidates=r["candidates"], members=r["members"], seen_from=r["seen_from"])
        spans_all[pg] = sp["spans"]
        del pws, cells, views, ink
    return res, spans_all


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plate")
    ap.add_argument("off")
    ap.add_argument("on")
    ap.add_argument("--pages", default=None)
    ap.add_argument("--cell-map", default=None)
    a = ap.parse_args()
    cm = pathlib.Path(a.cell_map) if a.cell_map else CM.ROOT_DEFAULT
    src = CR.resolve_source(a.on)
    pages = [int(p) for p in a.pages.split(",")] if a.pages else CR.slice_pages(src)
    pdf = CR.LIB / CR.edition_info(CR.read_rows(src, pages))["edition_path"]
    rep = {"plate": a.plate, "pages": pages, "filter": filter_rows(a.on)}
    O, _ = arms(a.off, pages, cm, pdf, False)
    F, _ = arms(a.on, pages, cm, pdf, False)
    H, spans = arms(a.on, pages, cm, pdf, True)
    heads = [k for k, v in O.items() if v["family"] == "head"]

    def diff(X, Y, only_heads=True):
        out = []
        for k in (heads if only_heads else X):
            x, y = X.get(k), Y.get(k)
            if x and y and (x["owner"], x["status"]) != (y["owner"], y["status"]):
                out.append({"key": k, "page": x["page"], "before": [x["status"], x["owner"], x["reason"]],
                            "after": [y["status"], y["owner"], y["reason"]], "box": y["box"], "seen_from": y["seen_from"]})
        return out
    rep["owners_changed_by_filter"] = diff(O, F)
    rep["owners_changed_by_hairpin"] = diff(F, H)
    rep["heads"] = len(heads)
    rep["head_status_O"] = dict(collections.Counter("%s:%s" % (O[k]["status"], O[k]["reason"]) for k in heads))
    rep["head_status_H"] = dict(collections.Counter("%s:%s" % (H[k]["status"], H[k]["reason"]) for k in heads if k in H))
    rep["hairpin_disagreements"] = [{"key": k, "page": H[k]["page"], "candidates": H[k]["candidates"], "box": H[k]["box"]}
                                    for k in heads if k in H and H[k]["reason"] == "hairpin_disagrees"]
    arc_rows = []
    for pg, sps in spans.items():
        for s in sps:
            if s["kind"] != "arc":
                continue
            ow = s.get("owner") or {}
            arc_rows.append({"page": pg, "box": s["box"], "seen_from": s["staves_seen_from"], "status": ow.get("status"), "owner": ow.get("owner"),
                             "reason": ow.get("reason"), "differs": bool(ow.get("owner") and ow["owner"] not in s["staves_seen_from"]),
                             "ends": ow.get("ends"), "views": s["views"], "crosses_barline": s["crosses_barline"]})
    rep["arcs"] = {"n": len(arc_rows), "by_status_reason": dict(collections.Counter("%s:%s" % (r["status"], r["reason"]) for r in arc_rows)),
                   "owner_not_a_seen_from_staff": sum(1 for r in arc_rows if r["differs"]), "rows": arc_rows}
    print("%s pages %s: heads %d | filter dropped rungs %s in %d owner-ledger rows (%d readings changed) | head owners changed by filter %d, by hairpin %d "
          "(hairpin disagrees %d) | arcs %d %s, owner on a staff the arc was not seen from %d" % (
              a.plate, pages, rep["heads"], rep["filter"]["rungs_dropped_by_word"], rep["filter"]["rows_that_dropped_a_rung"],
              rep["filter"]["readings_changed"], len(rep["owners_changed_by_filter"]), len(rep["owners_changed_by_hairpin"]),
              len(rep["hairpin_disagreements"]), rep["arcs"]["n"], rep["arcs"]["by_status_reason"], rep["arcs"]["owner_not_a_seen_from_staff"]))
    (OUT / ("measure_%s.json" % a.plate)).write_text(json.dumps(rep, indent=1, default=str))


if __name__ == "__main__":
    sys.exit(main())
