"""ROADMAP 2.312: are far-head fallback notes written (and blue) in the exported file?  python3 written_check.py HEADS.json  (a far_heads_rerun.py file made WITH the traced export)"""
import collections, json, sys
hs = json.load(open(sys.argv[1]))
c = collections.Counter()
for h in hs:
    g = int(round(h["geom"]))
    if not (g <= -2 or g >= 10) or h["ledger_row"] is not None:
        continue
    r = (h["pitch"] or {}).get("reason")
    if r in ("reowned", "reowned_by_ledger_reading"):
        continue
    nan = h["not_a_note"]
    w = h["written"]
    c[(r, "refused as head" if nan and nan[1] is True else "head", "written blue" if w and w["blue"] else "written plain" if w else "NOT written")] += 1
for k, v in sorted(c.items(), key=lambda x: -x[1]):
    print(v, k)
