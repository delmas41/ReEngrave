"""2.299: cut the REAL rows of Sean's 12 staff-start tiles (2.292 r1) out of a flag-OFF analyze.py run into data/tile_fixtures.json.
    PYTHONPATH=. python3 make_fixtures.py L9_off.json B04_off.json
Each fixture is what the reader is given on the real page: the staff's `system_key_object` row (read_pieces with their measured steps, the staff space,
the system count), its READ clef (None where the clef was unread), the standing key verdict ADJUDICATE reached, and Sean's own words for that tile.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ANS = os.path.join(HERE, "..", "why-key-clef-inferred-2026-11", "answers", "answers-2.292-r1.json")

runs = {}
for path in sys.argv[1:]:
    d = json.load(open(path))
    runs[d["plate"]] = d
ans = json.load(open(ANS))["answers"]
out = {}
for n, a in sorted(ans.items(), key=lambda kv: int(kv[0])):
    v = runs[a["plate"]]["staffs"][a["staff"]]
    row = None
    for r in v["evidence"].get("claimed_area", []):
        dt = r.get("detail")
        if isinstance(dt, dict) and dt.get("source") == "system_key_object" and dt.get("key_object"):
            row = {"ko": dt["key_object"], "space": dt.get("space_page_px")}
            break
    c = v["clef"][0] if v["clef"] else None
    clef = c["value"] if c and c["outcome"] == "decided" and not str(c.get("decider", "")).startswith("infer") else None
    k = v["key"][0]
    out[n] = {"plate": a["plate"], "staff": a["staff"], "sean_clef": a["sean_clef"], "sean_fifths": a["sean_fifths"], "bucket": a["bucket"],
              "clef_read": clef, "key_row": row,
              "adjudicate_key": {"decider": k["decider"], "outcome": k["outcome"], "value": k["value"], "reason": k.get("reason")}}
json.dump(out, open(os.path.join(HERE, "data", "tile_fixtures.json"), "w"), indent=1, default=str)
print("fixtures", len(out), "with a key object", sum(1 for f in out.values() if f["key_row"]))
