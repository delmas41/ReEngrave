"""Where in the document each system size lives — the movement structure."""
import json
import sys

d = json.load(open(sys.argv[1]))
runs = []
for r in d["rows"]:
    for s in r.get("systems", []):
        p = r["page"]
        if runs and runs[-1][0] == s:
            runs[-1][2] = p
        else:
            runs.append([s, p, p])
print(f"{len(d['rows'])} pages")
for size, a, b in runs:
    print(f"  size {size:3d}   pages {a:3d}-{b:3d}")
