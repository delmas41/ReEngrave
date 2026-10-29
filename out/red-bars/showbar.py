import json, sys
plate = sys.argv[1]
F = {b["key"]: b for b in json.load(open("out/red-bars/work/%s.feat.json" % plate))}
for k in sys.argv[2:]:
    b = F[k]
    print("==", k, "want", b["want"], "counted", b["counted"], "why", b["why"], "meter", (b["meter"] or {}).get("reason"), "others_red", b["others_red"], "voices", (b["voices"] or [None, None])[:2])
    for r in sorted(b["rows"], key=lambda r: r["xc"] or 0):
        print("  ", str(r["glyph"]).replace("glyph/", ""), r["cls"], r["beats"], r["status"], "xc", r["xc"] and round(r["xc"]), "yc", r["yc"] and round(r["yc"]), "pos", r["staffpos"], "owner", r["owner"], "dur", (r["dur"] or {}).get("reason"), (r["dur"] or {}).get("outcome"))
    print("   fates", b["fates"])
