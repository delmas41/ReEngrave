import json, statistics, collections
for plate in ("litolff", "brahms"):
    cb = {}
    for l in open("out/red-bars/slice/%s/observations.jsonl" % plate):
        o = json.loads(l)
        if o["quantity"] == "cell_box":
            p = o["subject"].split("/")
            cb[(int(p[1]), int(p[2]), int(p[3]), int(p[4]))] = o["value"]
    C = {tuple(int(x) for x in c["key"].split("/")): c for c in json.load(open("out/red-bars/work/%s.cls.json" % plate))}
    # per system median width (staff 0), first cell excluded (clef/key room)
    med = {}
    for (p, s, st, ce), v in cb.items():
        if st == 0 and ce > 0:
            med.setdefault((p, s), []).append(v[2] - v[0])
    med = {k: statistics.median(v) for k, v in med.items()}
    def cat(key):
        p, s, st, ce = key
        w = cb[key][2] - cb[key][0]
        m = med.get((p, s))
        if not m or ce == 0: return "n/a"
        return "narrow" if w < 0.6 * m else ("wide" if w > 1.5 * m else "normal")
    t = collections.Counter(); tr = collections.Counter(); ts = collections.Counter(); to = collections.Counter()
    for k in cb:
        c = cat(k); t[c] += 1
        if k in C:
            tr[c] += 1
            (to if C[k]["over"] else ts)[c] += 1
    print(plate, "cells", dict(t))
    print("   red", dict(tr), " red short", dict(ts), " red over", dict(to))
    print("   share of cells red:", {k: round(tr[k] / t[k], 3) for k in t})
