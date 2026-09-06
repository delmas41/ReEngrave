import collections
import json

P = ("/Users/seanjohnson/Desktop/ReEngrave/benchmarks/"
     "omr-absent-instrument-veto-2026-09/out/whole-report2.extract.json")
v = json.load(open(P))["contextual"]["absent_instrument_veto"]
print("mode", v["mode"], "rule", v["rule"], "window", v["window"],
      "reference_size", v["reference_size"])
rows = v["vetoes"]
print(json.dumps(rows[0], indent=1))
d = collections.Counter(r["distance_pages"] for r in rows)
o = collections.Counter(r["pages_outside"] for r in rows)
print("distance_pages:", dict(sorted(d.items())))
print("pages_outside :", dict(sorted(o.items())))
byinst = collections.defaultdict(collections.Counter)
for r in rows:
    byinst[r["instrument"]][r["distance_pages"]] += 1
for k, c in byinst.items():
    print(f"  {k:16s} {dict(sorted(c.items()))}")
