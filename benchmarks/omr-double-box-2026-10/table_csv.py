"""2.185: the full table, one CSV per plate x run: cause, kind, class pair, source set, outcome -> inks, boxes.
usage: table_csv.py ROWS.json OUT.csv"""
import csv, json, sys, collections
rows = json.load(open(sys.argv[1]))
t = collections.Counter(); b = collections.Counter()
for x in rows:
    ms = x["members"]
    pair = "+".join(sorted({m["cls"] for m in ms}))
    src = "+".join(sorted({m["src"] for m in ms}))
    fates = "+".join(sorted(collections.Counter(m["fate"] for m in ms).elements()))
    k = (x["cause"], pair, src, x["out"])
    t[k] += 1; b[k] += len(ms)
w = csv.writer(open(sys.argv[2], "w"))
w.writerow(["cause", "classes_in_ink", "sources", "outcome", "inks", "boxes"])
for k, v in sorted(t.items(), key=lambda kv: -kv[1]): w.writerow(list(k) + [v, b[k]])
print(len(t), "rows")
