"""Print one system's m0 columns: barline_columns_one.py plate page system (reads m0_<plate>.json); skips per-staff minority rows not cut."""
import json
import sys
plate, page, sysi = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
for s in json.load(open(f"benchmarks/page-claim-order-2026-10/m0_{plate}.json")):
    if s["page"] == page and s["system"] == sysi:
        print("n", s["n_staves"], "cuts", s["cuts"])
        for c in s["cols"]:
            if c["cut"] or c["votes"] >= 0.4 * s["n_staves"] or c["span"] != "per_staff":
                print({k: c[k] for k in ("x", "span", "vote", "votes", "crossed", "cut")})
