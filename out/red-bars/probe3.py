import json, sys, collections
from tools.omr.staged import lane_report as L
from tools.omr.staged.record_io import load_record
rec, pages = sys.argv[1], {int(x) for x in sys.argv[2].split(",")}
res = load_record(rec)
r = res["record"] if "record" in res else res
keep = lambda it: (lambda pg: pg is None or pg in pages)(L.page_of(it.get("subject")))
c = collections.Counter(o["quantity"] for o in r["observations"] if keep(o))
print([k for k in c.items() if any(w in k[0] for w in ("bar", "cell", "partition", "measure", "system"))])
shown = 0
for o in r["verdicts"]:
    if keep(o) and o["quantity"] == "measure_partition" and shown < 2:
        print(json.dumps(o, default=str)[:1800]); shown += 1
shown = 0
for o in r["observations"]:
    if keep(o) and o["quantity"] in ("barline_column", "cell_box", "barline") and shown < 4 and o["subject"].startswith(sys.argv[3]):
        print(json.dumps(o, default=str)[:600]); shown += 1
