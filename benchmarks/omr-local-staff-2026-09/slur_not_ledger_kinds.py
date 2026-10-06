"""lane-slur-not-ledger: which refusal kind lies behind each changed decision (read of the OOS json), with geometry agreement.
python3 slur_not_ledger_kinds.py oos_lito.json oos_brah.json"""
import collections, json, sys

rows = []
for p in sys.argv[1:]:
    rows += [r for r in json.load(open(p))["rows"] if r["repro"]]
c, agree = collections.Counter(), collections.Counter()
for r in rows:
    if r["off"]["pos"] != r["on"]["pos"]:
        kinds = sorted({x["why"].replace("not_straight_short_level_", "") for x in (r["on"]["refused"] or [])
                        if "not_straight" in x["why"] or "arc_box" in x["why"]})
        k = "+".join(kinds) or "(gap-found rung only)"
        c[k] += 1
        agree[k] += int(r["off"]["pos"] == r["geo"])
for k, n in c.most_common():
    print(f"{n:4d} changed; before-position agreed with geometry on {agree[k]:4d}  | {k}")
