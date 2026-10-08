"""day 2026-10-07 read, step 1: ONE load_record of a record -> everything the day read needs, compact.
READ ONLY on the record (GATHER+ADJUDICATE only; no EVALUATE/INFER/EXPORT is run).

  python3 day_1007_extract.py <record.json> <out.json>

= night_1006_extract.from_result (per-glyph geo/box/class/far-head/position/owner/not-a-note, staff lines, clef, meter,
census) + `mark_group` {subject: [gid, category]} + `summary` + `allv` {"quantity|subject": [outcome, value<=160ch, reason]}
for every standing verdict + `arc_boxes` (subjects with a Q.ARC_BOX row) + `obs_count` {quantity: n rows}.
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import night_1006_extract as E6
from tools.omr.staged.record_io import load_record
from tools.omr.staged.record import Q


def main(src, dst):
    res = load_record(src)
    out = E6.from_result(res, src)
    rec = res["record"]
    mg, arcs, oc = {}, [], collections.Counter()
    for o in rec["observations"]:
        oc[o["quantity"]] += 1
        if o["quantity"] == Q.MARK_GROUP:
            mg[o["subject"]] = [o["value"], (o.get("detail") or {}).get("category")]
        elif o["quantity"] == Q.ARC_BOX:
            arcs.append(o["subject"])
    sup = {v["supersedes"] for v in rec["verdicts"] if v.get("supersedes")}
    allv = {}
    for v in rec["verdicts"]:
        if v["id"] in sup:
            continue
        allv[f'{v["quantity"]}|{v["subject"]}'] = [v["outcome"], json.dumps(v.get("value"), default=str)[:160], v.get("reason")]
    out.update(mark_group=mg, summary=res.get("summary"), allv=allv, arc_boxes=arcs, obs_count=dict(oc))
    Path(dst).write_text(json.dumps(out))
    print(dst, "glyphs", len(out["glyphs"]), "allv", len(allv), "arc_boxes", len(arcs), flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:3])
