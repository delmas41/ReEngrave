"""Replay ADJUDICATE (through tie_pair) over a saved GATHER record on the
CURRENT tree and dump one row per arc.

usage: PYTHONPATH=<tree> python3 replay.py record.json out.json
Rows: sub, det (detector class), kind, reason, rule info, refused.
The control (an unchanged tree) must give the record's own arc_kind values.
"""
import json
import sys
import time

from tools.omr.staged import adjudicate, adjudicators, consequences  # noqa: F401
from tools.omr.staged import record_io
from tools.omr.staged.record import Q
from tools.omr.staged.review.rerun import rebuild_gather


def main(src, dst):
    t0 = time.time()
    rec = record_io.load_record(src)["record"]
    log, _ids = rebuild_gather(rec)
    log.freeze()
    order = list(adjudicate.ORDER)
    stop = order.index(Q.TIE_PAIR) + 1
    adjudicate.run(log, order=order[:stop])
    rows = []
    for o in rec["observations"]:
        if o["quantity"] != "arc_box":
            continue
        sub = o["subject"]
        from tools.omr.staged.record import Subject
        s = Subject.from_key(sub)
        v = log.verdict(Q.ARC_KIND, s)
        nv = log.verdict(Q.ARC_IS_NOT_AN_ARC, s)
        tp = log.verdict(Q.TIE_PAIR, s)
        row = dict(sub=sub, det=o["value"], box=o["detail"].get("bbox_page_px"),
                   refused=bool(nv is not None and nv.outcome.value == "decided" and nv.value is True),
                   kind=(v.value if v is not None and v.outcome.value == "decided" else None),
                   outcome=None if v is None else v.outcome.value,
                   reason=None if v is None else v.reason,
                   tie_pair=None if tp is None else (tp.outcome.value, tp.reason))
        if v is not None:
            g = (v.detail or {}).get("grammar") or {}
            row["rule"] = g.get("tie_slur_rule")
            row["grammar_says"] = g.get("says")
        rows.append(row)
    json.dump(rows, open(dst, "w"))
    print("arcs", len(rows), "seconds", round(time.time() - t0))


main(sys.argv[1], sys.argv[2])
