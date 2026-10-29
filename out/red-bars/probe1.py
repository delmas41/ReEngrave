import json, sys
from tools.omr.staged import lane_report as L
from tools.omr.staged.record_io import load_record
rec, pages, want = sys.argv[1], {int(x) for x in sys.argv[2].split(",")}, sys.argv[3]
res = load_record(rec)
r = res["record"] if "record" in res else res
keep = lambda it: (lambda pg: pg is None or pg in pages)(L.page_of(it.get("subject")))
for k in ("observations", "abstentions", "verdicts"):
    r[k] = [x for x in r[k] if keep(x)]
print(r.keys() if isinstance(r, dict) else type(r))
n = 0
for k in ("observations", "verdicts", "abstentions"):
    for o in r[k]:
        s = o.get("subject") or ""
        if s.startswith(want) or s.startswith("cell/" + want[6:]) :
            print(k, json.dumps(o, default=str)[:600]); n += 1
            if n > 60: sys.exit()
