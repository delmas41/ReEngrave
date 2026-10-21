"""2.182a: count rests refused by `family_precision._duplicate_box_refusal` as a DIFFERENT-class pair
(reason `rest_is_a_duplicate_box`, detail key `duplicate_disagrees_with`). usage: count.py DOC EXTRACT.json [OUTCASES.json]
A case = connected cluster of boxes linked by disagreement. 'both refused' = every box in the cluster has a live rest_is_not_a_rest verdict value True."""
import collections, json, sys
doc, path = sys.argv[1:3]
d = json.load(open(path))
byid = {b["id"]: (s, b) for s, b in d["boxes"].items()}
sup = {v["supersedes"] for v in d["verdicts"] if v.get("supersedes")}
live = {}
for v in d["verdicts"]:
    if v["id"] not in sup:
        live[v["subject"]] = v
dis = {s: v for s, v in live.items() if v["reason"] == "rest_is_a_duplicate_box" and (v.get("detail") or {}).get("duplicate_disagrees_with")}
same = [s for s, v in live.items() if v["reason"] == "rest_is_a_duplicate_box" and s not in dis]
# clusters
adj = collections.defaultdict(set)
for s, v in dis.items():
    for oid in v["detail"]["duplicate_disagrees_with"]:
        if oid in byid:
            adj[s].add(byid[oid][0]); adj[byid[oid][0]].add(s)
seen, cl = set(), []
for s in dis:
    if s in seen: continue
    st, comp = [s], set()
    while st:
        x = st.pop()
        if x in comp: continue
        comp.add(x); st += list(adj[x])
    seen |= comp; cl.append(sorted(comp))
rows, pairs, boxes_ref = [], collections.Counter(), 0
for c in cl:
    refused_all = all(live.get(s, {}).get("value") is True for s in c)
    cls = sorted(d["boxes"][s]["value"][0] for s in c)
    rows.append(dict(cluster=c, classes=cls, scores=[d["boxes"][s]["score"] for s in c], both_refused=refused_all,
                     reasons=[live[s]["reason"] if s in live else None for s in c]))
    pairs[" + ".join(cls)] += 1
    boxes_ref += sum(1 for s in c if s in dis)
print(doc, "disagreement verdicts (boxes refused):", len(dis), "clusters (cells of ink):", len(cl),
      "all-members-refused clusters:", sum(r["both_refused"] for r in rows), "| same-class duplicate refusals (control):", len(same))
for k, v in pairs.most_common(): print("   ", v, k)
if len(sys.argv) > 3: json.dump(rows, open(sys.argv[3], "w"), indent=1)
