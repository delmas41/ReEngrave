import json, collections
for plate in ("litolff", "brahms"):
    C = json.load(open("out/red-bars/work/%s.cls.json" % plate))
    F = {b["key"]: b for b in json.load(open("out/red-bars/work/%s.feat.json" % plate))}
    col = collections.defaultdict(list)
    for c in C:
        p, s, st, ce = (int(x) for x in c["key"].split("/"))
        col[(p, s, ce)].append(c)
    nst = {}
    for b in F.values():
        nst[(b["page"], b["system"])] = b["n_staves"]
    tot = collections.Counter(); big = {}
    for (p, s, ce), v in sorted(col.items()):
        n = len(v)
        ns = nst[(p, s)]
        tot[min(n, 6)] += n
        if n >= 4:
            big[(p, s, ce)] = (n, ns, sum(1 for c in v if c["over"]), sum(1 for c in v if not c["over"]))
    print(plate, "red bars by size of their same-cell red group (1..5, 6+):", dict(tot))
    inbig = sum(v[0] for v in big.values())
    print("  red bars in columns with >=4 red staves:", inbig, "of", len(C), " columns:", len(big))
    for k, v in sorted(big.items()):
        print("   col", k, "red staves", v[0], "of", v[1], "over", v[2], "short", v[3])
