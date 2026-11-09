"""results.json: the census in one file -- per hand box (153) and per printed arc (109), bucket OFF and ON, plus the tallies (strict scorer, audited scorer)."""
import json
import collections
from load import *  # noqa

C = json.load(open("buckets.json"))
truth = json.load(open(S.TRUTH))
byid = {b["id"]: b for b in truth["boxes"]}
boxes = []
for c in C:
    p = printed()[0][c["n"]]
    for i in p["ids"]:
        b = byid[i]
        boxes.append(dict(hand_id=i, cell=b["cell_id"], cls=b["cls"], origin=b["origin"], printed_arc=c["n"], bucket_off=c["bucket_off"], bucket_on=c["bucket_on"]))
arcs = [{k: c[k] for k in ("n", "staff", "kind", "x0", "x1", "width_sp", "hand_boxes", "strict_off", "strict_on", "aud_off", "aud_on", "bucket_off", "why_off", "bucket_on", "why_on", "box_cov", "run_cov", "open_L", "open_R", "ghost", "chain")} for c in C]
tally = {}
for arm in ("off", "on"):
    tally[arm] = dict(printed_arcs=dict(sorted(collections.Counter(c["bucket_" + arm] for c in C).items())),
                      hand_boxes=dict(sorted(collections.Counter(b["bucket_" + arm] for b in boxes).items())),
                      strict_right=sum(1 for c in C if c["strict_" + arm] == "right"), audited_or_strict_right=sum(1 for c in C if c["bucket_" + arm] == "right"))
json.dump(dict(tally=tally, arcs=arcs, hand_boxes=boxes), open("results.json", "w"), indent=1)
print(json.dumps(tally, indent=1))
print(len(boxes), "hand boxes;", len(arcs), "printed arcs")
print("ON bucket members:", {b: [c["n"] for c in C if c["bucket_on"] == b] for b in sorted({c["bucket_on"] for c in C}) if b != "right"})
print("OFF bucket members:", {b: [c["n"] for c in C if c["bucket_off"] == b] for b in sorted({c["bucket_off"] for c in C}) if b != "right"})
print("ON lost vs OFF:", [c["n"] for c in C if c["bucket_off"] == "right" and c["bucket_on"] != "right"], "won:", [c["n"] for c in C if c["bucket_off"] != "right" and c["bucket_on"] == "right"])
