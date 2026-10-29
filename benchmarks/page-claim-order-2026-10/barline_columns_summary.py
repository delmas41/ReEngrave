"""Summarise m0_*.json from barline_columns.py: per plate, systems and columns by span class vs the shared extractor's cuts."""
import json, sys, collections
for plate in ("litolff", "brahms"):
    r = json.load(open(f"benchmarks/page-claim-order-2026-10/m0_{plate}.json"))
    n_sys = len(r)
    cols = collections.Counter(); cut = collections.Counter(); missed = []; invented = []; partial_sys = 0; rep = 0
    through_sys = 0
    for s in r:
        n = s["n_staves"]
        core = [c for c in s["cols"] if c["span"] != "per_staff" and c["votes"] >= 0.75 * n]
        G = collections.Counter()
        has_through = bool(core)
        through_sys += has_through
        for c in s["cols"]:
            k = c["span"] + (":" + c["vote"] if c["span"] == "per_staff" else "")
            cols[k] += 1
            if c["cut"]:
                cut[k] += 1
            if c["span"] != "per_staff" and c["cut"] and c["lacking"]:
                rep += c["lacking"]
        # systems with a column seen on some staves but not others (cut or through)
        if any(c["span"] != "per_staff" and c["lacking"] for c in s["cols"] if c["votes"] >= 0.75 * n or c["cut"]):
            partial_sys += 1
        for c in s["cols"]:
            if has_through and c["cut"] and c["span"] == "per_staff":
                invented.append((s["page"], s["system"], c["x"], c["vote"], c["votes"], n))
            if has_through and c["span"] != "per_staff" and not c["cut"] and c["votes"] >= 0.75 * n:
                missed.append((s["page"], s["system"], c["x"], c["votes"], n, c["crossed"]))
            if has_through and c["span"] != "per_staff" and c["cut"] and c["crossed"] <= 1 and n > 3:
                invented.append((s["page"], s["system"], c["x"], "thin_through", c["votes"], n))
    print(plate, "systems", n_sys, "with through-gap columns", through_sys)
    print("  columns by class (all / cut):", {k: (cols[k], cut[k]) for k in cols})
    print("  systems where a through column lacks a rule on some staves:", partial_sys, " staff-lacks on cut cols:", rep)
    print("  invented (cut per-staff col or 1-gap col in a through system):", len(invented), invented)
    print("  missed (strong through col not cut):", len(missed), missed)
