"""List the probe's KEPT rows of one page, sorted by extent trend (ROADMAP 2.254 lane look)."""
import json
import sys

d = json.load(open(sys.argv[1]))
WHY = sys.argv[2] if len(sys.argv) > 2 else "KEPT"
for r in sorted([r for r in d["rows"] if r["why"] == WHY], key=lambda r: r["trend"]):
    print(r["staff"], r["bbox"], r["w_sp"], r["h_sp"], "open", r["open"], "cl", r["closed"], "trend", r["trend"])
