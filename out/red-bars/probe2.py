import json, sys, collections
from tools.omr.staged import lane_report as L
from tools.omr.staged.record_io import load_record
rec, pages = sys.argv[1], {int(x) for x in sys.argv[2].split(",")}
res = load_record(rec)
r = res["record"] if "record" in res else res
keep = lambda it: (lambda pg: pg is None or pg in pages)(L.page_of(it.get("subject")))
for k in ("observations", "abstentions", "verdicts"):
    r[k] = [x for x in r[k] if keep(x)]
c = collections.Counter()
shown = set()
for o in r["verdicts"]:
    q = o["quantity"]
    c[q] += 1
    if q in ("meter", "events", "event", "voices", "onset_column") and q not in shown:
        shown.add(q); print(json.dumps(o, default=str)[:1500])
print(c.most_common(60))
sub = collections.Counter((o["quantity"], (o.get("subject") or "").split("/")[0]) for o in r["verdicts"] if o["quantity"] in ("meter", "voices", "event"))
print(sub)
