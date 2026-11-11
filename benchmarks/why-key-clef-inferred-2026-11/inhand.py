"""For each FILLED key: was the printed count already IN HAND on that very staff-system (same raster, so not an independent witness -- a question about
labelling vs reading)?  A fill has the count in hand if ANY of: the staff's own marker read == fill; the GATHER key object's own_slots == |fill| (kind
flat); a header reader on the staff (cv_header / template) gave fill.   python3 inhand.py CLS.json X.json [X.json ...]
"""
import collections
import json
import sys

cls = json.load(open(sys.argv[1]))
byk = {(r["src"], r["staff"]): r for r in cls["keys"]}
tot = collections.Counter()
for path in sys.argv[2:]:
    d = json.load(open(path))
    for k, v in d["staffs"].items():
        r = byk.get((path, k))
        if r is None:
            continue
        p = v["key"][-1].get("detail") or {}
        fill = r["fill"]
        wit = []
        if r["staff_read"] is not None and r["staff_read"] == fill:
            wit.append("own marker read")
        if r["own_slots"] is not None and fill != 0 and r["own_slots"] == abs(fill) and not r["more_than_system"]:
            wit.append("key object own_slots")
        for x in p.get("disagreeing_readers", []):
            if x["fifths"] == fill:
                wit.append("reader " + x["reader"])
        key = "in hand" if wit else "not in hand"
        tot[(key, r["blue_key"] > 0)] += 1
        tot[("notes", key)] += r["blue_key"]
        for w in wit:
            tot[("via", w)] += 1
        r["in_hand"] = wit
print(dict(tot))
json.dump(byk and {"%s|%s" % k: v.get("in_hand") for k, v in byk.items()}, open(sys.argv[1].replace(".json", "_inhand.json"), "w"))
