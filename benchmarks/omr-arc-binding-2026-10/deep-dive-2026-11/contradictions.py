"""The exporter's tie pitch-contradiction guard: how many dropped ties had an end the exporter itself calls unsure (measure only)."""
import collections
import json
import sys

d = json.load(open(sys.argv[1]))
tc = d["report_arc"].get("tie_contradictions") or []
c = collections.Counter()
for t in tc:
    u = t.get("unsure_ends") or []
    c[(t["kind"], "unsure_end:" + "/".join(sorted({x["why"] for x in u})) if u else "no_unsure_end")] += 1
print(len(tc), dict(c))
print(d["report_arc"].get("arcs_not_written"))
print({k: v for k, v in d["report_arc"].items() if k not in ("tie_contradictions", "arcs_not_written")})
