"""For human-boxed accidentals (v14-v22, i.e. NOT in hollow-ft's boxed corpus), the best own-class score vs the best score of the other two groups, per model.
'offered' = own row >= .25 and is the max of the three groups; 'confused' = another group's row >= .25 and above own; 'silent' = all three < .25."""
import json, collections
r = [x for x in json.load(open("q6_confusion.json")) if not x["ver"].startswith(("v1-", "v2-", "v3-", "v4-"))]
for m in ("prod", "dsv2base"):
    print("\n" + m)
    for g in ("natural", "flat", "sharp"):
        c = collections.Counter()
        for x in (y for y in r if y["model"] == m and y["grp"] == g):
            sc = {"natural": x["nat"] if g != "natural" else x["own"], "flat": x["flat_row"], "sharp": x["sharp_row"]}
            sc[g] = x["own"]
            top = max(sc, key=sc.get)
            c["offered" if top == g and sc[g] >= .25 else "confused_with_" + top if sc[top] >= .25 else "silent"] += 1
        n = sum(c.values()); print("  human %-8s n=%d  " % (g, n), {k: f"{v} ({v/n:.0%})" for k, v in sorted(c.items())})
