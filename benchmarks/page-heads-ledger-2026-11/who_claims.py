"""ROADMAP 2.290 build -- which page head claims given cell strokes (READ-ONLY; re-runs only the stroke owner of one cell).

    PYTHONPATH=. OMR_PAGE_HEAD_ONE=1 OMR_PAGE_HEAD_LEDGER=1 python3 benchmarks/page-heads-ledger-2026-11/who_claims.py REC CELLKEY ORD [ORD ...]
"""
import json
import sys


def main(path, cell_key, ords):
    from tools.omr.staged.review import rerun as RR
    from tools.omr.staged.adjudicate import Evidence, REGISTRY
    from tools.omr.staged.record import Q, Subject
    from tools.omr.staged.adjudicators import stroke_owner as A
    d = json.load(open(path))
    rec = d.get("record", d)
    log, _ = RR.rebuild_gather({"observations": rec["observations"], "abstentions": rec.get("abstentions") or [], "verdicts": []})
    log.freeze() if hasattr(log, "freeze") else None
    cell = Subject.from_key(cell_key)
    ev = Evidence(log, cell, REGISTRY[Q.STROKE_OWNER])
    view = A._cell_view(ev, cell)
    rows = {r.id: r for r in log.rows(Q.CLAIMED_AREA, Subject.from_key("page/%d" % cell.page))}
    by = {i.ordinal: i for i in view["inks"]}
    for o in ords:
        ink = by.get(o)
        print("stroke", o, ink.kind if ink else None, [round(v) for v in view["page"].get(o, ())], "link", A._links(ev, cell).get(o))
        for c in view["claims"]:
            if o in c.covers:
                extra = ""
                if c.members:
                    r = rows.get(c.row_id)
                    dd = r.detail if r is not None else {}
                    extra = "rep %s oval %s page_strokes %s members %s" % (dd.get("rep"), dd.get("oval"), dd.get("page_strokes"), dd.get("members"))
                print("   ", c.key, c.family, c.cls, extra)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3:]])
