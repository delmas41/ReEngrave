"""usage: inkshow.py BARS.json INK.json -- red bars with their biggest unclaimed/contested ink components"""
import json
import sys

bars = json.load(open(sys.argv[1]))
ink = json.load(open(sys.argv[2]))
for b in bars:
    if b["status"] != "red":
        continue
    k = "%d/%d/%d/%d" % tuple(b["key"])
    cs = ink[k]
    r = b["red"]
    print(k, "want", r["want_quarters"], "got", r["counted_quarters"], b["why"][:12], "| comps:",
          [(c["px"], c["w_sp"], c["h_sp"], list(c["states"])[0][:14]) for c in cs[:5]])
