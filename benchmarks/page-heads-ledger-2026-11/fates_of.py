"""ROADMAP 2.290 build -- the export fate (written / the refusal reason) of named glyphs on a gathered record, ADJUDICATE..EXPORT replayed on this tree
with the env given (READ-ONLY; no gather, no detector).

    OMR_PAGE_HEAD_ONE=1 OMR_PAGE_HEAD_LEDGER=1 python3 benchmarks/page-heads-ledger-2026-11/fates_of.py REC.gathered.record.json GLYPH [GLYPH ...]

Prints each glyph's fate and its verdicts for the head / rest deciders (`notehead_is_not_a_notehead`, `rest_is_not_a_rest`, `glyph_owner`, `duration`).
"""
import json
import os
import sys

os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")


def main(path, keys):
    from tools.omr.staged import export as E
    from tools.omr.staged.review import rerun as RR
    d = json.load(open(path))
    rec = d.get("record", d)
    log, _ = RR.rebuild_gather({"observations": rec["observations"], "abstentions": rec.get("abstentions") or [], "verdicts": []})
    RR.run_stages(log)
    result = {"record": log.to_json(), "summary": log.summary()}
    grabbed = {}
    orig = E._place_notes

    def spy(*a, **kw):
        grabbed["fates"] = kw.get("fates")
        return orig(*a, **kw)
    E._place_notes = spy
    try:
        E.to_musicxml(result)
    finally:
        E._place_notes = orig
    fates = grabbed.get("fates") or {}
    want = ("notehead_is_not_a_notehead", "rest_is_not_a_rest", "glyph_owner", "duration", "stroke_owner")
    vs = [v for v in result["record"]["verdicts"] if v.get("subject") in keys and v.get("quantity") in want]
    for k in keys:
        print(k, "fate:", fates.get(k))
        for v in vs:
            if v["subject"] == k:
                print("   ", v["quantity"], v.get("outcome"), v.get("value"), v.get("reason"), json.dumps(v.get("detail"), default=str)[:300])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
