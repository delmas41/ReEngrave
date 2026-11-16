"""2.311 scratch: what a facts file holds (fates, verdict reasons, bar lists)."""
import collections
import json
import sys

f = json.load(open(sys.argv[1]))
g = f["glyphs"]
print("fates", collections.Counter(x["fate"] for x in g.values() if x["fate"]).most_common(40))
print("heads", sum(x["head"] for x in g.values()), "rests", sum(x["rest"] for x in g.values()))
print("head no fate", sum(1 for x in g.values() if x["head"] and not x["fate"]))
nn = collections.Counter()
for x in g.values():
    v = (x.get("v") or {}).get("notehead_is_not_a_notehead")
    if v:
        nn[(v["outcome"], str(v["value"])[:10], v["reason"])] += 1
print("nn", nn.most_common(30))
du = collections.Counter()
for x in g.values():
    v = (x.get("v") or {}).get("duration")
    if v and x["head"]:
        du[(v["outcome"], v["reason"])] += 1
print("dur", du.most_common(30))
print({k: len(v) if isinstance(v, list) else type(v) for k, v in f["bars"].items()})
for k in ("red_not_add_up", "held", "unread_empty", "partial"):
    if f["bars"][k]:
        print(k, json.dumps(f["bars"][k][0], default=str)[:600])
print("written", len(f["written"]), json.dumps(f["written"][0], default=str)[:400])
print("claimed", len(f["claimed_area"]), f["claimed_area"][:2])
print("nnw", f["notes_not_written"])
