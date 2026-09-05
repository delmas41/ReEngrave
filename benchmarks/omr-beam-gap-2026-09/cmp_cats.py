"""Compare cost_by_category between two ops dumps of the same work."""
import json
import sys

a = json.load(open(sys.argv[1]))['cost_by_category']
b = json.load(open(sys.argv[2]))['cost_by_category']
for k in sorted(set(a) | set(b)):
    da, db = a.get(k, 0), b.get(k, 0)
    if da != db:
        print(f"{k:44s} {da:5d} -> {db:5d}  ({db-da:+d})")
