"""Print the interesting part of measure_<plate>.json:  python3 benchmarks/page-ledger-2026-10/s3/show.py brahms"""
import json
import pathlib
import sys

r = json.load(open(pathlib.Path(__file__).parent / ("measure_%s.json" % sys.argv[1])))
print({k: v for k, v in r.items() if k not in ("filter", "arcs", "owners_changed_by_filter", "owners_changed_by_hairpin", "hairpin_disagreements")})
f = r["filter"]
print({k: v for k, v in f.items() if k != "rows"})
for c in f["rows"]:
    if c["reading_changed"]:
        print("reading changed", c["subject"], c["candidate"], c["dropped"], "now", c["fits_now"], c["pos_now"], "before", c["fits_before"], c["pos_before"])
for x in r["owners_changed_by_filter"]:
    print("FILTER", x["page"], x["key"], x["before"], "->", x["after"])
for x in r["owners_changed_by_hairpin"]:
    print("HAIRPIN", x["page"], x["key"], x["before"], "->", x["after"])
print("arcs", r["arcs"]["by_status_reason"], "owner not a seen-from staff:", r["arcs"]["owner_not_a_seen_from_staff"])
