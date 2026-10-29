import json, sys, collections
plate = sys.argv[1]
F = {b["key"]: b for b in json.load(open("out/red-bars/work/%s.feat.json" % plate))}
C = json.load(open("out/red-bars/work/%s.cls.json" % plate))
short = [c for c in C if not c["over"]]
one = [c for c in short if c["n_events"] == 1]
print("short one-event", len(one))
t = collections.Counter()
for c in one:
    r = F[c["key"]]["rows"]
    t[(tuple(sorted(x["cls"] or "None" for x in r)), tuple(x["beats"] for x in r), c["why"], tuple(c["fate_reasons"])[:3])] += 1
for k, v in t.most_common(25): print(v, k)
print()
print("short, ge2 events: by class combos")
t = collections.Counter()
for c in short:
    if c["n_events"] >= 2:
        r = F[c["key"]]["rows"]
        t[(c["diff"], c["why"])] += 1
print(t.most_common())
print("page dist short one", collections.Counter(c["page"] for c in one))
print("page dist all", collections.Counter(c["page"] for c in C))
print("staff dist short one", collections.Counter(F[c["key"]]["staff"] for c in one))
print("staff dist all", collections.Counter(F[c["key"]]["staff"] for c in C))
