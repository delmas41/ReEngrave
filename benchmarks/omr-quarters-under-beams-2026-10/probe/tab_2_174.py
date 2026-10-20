"""2.174 step 2a: tabulate census_2_174 rows with beam evidence in the cell by the drop reasons the verdict recorded. usage: tab_2_174.py CENSUS.json"""
import json, sys, collections
d = json.load(open(sys.argv[1]))
R = [r for r in d["rows"] if r["has_stem"] and r["reason"] == "head_and_marks" and (r["cv"] or r["yolo"])]
print(len(R))
c = collections.Counter()
for r in R:
    k = []
    for f in ("far", "beyond", "ledger", "slash", "nbr", "arc", "ink", "by_stem"):
        if r[f]:
            k.append(f)
    c[("cv" if r["cv"] else "") + ("+yolo" if r["yolo"] else ""), tuple(k)] += 1
for k, v in c.most_common(30):
    print(v, k)
