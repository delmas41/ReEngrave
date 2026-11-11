"""ROADMAP 2.290 r1 -- the three M6 flags OFF vs ON on today's tree, one page, same gather settings: per head box, did its export fate change?

    PYTHONPATH=. python3 benchmarks/page-heads-ledger-2026-11/arm_diff.py OFF.record.json ON.record.json PAGE OUT.json

Both records are `--through adjudicate` gathers of the same page (same cell map, same detector cache, same tree; only OMR_PAGE_HEADS / _HEAD_VIEWS / _HEAD_CLAIM differ). Each is
run through the rest of the pipeline exactly as `conservation.export_pages` does, `export._place_notes`'s `fates` are captured, and every notehead box's fate (written or
the refusal reason) is compared BY GLYPH KEY (the same gather's detector order: the boxes are identical in the two arms because the flags act after the detector; the script
checks that). Also prints the exported `<note>` count, and the page-head census row of the ON arm.
"""
import collections
import json
import os
import sys

os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")


def arm(path):
    from tools.omr.staged import export as E
    from tools.omr.staged.review import rerun as RR
    from tools.omr.staged.record import Q
    rec = json.load(open(path))
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
    boxes, census, ph_rows = {}, None, 0
    for o in result["record"]["observations"]:
        if o["quantity"] == Q.GLYPH_BOX and (o.get("detail") or {}).get("category") == "notehead":
            boxes[o["subject"]] = (o.get("detail") or {}).get("bbox_page_px")
        if o["quantity"] == Q.PAGE_HEAD:
            ph_rows += 1
            if o["value"] == "census":
                census = o.get("detail")
    return dict(fates=grabbed["fates"] or {}, boxes=boxes, notes=xml.count("<note"), census=census, page_head_rows=ph_rows, blue=xml.count("#1F6FEB"))


def main(off, on, page, out):
    a, b = arm(off), arm(on)
    same_boxes = a["boxes"] == b["boxes"]
    ch = collections.Counter()
    rows = []
    for k in sorted(set(a["boxes"]) | set(b["boxes"])):
        fa, fb = a["fates"].get(k), b["fates"].get(k)
        if fa != fb:
            ch[(fa, fb)] += 1
            rows.append(dict(sub=k, off=fa, on=fb, box=b["boxes"].get(k) or a["boxes"].get(k)))
    print("page", page, "| same boxes in both arms:", same_boxes, "| head boxes", len(a["boxes"]))
    print("exported <note> OFF %d ON %d | blue marks OFF %d ON %d | Q.PAGE_HEAD rows OFF %d ON %d" % (a["notes"], b["notes"], a["blue"], b["blue"], a["page_head_rows"], b["page_head_rows"]))
    print("head boxes whose export fate changed:", sum(ch.values()))
    for (fa, fb), n in ch.most_common():
        print("  %4d  %s  ->  %s" % (n, fa, fb))
    json.dump(dict(rows=rows, off=dict(notes=a["notes"]), on=dict(notes=b["notes"], census=b["census"])), open(out, "w"), default=str)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
