import json, collections
for plate in ("litolff", "brahms"):
    F = json.load(open("out/red-bars/work/%s.feat.json" % plate))
    C = {c["key"]: c for c in json.load(open("out/red-bars/work/%s.cls.json" % plate))}
    u = 15.75 if plate == "litolff" else 32.0
    res = collections.Counter(); ex = collections.defaultdict(list)
    for b in F:
        c = C[b["key"]]
        rows = [r for r in b["rows"] if r["glyph"]]
        far = [r for r in rows if r["staffpos"] is not None and abs(r["staffpos"]) >= 8.0 and r["kind"] == "note"]
        if not far:
            continue
        # events: group far rows by x; sum durations of far rows (chord = one)
        xs = {}
        for r in far:
            xs.setdefault(round((r["xc"] or 0) / (0.8 * u)), r["beats"])
        far_sum = sum(xs.values())
        k = ("over" if c["over"] else "short")
        res[k + "_with_far_row"] += 1
        diff = c["diff"]
        if c["over"] and abs(diff - far_sum) < 1e-6:
            res["over_far_row_sum_equals_excess"] += 1; ex["fix"].append(b["key"])
        if c["over"] and diff > 0 and far_sum >= diff - 1e-6:
            res["over_far_rows_cover_excess"] += 1
    print(plate, dict(res))
    print("  examples far-removal fixes:", ex["fix"][:10])
