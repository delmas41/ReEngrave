"""ROADMAP 2.205 (read-only): how many of 2.204's `disagree` stem abstentions does ONE OWNER PER STROKE remove?

usage: stem_disagree_owner.py REPORT_OUT_DIR OUT.json
   REPORT_OUT_DIR = a lane_report out dir whose two arms both ran OMR_STEMS_FROM_STROKES and differ by OMR_STROKE_OWNER (run (b) of FINDINGS 2.205).

Streams each arm's mini-record (`duration` verdicts carry `detail.stems_from_strokes.settled`) and pairs the heads: per plate, the settled kinds in
each arm, and for every head OFF settled `disagree`: what it became ON (gone to `agrees` / `gained` / `old_refused` / ..., or still `disagree`)."""
import collections
import json
import pathlib
import sys

import ijson


def settled(path):
    out = {}
    with open(path, "rb") as f:
        for v in ijson.items(f, "verdicts.item", use_float=True):
            if v["quantity"] != "duration" or v.get("supersedes"):
                continue
            s = ((v.get("detail") or {}).get("stems_from_strokes") or {})
            if s:
                out[v["subject"]] = (s.get("settled"), s.get("disagree"), v.get("outcome"), v.get("reason"))
    return out


def main():
    rep = pathlib.Path(sys.argv[1])
    res = {}
    for plate in ("litolff", "brahms"):
        off = settled(rep / "work" / ("%s.off.mini-record.json" % plate))
        on = settled(rep / "work" / ("%s.on.mini-record.json" % plate))
        became = collections.Counter()
        why_off = collections.Counter()
        new_dis = []
        for k, (s, why, _o, _r) in off.items():
            if s == "disagree":
                why_off[str(why)] += 1
                became[str(on.get(k, (None,))[0])] += 1
        for k, (s, why, _o, _r) in on.items():
            if s == "disagree" and off.get(k, (None,))[0] != "disagree":
                new_dis.append([k, why])
        res[plate] = {"off": dict(collections.Counter(v[0] for v in off.values())), "on": dict(collections.Counter(v[0] for v in on.values())),
                      "off_disagree_why": dict(why_off), "off_disagree_became_on": dict(became),
                      "new_disagree_on": len(new_dis), "new_disagree_examples": new_dis[:20]}
        print(plate, "OFF disagree", sum(why_off.values()), "-> ON", dict(became), "| new ON disagree", len(new_dis))
    json.dump(res, open(sys.argv[2], "w"), indent=1)


if __name__ == "__main__":
    main()
