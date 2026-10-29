"""2.229: print the per-kind per-page counts from rank_counts.py output, old beside new. usage: summarize_rank.py WORKDIR_OLD WORKDIR_NEW PLATE NPAGES"""
import json, sys
wo, wn, plate, npg = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
O = json.load(open("%s/%s.rank.saved.json" % (wo, plate))); N = json.load(open("%s/%s.rank.saved.json" % (wn, plate)))
keys = sorted(set(O["rows"]) | set(N["rows"]), key=lambda k: -N["rows"].get(k, {}).get("counted_total", 0))
print("%-34s %8s %8s %9s %9s" % ("kind", "old tot", "new tot", "old/page", "new/page"))
for k in keys:
    o = O["rows"].get(k, {}).get("counted_total", 0); n = N["rows"].get(k, {}).get("counted_total", 0)
    print("%-34s %8d %8d %9.1f %9.1f" % (k, o, n, o / npg, n / npg))
print("--- totals over the loaded pages (new)")
for k, v in N["totals_over_loaded_pages"].items(): print(" ", k, json.dumps(v, default=str)[:260])
print("--- totals over the loaded pages (old)")
for k, v in O["totals_over_loaded_pages"].items(): print(" ", k, json.dumps(v, default=str)[:260])
