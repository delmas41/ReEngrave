import json, sys, collections
plate = sys.argv[1]
F = {b["key"]: b for b in json.load(open("out/red-bars/work/%s.feat.json" % plate))}
C = json.load(open("out/red-bars/work/%s.cls.json" % plate))
over = [c for c in C if c["over"]]
print("over", len(over))
t = collections.Counter(); t2 = collections.Counter(); t3 = collections.Counter()
for c in over:
    b = F[c["key"]]
    rows = [r for r in b["rows"] if r["xc"] is not None]
    # same-x, different-beats note rows
    mixed = 0
    for i, r in enumerate(rows):
        for s in rows[i + 1:]:
            if abs(r["xc"] - s["xc"]) < 0.8 * 15.5 and r["beats"] != s["beats"]:
                mixed += 1
    c["mixed_same_x"] = mixed
    rm = [x[0] for x in c["remove_one_fixes"]]
    for k in set(rm): t[k] += 1
    t2[("two_voice" if c["two_voice"] else "1v", "mixed_same_x" if mixed else "-", "removeFix" if rm else "noRemove", "valFix" if c["one_value_fixes"] else "noVal", "wholeRest" if c["whole_rest_in_bar"] else "")] += 1
    for r in b["rows"]:
        t3[(r["cls"], r["beats"], (r["dur"] or {}).get("reason"))] += 1
print("class removable", t.most_common())
print(t2.most_common())
print("row class/beats/reason in over", t3.most_common(30))
