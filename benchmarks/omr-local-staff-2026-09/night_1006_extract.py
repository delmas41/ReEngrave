"""night 2026-10-06 read, step 1: pull what the far-head / ownership / whole-record comparison needs out of ONE record.

READ ONLY on the record (loaded via `record_io.load_record`, one at a time, freed on exit).
  python3 night_1006_extract.py <record.json> <out.json>

Per glyph: geometry position, detector box, class, far-head row/abstention (+ledger_reason), standing
Q.NOTEHEAD_POSITION verdict, standing Q.GLYPH_OWNER verdict, standing Q.NOTEHEAD_IS_NOT_A_NOTEHEAD verdict.
Per staff: Q.STAFF_LINES + standing Q.CLEF verdict. Per system: standing Q.METER verdict. Census block: whole-record
counts (noteheads gathered, verdict outcomes by quantity) computed here so the page-level comparison needs no record.
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from tools.omr.staged.record_io import load_record
from tools.omr.staged.record import Q

CENSUS_Q = (Q.CLEF, Q.METER, Q.GLYPH_OWNER, Q.NOTEHEAD_POSITION, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD)


def main(src, dst):
    res = load_record(src)
    rec = res["record"]
    superseded = {v["supersedes"] for v in rec["verdicts"] if v.get("supersedes")}
    stand = collections.defaultdict(dict)       # quantity -> subject -> verdict
    census = {}
    for v in rec["verdicts"]:
        if v["id"] in superseded:
            continue
        if v["quantity"] in CENSUS_Q:
            stand[v["quantity"]][v["subject"]] = v
    for q in CENSUS_Q:
        c = collections.Counter(); r = collections.Counter()
        for s, v in stand[q].items():
            c[v["outcome"]] += 1
            r[f'{v["outcome"]}:{v.get("reason")}'] += 1
        census[q] = dict(outcome=dict(c), reason=dict(r))
    g = {}
    staff_lines, boxes = {}, []
    nh_class = set()
    for o in rec["observations"]:
        q = o["quantity"]
        if q == Q.NOTEHEAD_STAFF_POSITION:
            d = g.setdefault(o["subject"], {}); d["geo"] = o["value"]; d["geo_rounded"] = (o.get("detail") or {}).get("rounded")
        elif q == Q.GLYPH_BOX:
            pb = (o.get("detail") or {}).get("bbox_page_px")
            if pb:
                g.setdefault(o["subject"], {})["box"] = [float(x) for x in pb]
                if o.get("value"):
                    boxes.append([o["subject"], o["value"][0], [float(x) for x in pb]])
        elif q == Q.NOTEHEAD_CLASS:
            g.setdefault(o["subject"], {})["cls"] = o["value"]; nh_class.add(o["subject"])
        elif q == Q.FAR_HEAD_LEDGER_POSITION:
            d = o.get("detail") or {}
            g.setdefault(o["subject"], {})["fh"] = dict(value=o["value"], ledger_reason=d.get("ledger_reason"),
                box_source=d.get("box_source"), shape_source=d.get("shape_source"), geometry_position=d.get("geometry_position"))
        elif q == Q.STAFF_LINES:
            staff_lines[o["subject"]] = [float(y) for y in o["value"]]
    for a in rec["abstentions"]:
        if a["quantity"] == Q.FAR_HEAD_LEDGER_POSITION:
            d = a.get("detail") or {}
            g.setdefault(a["subject"], {})["fh_abs"] = dict(reason=a["reason"], ledger_reason=d.get("ledger_reason"),
                geometry_position=d.get("geometry_position"))
    for s, v in stand[Q.NOTEHEAD_POSITION].items():
        g.setdefault(s, {})["np"] = dict(outcome=v["outcome"], value=v.get("value"), reason=v.get("reason"), detail=v.get("detail"))
    for s, v in stand[Q.GLYPH_OWNER].items():
        g.setdefault(s, {})["own"] = dict(outcome=v["outcome"], value=v.get("value"), reason=v.get("reason"))
    for s, v in stand[Q.NOTEHEAD_IS_NOT_A_NOTEHEAD].items():
        g.setdefault(s, {})["nan"] = dict(outcome=v["outcome"], reason=v.get("reason"))
    keep = {s: v for s, v in g.items() if any(k in v for k in ("geo", "fh", "fh_abs", "np"))}
    census["noteheads_gathered"] = len(nh_class)
    clef = {s: dict(outcome=v["outcome"], value=v.get("value"), reason=v.get("reason")) for s, v in stand[Q.CLEF].items()}
    meter = {s: dict(outcome=v["outcome"], value=(v.get("value") or {}).get("raw") if isinstance(v.get("value"), dict) else v.get("value"),
                     reason=v.get("reason")) for s, v in stand[Q.METER].items()}
    out = dict(src=str(src), provenance=res.get("provenance"), glyphs=keep, staff_lines=staff_lines, boxes=boxes,
               census=census, clef=clef, meter=meter)
    Path(dst).write_text(json.dumps(out))
    print(dst, "glyphs", len(keep), "staves", len(staff_lines), "noteheads", len(nh_class))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
