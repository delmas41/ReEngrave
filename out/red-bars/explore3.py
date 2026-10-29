import json, sys, collections
plate = sys.argv[1]
C = json.load(open("out/red-bars/work/%s.cls.json" % plate))
F = {b["key"]: b for b in json.load(open("out/red-bars/work/%s.feat.json" % plate))}
by = {}
for c in C:
    p, s, st, ce = (int(x) for x in c["key"].split("/"))
    by[(p, s, st, ce)] = c
pairs = []
for (p, s, st, ce), c in by.items():
    n = by.get((p, s, st, ce + 1))
    if n and not c["over"] and not n["over"]:
        tot = round(max(c["counted"]) + max(n["counted"]), 4)
        pairs.append((c["key"], n["key"], max(c["counted"]), max(n["counted"]), tot, c["want"]))
print(plate, "adjacent short-short pairs", len(pairs), "sum == want", sum(1 for x in pairs if abs(x[4] - x[5]) < 1e-6), "sum<want", sum(1 for x in pairs if x[4] < x[5] - 1e-6), "sum>want", sum(1 for x in pairs if x[4] > x[5] + 1e-6))
for x in pairs[:15]: print(x)
# adjacent over/short
mix = 0
for (p, s, st, ce), c in by.items():
    n = by.get((p, s, st, ce + 1))
    if n and c["over"] != n["over"]:
        mix += 1
print("adjacent over-short pairs", mix)
# how does the cell width of the red cell compare to the typical cell width
import statistics
cb = {}
for l in open("out/red-bars/slice/%s/observations.jsonl" % plate):
    o = json.loads(l)
    if o["quantity"] == "cell_box":
        cb[o["subject"]] = o["value"]
w_all = [v[2] - v[0] for v in cb.values()]
print("median cell width", statistics.median(w_all))
ws = [(cb["cell/" + c["key"]][2] - cb["cell/" + c["key"]][0]) for c in C if "cell/" + c["key"] in cb]
print("red short cell widths median", statistics.median([(cb["cell/" + c["key"]][2] - cb["cell/" + c["key"]][0]) for c in C if not c["over"] and "cell/" + c["key"] in cb]), "over", statistics.median([(cb["cell/" + c["key"]][2] - cb["cell/" + c["key"]][0]) for c in C if c["over"] and "cell/" + c["key"] in cb]))
