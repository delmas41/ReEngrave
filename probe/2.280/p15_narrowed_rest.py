"""2.280 probe 15: among ALL kept heads whose duration verdict is NARROWED (the 2.275 / 2.278 'narrowed notes' population), how many have NOTEHEAD_IS_A_WHOLE_REST decided True
(the same ink already read as a whole rest), with / without a touching stem row, and what the export did with them. Current tree re-adjudication (p8).
usage: p15_narrowed_rest.py plate"""
import collections
import json
import sys

plate = sys.argv[1]
pop = {r["sub"]: r for r in json.load(open("out/2.280/pop_%s.json" % plate))}
ct = collections.Counter()
for l in open("out/2.280/fates_%s.jsonl" % plate):
    f = json.loads(l)
    p = pop.get(f["sub"])
    if p is None or not f["duration"] or f["duration"][0] != "narrowed":
        continue
    wr = bool(f["whole_rest"] and f["whole_rest"][0] == "decided" and f["whole_rest"][2] is True)
    ct[("whole_rest decided True" if wr else "not a whole rest", "no stem row" if p["n_stem"] == 0 else "stem row", f["fate"])] += 1
print(plate, "kept heads with a NARROWED duration (re-adjudicated):", sum(ct.values()))
for k, v in sorted(ct.items()):
    print("  %-24s %-12s %-26s %d" % (k[0], k[1], k[2], v))
