"""ROADMAP 2.290 r1 -- READ-ONLY: what happens to every detector HEAD box on a saved gather, on today's ADJUDICATE..EXPORT.

    python3 benchmarks/page-heads-ledger-2026-11/replay_head_fates.py SLICES_DIR PLATE PAGES OUT.json

SLICES_DIR holds `<plate>/{observations,abstentions}.jsonl` (lane_report slices). Reuses `conservation.load_pages`, replays ADJUDICATE..EXPORT on the
tree's defaults, and captures `export._place_notes`' own `fates` out-param (the written / refusal reason of every notehead and rest box). Joins each
notehead box to its `Q.GLYPH_BOX` row (cell, page box, class, confidence) and its `Q.MARK_GROUP` (twin boxes). Writes one row per notehead box.
No code under tools/ is edited, no detector, no OCR, no gather.
"""
from __future__ import annotations

import collections
import json
import os
import sys
import time

os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")


def main(slices: str, plate: str, pages: list, out_path: str) -> None:
    from tools.omr.staged import conservation as C
    from tools.omr.staged import export as E
    from tools.omr.staged.review import rerun as RR
    from tools.omr.staged.record import Q
    rec = C.load_pages(plate, pages, slices)
    t0 = time.time()
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    result = {"record": log.to_json(), "summary": log.summary()}
    grabbed = {}
    orig = E._place_notes

    def spy(*a, **kw):
        grabbed["fates"] = kw.get("fates")
        return orig(*a, **kw)
    E._place_notes = spy
    try:
        xml, report = E.to_musicxml(result)
    finally:
        E._place_notes = orig
    fates = grabbed["fates"] or {}
    obs = result["record"]["observations"]
    boxes, groups = {}, {}
    for o in obs:
        q = o["quantity"]
        if q == Q.GLYPH_BOX:
            d = o.get("detail") or {}
            boxes[o["subject"]] = dict(box=d.get("bbox_page_px"), cat=d.get("category"), cls=d.get("smufl_name") or d.get("class") or o.get("value"),
                                       conf=o.get("score"))
        elif q == Q.MARK_GROUP:
            groups[o["subject"]] = (o["value"], (o.get("detail") or {}).get("size"))
    rows = []
    for sub, why in fates.items():
        b = boxes.get(sub)
        if not b or b["cat"] != "notehead":
            continue
        g = groups.get(sub, (None, 1))
        rows.append(dict(sub=sub, fate=why, group=g[0], group_size=g[1], **b))
    cnt = collections.Counter(r["fate"] for r in rows)
    json.dump(dict(plate=plate, pages=pages, seconds=round(time.time() - t0, 1), n_heads=len(rows), by_fate=dict(cnt), rows=rows,
                   marks_census=report.get("marks_census"), conservation=report.get("conservation")), open(out_path, "w"), default=str)
    print(plate, pages, "heads", len(rows), dict(cnt.most_common()))
    mc = (report.get("marks_census") or {}).get("notehead")
    print("marks_census notehead:", mc)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3].split(",")], sys.argv[4])
