"""ROADMAP 2.165 -- the stem-value and duration verdicts of named glyphs in a replay's mini record (why a stem was held out).
usage: look_stems_2_165.py RECORD.json GLYPH [GLYPH ...]   (also prints every member the stem verdict names)"""
import json
import sys

import ijson

rec, want = sys.argv[1], set(sys.argv[2:])
stems, durs = {}, {}
with open(rec, "rb") as f:
    for v in ijson.items(f, "verdicts.item", use_float=True):
        if v["quantity"] == "stem_value":
            stems.setdefault(v["subject"], []).append(v)
        elif v["quantity"] == "duration":
            durs.setdefault(v["subject"], []).append(v)
for g in sorted(want):
    for s in stems.get(g, []):
        d = s.get("detail") or {}
        print(g, s["outcome"], s["reason"], "members", d.get("members"))
        print("   evidence", json.dumps(d.get("evidence"))[:600])
        for m in d.get("members") or []:
            for dv in durs.get(m, []):
                val = dv["value"] if isinstance(dv["value"], dict) else {}
                print("   ", m, dv["decider"], dv["reason"], dv["outcome"], val.get("written"), val.get("dots"),
                      val.get("beam_levels"), val.get("head_fill"))
