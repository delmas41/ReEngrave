"""ROADMAP 2.290 build -- every verdict in one cell whose quantity matches, ADJUDICATE replayed on a gathered record with the env given (READ-ONLY).

    PYTHONPATH=. [OMR_...=1] python3 benchmarks/page-heads-ledger-2026-11/cell_verdicts.py REC CELLPREFIX QUANTITY_SUBSTR [...]
"""
import json
import os
import sys

os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")


def main(path, cell, subs):
    from tools.omr.staged.review import rerun as RR
    d = json.load(open(path))
    rec = d.get("record", d)
    log, _ = RR.rebuild_gather({"observations": rec["observations"], "abstentions": rec.get("abstentions") or [], "verdicts": []})
    RR.run_stages(log)
    vs = log.to_json()["verdicts"]
    boxes = {o["subject"]: (o["value"][0] if isinstance(o["value"], list) else o["value"]) for o in rec["observations"] if o.get("quantity") == "glyph_box"}
    for v in vs:
        s = v.get("subject", "")
        if not s.startswith("glyph/" + cell + "/") and s != "cell/" + cell:
            continue
        if any(x in v["quantity"] for x in subs):
            print(s, boxes.get(s), v["quantity"], v.get("outcome"), json.dumps(v.get("value"), default=str)[:120], v.get("reason"),
                  json.dumps(v.get("detail"), default=str)[:400])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
