"""overnight 2026-10-04 re-gathers, step 1: pull the far-head facts out of a record into a small JSON.

READ ONLY on the record (loaded via `record_io.load_record`, one at a time, freed on exit). Writes only to the
output path given.

  python3 overnight_1004_extract.py <record.json> <out.json>

Per glyph subject keeps: geometry position (Q.NOTEHEAD_STAFF_POSITION), the detector box in page px, the notehead
class, the far-head ledger row (value + detail) or abstention (reason), and the standing Q.NOTEHEAD_POSITION
verdict (outcome/value/reason). Per staff: Q.STAFF_LINES.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from tools.omr.staged.record_io import load_record
from tools.omr.staged.record import Q


def main(src, dst):
    res = load_record(src)
    rec = res["record"]
    superseded = {v["supersedes"] for v in rec["verdicts"] if v.get("supersedes")}
    stand = {}
    for v in rec["verdicts"]:
        if v["quantity"] != Q.NOTEHEAD_POSITION or v["id"] in superseded:
            continue
        stand[v["subject"]] = dict(outcome=v["outcome"], value=v.get("value"), reason=v.get("reason"),
                                   detail=v.get("detail"))
    g = {}
    staff_lines = {}
    boxes = []   # every detection (subject, class, page-px box): the replay's page_boxes
    for o in rec["observations"]:
        q = o["quantity"]
        if q == Q.NOTEHEAD_STAFF_POSITION:
            d = g.setdefault(o["subject"], {})
            d["geo"] = o["value"]
            d["geo_rounded"] = (o.get("detail") or {}).get("rounded")
        elif q == Q.GLYPH_BOX:
            pb = (o.get("detail") or {}).get("bbox_page_px")
            if pb:
                g.setdefault(o["subject"], {})["box"] = [float(x) for x in pb]
                if o.get("value"):
                    boxes.append([o["subject"], o["value"][0], [float(x) for x in pb]])
        elif q == Q.NOTEHEAD_CLASS:
            g.setdefault(o["subject"], {})["cls"] = o["value"]
        elif q == Q.FAR_HEAD_LEDGER_POSITION:
            d = o.get("detail") or {}
            g.setdefault(o["subject"], {})["fh"] = dict(
                value=o["value"], ledger_reason=d.get("ledger_reason"), box_source=d.get("box_source"),
                shape_source=d.get("shape_source"), geometry_position=d.get("geometry_position"))
        elif q == Q.STAFF_LINES:
            staff_lines[o["subject"]] = [float(y) for y in o["value"]]
    for a in rec["abstentions"]:
        if a["quantity"] == Q.FAR_HEAD_LEDGER_POSITION:
            d = a.get("detail") or {}
            g.setdefault(a["subject"], {})["fh_abs"] = dict(
                reason=a["reason"], ledger_reason=d.get("ledger_reason"), geometry_position=d.get("geometry_position"))
    keep = {s: v for s, v in g.items() if "geo" in v or "fh" in v or "fh_abs" in v}
    for s, v in stand.items():
        keep.setdefault(s, {})["np"] = v
    out = dict(src=str(src), provenance=res.get("provenance"), glyphs=keep, staff_lines=staff_lines, boxes=boxes)
    Path(dst).write_text(json.dumps(out))
    print(dst, "glyphs", len(keep), "staves", len(staff_lines), "far-head obs",
          sum(1 for v in keep.values() if "fh" in v), "abs", sum(1 for v in keep.values() if "fh_abs" in v))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
