"""sample.py PLATE over|short N SEED -> prints keys and a one-line summary each"""
import json, sys, random
plate, kind, n, seed = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
F = {b["key"]: b for b in json.load(open("out/red-bars/work/%s.feat.json" % plate))}
C = json.load(open("out/red-bars/work/%s.cls.json" % plate))
pool = [c for c in C if (c["over"] if kind == "over" else not c["over"]) and not c["doubled"]]
random.Random(seed).shuffle(pool)
keys = []
for c in pool[:n]:
    b = F[c["key"]]
    rows = " ".join("%s%s" % ((r["cls"] or "?").replace("notehead", "h").replace("Black", "B").replace("InSpace", "S").replace("OnLine", "L"), r["beats"]) for r in sorted(b["rows"], key=lambda r: r["xc"] or 0))
    print(c["key"], "want", c["want"], "cnt", c["counted"], "|", rows, "|", ",".join(c["fate_reasons"])[:80], file=sys.stderr)
    keys.append(c["key"])
print(" ".join(keys))
