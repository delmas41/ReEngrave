"""2.185: accidental boxes that BOTH name the same head as their owner (accidental_owner), by plate. usage: acc_owner.py RECORD.json EXTRACT.json
A head with two accidental owners of DIFFERENT alterations is a place where `consequences.apply_printed_accidental` fires twice on one head
(the later supersede wins, in subject iteration order) -- a wrong-class-kept route into the exported pitch."""
import ijson, json, sys, collections
rec, ex = sys.argv[1:3]
d = json.load(open(ex)); cls = {b["subject"]: b["cls"] for b in d["boxes"]}
sup = set(); own = []
with open(rec, "rb") as f:
    for v in ijson.items(f, "record.verdicts.item", use_float=True):
        if v["quantity"] == "accidental_owner":
            own.append(v)
sup = {v["supersedes"] for v in own if v.get("supersedes")}
by = collections.defaultdict(list)
for v in own:
    if v["id"] in sup or v["outcome"] != "decided" or not isinstance(v["value"], str): continue
    by[v["value"]].append(v["subject"])
multi = {h: s for h, s in by.items() if len(s) > 1}
diff = {h: s for h, s in multi.items() if len({cls[x] for x in s}) > 1}
print("decided accidental owners", sum(len(s) for s in by.values()), "heads with an accidental owner", len(by),
      "| heads owned by >1 accidental box", len(multi), "| of those with >1 CLASS", len(diff))
c = collections.Counter(tuple(sorted(cls[x] for x in s)) for s in diff.values())
print(c.most_common(12))
json.dump(dict(multi=multi, diff=diff), open(sys.argv[3], "w")) if len(sys.argv) > 3 else None
