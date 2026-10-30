"""List the through-ink columns the extractor did not cut, and the thin (<=1 gap) cut ones, from m0_*.json."""
import json
for pl in ("litolff", "brahms"):
    for s in json.load(open(f"benchmarks/page-claim-order-2026-10/m0_{pl}.json")):
        n = s["n_staves"]
        for c in s["cols"]:
            if c["span"] != "per_staff" and (not c["cut"] or c["crossed"] <= 1):
                print(pl, s["page"], s["system"], "n", n, {k: c[k] for k in ("x", "span", "votes", "crossed", "cut")})
