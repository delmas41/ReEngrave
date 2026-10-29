import json, sys, collections
for plate in ("litolff", "brahms"):
    C = json.load(open("out/red-bars/work/%s.cls.json" % plate))
    by = {}
    for c in C:
        p, s, st, ce = (int(x) for x in c["key"].split("/"))
        by[(p, s, st, ce)] = c
    merged = set(); shifted = set()
    for (p, s, st, ce), c in by.items():
        n = by.get((p, s, st, ce + 1))
        if not n or c["two_voice"] or n["two_voice"]:
            continue
        a, b, w = max(c["counted"]), max(n["counted"]), c["want"]
        if abs(a + b - w) < 1e-6:
            merged.update([c["key"], n["key"]])
        elif abs(a + b - 2 * w) < 1e-6 and (c["over"] != n["over"]):
            shifted.update([c["key"], n["key"]])
    print(plate, "red bars in a cut-bar pair (A+B==want):", len(merged), " shifted-boundary pairs (over+short, A+B==2*want):", len(shifted))
    print("  merged keys", sorted(merged)[:40])
    json.dump(dict(merged=sorted(merged), shifted=sorted(shifted)), open("out/red-bars/work/%s.partition.json" % plate, "w"))
