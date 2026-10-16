"""ROADMAP 2.151 -- every head whose live duration differs between two `dots_truth_2_151.py` outputs (base, arm), by
the kind of change. usage: diff_2_151.py BASE.json ARM.json OUT.json"""
import collections, json, sys

a, b = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
da, db = a["durations"], b["durations"]
rows, c = [], collections.Counter()
for s in sorted(set(da) | set(db)):
    x, y = da.get(s), db.get(s)
    if x == y:
        continue
    kind = "%s:%s -> %s:%s" % (x and x[0], x and x[3], y and y[0], y and y[3])
    c[kind] += 1
    rows.append(dict(glyph=s, base=x, arm=y, bbox=b["page_boxes"].get(s), kind=kind))
json.dump(rows, open(sys.argv[3], "w"), indent=0)
print(len(rows), "changed")
for k, n in c.most_common():
    print("  %3d %s" % (n, k))
