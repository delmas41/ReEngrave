"""2.185: per head, which accidental boxes own it (accidental_owner) and what its standing `accidental` verdict is (decider/value).
usage: acc_final.py RECORD.json EXTRACT.json OUT.json -- heads owned by one accidental box get `apply_printed_accidental`; heads owned by boxes of
DIFFERENT classes fall back to `respell_accidental` (the key's alteration)."""
import ijson, json, sys, collections
rec, ex, out = sys.argv[1:4]
d = json.load(open(ex)); cls = {b["subject"]: b["cls"] for b in d["boxes"]}
own = []; acc = []
with open(rec, "rb") as f:
    for v in ijson.items(f, "record.verdicts.item", use_float=True):
        if v["quantity"] == "accidental_owner": own.append(v)
        elif v["quantity"] == "accidental": acc.append(dict(id=v["id"], subject=v["subject"], value=v["value"], decider=v["decider"], sup=v.get("supersedes")))
sup = {v["sup"] for v in acc if v["sup"]}
final = {v["subject"]: v for v in acc if v["id"] not in sup}
osup = {v["supersedes"] for v in own if v.get("supersedes")}
by = collections.defaultdict(list)
for v in own:
    if v["id"] in osup or v["outcome"] != "decided" or not isinstance(v["value"], str): continue
    by[v["value"]].append(v["subject"])
c = collections.Counter(); rows = []
for h, s in by.items():
    cs = sorted({cls[x][10:] for x in s}); fv = final.get(h)
    kind = "one_box" if len(s) == 1 else ("several_boxes_one_class" if len(cs) == 1 else "several_boxes_diff_class")
    c[(kind, fv and fv["decider"], fv and str(fv["value"]))] += 1
    rows.append(dict(head=h, boxes=s, classes=[cls[x] for x in s], decider=fv and fv["decider"], value=fv and fv["value"], kind=kind))
tot = collections.Counter()
for (k, dec, val), n in c.items(): tot[k] += n
print("heads with an accidental owner", len(by), dict(tot))
for k, v in sorted(c.items(), key=lambda kv: -kv[1])[:20]: print("  %5d %s" % (v, k))
json.dump(rows, open(out, "w"))
