import json, pickle, collections
d = pickle.load(open("out/lane-report/whole-rest/lit.pkl", "rb"))
rows = json.load(open("out/lane-report/whole-rest/c3_litolff.json"))
subs = {r[0] for r in rows}
n = 0
for v in d["verdicts"]:
    if v["subject"] in subs and v["quantity"] == "notehead_is_a_whole_rest":
        n += 1
        if n <= 4:
            print(v["subject"], json.dumps(v.get("detail"))[:600], v.get("margin"))
# how many of the 25 sit alone in the bar; what else the bar holds
gb = collections.defaultdict(list)
for o in d["observations"]:
    if o["quantity"] == "glyph_box":
        p = o["subject"].split("/"); gb["/".join(p[1:5])].append((o["subject"], o["value"][0]))
lone = 0
for s in subs:
    p = s.split("/"); k = "/".join(p[1:5])
    others = [x for x in gb[k] if x[0] != s]
    print(s, "others in cell:", collections.Counter(c for _, c in others).most_common(4))
