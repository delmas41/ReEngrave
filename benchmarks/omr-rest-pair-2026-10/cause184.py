"""2.184 Part 1: where did each box of a different-class rest pair come from. usage: cause184.py EX.json [OUT.json]
Clusters = boxes linked by `duplicate_disagrees_with` (as 2.182a count.py). Prints reader pair, class pair, conf stats."""
import collections, json, sys
d = json.load(open(sys.argv[1]))
byid = {b["id"]: b for b in d["boxes"]}
sup = {v["supersedes"] for v in d["verdicts"] if v.get("supersedes")}
live = {v["subject"]: v for v in d["verdicts"] if v["id"] not in sup}
dis = {s: v for s, v in live.items() if v["reason"] == "rest_is_a_duplicate_box" and (v.get("detail") or {}).get("duplicate_disagrees_with")}
sub2box = {b["subject"]: b for b in d["boxes"]}
adj = collections.defaultdict(set)
for s, v in dis.items():
    for oid in v["detail"]["duplicate_disagrees_with"]:
        if oid in byid:
            adj[s].add(byid[oid]["subject"]); adj[byid[oid]["subject"]].add(s)
seen, cl = set(), []
for s in dis:
    if s in seen: continue
    st, comp = [s], set()
    while st:
        x = st.pop()
        if x in comp: continue
        comp.add(x); st += list(adj[x])
    seen |= comp; cl.append(sorted(comp))
rd = collections.Counter(); out = []
for c in cl:
    bs = [sub2box[s] for s in c]
    key = " + ".join(sorted(b["reader"] for b in bs))
    rd[key] += 1
    out.append(dict(cluster=c, readers=[b["reader"] for b in bs], classes=[b["value"][0] for b in bs], scores=[round(b["score"], 3) for b in bs],
                    frames=[b["frame"] for b in bs], bbox=[b["detail"]["bbox_page_px"] for b in bs], detail=[{k: v for k, v in b["detail"].items() if k not in ("bbox_page_px", "x_center_page", "y_center_page")} for b in bs]))
print(sys.argv[1].split("/")[-1], "clusters", len(cl))
for k, v in rd.most_common(): print("  ", v, k)
print("reader counts over ALL rest boxes:", collections.Counter(b["reader"] for b in d["boxes"]))
if len(sys.argv) > 2: json.dump(out, open(sys.argv[2], "w"))
