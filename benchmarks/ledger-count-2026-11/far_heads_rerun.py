"""ROADMAP 2.312 Part 0 -- per far head: what the ledger count said, what pitch was written, and whether it was written blue.

    PYTHONPATH=. python3 benchmarks/ledger-count-2026-11/far_heads_rerun.py PLATE OUT.json [ENV=VAL ...]

STAGED. Re-adjudicates the SAVED GATHER rows of the 2306 frozen-sample slices (`library/_shared-records/claim-readout-slices-2306-smp4-{lit,bra}`;
Litolff pages 1 2 4 6 8 9 10 11 16, Brahms 0 4 5 8 12 14 19 25) through ADJUDICATE..EVALUATE..INFER and the exporter, in this process (no detector,
no OCR). Per glyph that has a notehead class and a staff position: the geometry position, the far-head ledger verdict (decided value or abstention
reason word), the live PITCH verdict (value, reason, whether it is the far-unread guess), and the written note at the glyph (pitch, blue or plain).
"""
from __future__ import annotations

import collections
import json
import os
import sys

from tools.omr.staged.lane_report import RECORDS, glyph_boxes, load_slices, parse_symbols
from tools.omr.staged.record import READERS, Kind, Q

SLICE = {"litolff": RECORDS / "claim-readout-slices-2306-smp4-lit", "brahms": RECORDS / "claim-readout-slices-2306-smp4-bra"}


def main(plate, out, envs):
    for e in envs:
        k, v = e.split("=", 1)
        os.environ[k] = v
    from tools.omr.staged import export as E
    from tools.omr.staged.review import rerun as RR

    rec = load_slices(SLICE[plate])
    pages = os.environ.get("PAGES")      # e.g. PAGES=8,10: only those pages (+ document rows); the loaded machine cannot hold a whole plate
    if pages:
        from tools.omr.staged.lane_report import page_of
        keep_pg = {int(v) for v in pages.split(",")}
        for k in ("observations", "abstentions", "verdicts"):
            rec[k] = [r for r in rec[k] if page_of(r.get("subject")) is None or page_of(r.get("subject")) in keep_pg]
    boxes = glyph_boxes(rec["observations"])
    # the 2306 slices were gathered on lane 2.306, whose `page_stem` rows main does not know (flag OMR_PAGE_STEMS, OFF): left out, counted
    unknown = collections.Counter()
    import re
    idre = re.compile(r"\b(?:obs|abs):\d+")
    dropped_ids = set()
    for k in ("observations", "abstentions"):
        keep = []
        for r in rec[k]:
            try:
                Q.check(r["quantity"], "quantity")
                READERS.check(r["reader"], "reader")
                keep.append(r)
            except ValueError:
                unknown[r["quantity"] + "/" + str(r["reader"])] += 1
                dropped_ids.add(r["id"])
        rec[k] = keep
    while True:        # a row that names a dropped row cannot be replayed either
        changed = False
        for k in ("observations", "abstentions"):
            keep = []
            for r in rec[k]:
                refs = set(idre.findall(json.dumps([r.get("detail"), r.get("value"), r.get("basis")], default=str)))
                if refs & dropped_ids:
                    unknown["(names a dropped row) " + r["quantity"]] += 1
                    dropped_ids.add(r["id"])
                    changed = True
                else:
                    keep.append(r)
            rec[k] = keep
        if not changed:
            break
    print("rows of quantities main does not know, dropped:", dict(unknown))
    rec["verdicts"] = []
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    result = {"record": log.to_json(), "summary": log.summary()}
    from tools.omr.staged.lane_report import traced_export
    with traced_export():
        xml, _rep, refusals, _placed = RR.export_with_subjects(result)
    json.dump(dict(refusals=refusals, notes_not_written=_rep.get("notes_not_written"), notes_not_written_total=_rep.get("notes_not_written_total"),
                   bars_written_red=_rep.get("bars_written_red"), bars_held_out=_rep.get("bars_held_out_sum")), open(out + ".export.json", "w"), default=str)
    sym = parse_symbols(xml, boxes)
    written = {h["rg"]: h for h in sym["hosts"] if h.get("rg")}
    heads = []
    for sub in log.subjects(Kind.GLYPH):
        key = sub.to_key()
        cls = log.rows(Q.NOTEHEAD_CLASS, sub)
        pos = log.rows(Q.NOTEHEAD_STAFF_POSITION, sub)
        if not cls or not pos:
            continue
        gb = log.rows(Q.GLYPH_BOX, sub)
        led = log.rows(Q.FAR_HEAD_LEDGER_POSITION, sub)
        ledref = log.refusals(Q.FAR_HEAD_LEDGER_POSITION, sub)
        fv = log.verdict(Q.NOTEHEAD_POSITION, sub)
        pv = log.verdict(Q.PITCH, sub)
        nn = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, sub)
        keep = ("ledger_reason", "box_source", "shape_source", "geometry_position")
        d = dict(key=key, cls=cls[-1].value, geom=float(pos[-1].value),
                 box=(gb[-1].detail or {}).get("bbox_page_px") if gb else None,
                 ledger_row=(None if not led else float(led[-1].value)),
                 ledger_detail=(None if not led else {k: v for k, v in (led[-1].detail or {}).items() if k in keep}),
                 ledger_refusal=(None if not ledref else dict(reason=ledref[-1].reason,
                                                              detail={k: v for k, v in (ledref[-1].detail or {}).items() if k in keep})),
                 far_verdict=(None if fv is None else dict(outcome=str(fv.outcome), value=fv.value, reason=fv.reason)),
                 pitch=(None if pv is None else dict(outcome=str(pv.outcome), value=pv.value, reason=pv.reason, decider=pv.decider)),
                 not_a_note=(None if nn is None else (str(nn.outcome), nn.value, nn.reason)))
        w = written.get(key)
        d["written"] = None if w is None else dict(pitch=w["pitch"], blue=w["blue"], type=w["type"])
        heads.append(d)
    json.dump(heads, open(out, "w"), default=str)
    print(plate, len(heads), "heads;", sum(1 for h in heads if h["written"]), "written")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
