"""make crop items from a c4 json: python3 probe/look_items.py C4.json OUT_ITEMS.json N SEED [maxscore]"""
import json
import random
import sys

rows = json.load(open(sys.argv[1]))
n, seed = int(sys.argv[3]), int(sys.argv[4])
mx = float(sys.argv[5]) if len(sys.argv) > 5 else 0.6
rows = [r for r in rows if (r["score"] or 0) < mx]
random.Random(seed).shuffle(rows)
items = []
for r in rows[:n]:
    items.append(dict(plate=r["plate"], page=r["page"], box=r["page_box"], sp=r["sp_page"], label="%s %s s=%.2f" % (r["plate"][0].upper(), r["sub"][6:], r["score"] or 0)))
json.dump(items, open(sys.argv[2], "w"), indent=0)
print(len(rows), "in pool;", len(items), "picked")
