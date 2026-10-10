"""Which EVALUATE verdicts sit on a cell whose meter_at differs from the
system verdict's top-level (opening) numerator/denominator?"""
import sys, collections
sys.path.insert(0, ".")
from tools.omr.staged.record_io import load_record
from tools.omr.staged.record import meter_at

rec = load_record(sys.argv[1])
vs = rec["record"]["verdicts"]
sysmeter = {}
for v in vs:
    if v["quantity"] == "meter" and v["subject"].startswith("system/"):
        sysmeter[v["subject"]] = v
diff_systems = {}
for k, v in sysmeter.items():
    val = v.get("value")
    if v["outcome"] != "decided" or not val:
        continue
    segs = val.get("segments") or []
    top = (val.get("numerator"), val.get("denominator"))
    if len(segs) > 1 or (segs and (segs[0].get("numerator"), segs[0].get("denominator")) != top):
        diff_systems[k] = val
print("systems with >1 segment:", len(diff_systems), "of", len(sysmeter))
for k, val in sorted(diff_systems.items()):
    print(" ", k, [(s.get("from_cell"), "%s/%s" % (s.get("numerator"), s.get("denominator")), s.get("corroborated")) for s in val["segments"]])

DECIDERS = ("size_measure_rest", "reconcile_duration", "reconcile_chord_duration",
            "reinstate_rest_between_staves")
c = collections.Counter()
rows = collections.defaultdict(list)
for v in vs:
    d = v.get("decider")
    if d not in DECIDERS:
        continue
    parts = v["subject"].split("/")
    skey = "system/%s/%s" % (parts[1], parts[2])
    val = diff_systems.get(skey)
    cell = int(parts[4]) if len(parts) > 4 else None
    c[(d, "all")] += 1
    if val is None:
        continue
    top = (val.get("numerator"), val.get("denominator"))
    at = meter_at(val, cell)
    atk = (at.get("numerator"), at.get("denominator")) if at else None
    if atk != top:
        c[(d, "on_a_cell_whose_meter_differs_from_the_opening")] += 1
        rows[d].append((v["subject"], top, atk, v["value"] if d != "size_measure_rest" else v["value"].get("beats")))
for k in sorted(c):
    print(k, c[k])
for d, rr in rows.items():
    print(d, len(rr))
    for r in rr[:60]:
        print("   ", r)
