"""raw empty_bar_rest_search rows (and counts) from a record: search_rows.py REC [cells...]"""
import json, sys, collections
sys.path.insert(0, ".")
from tools.omr.staged.record_io import load_record

r = load_record(sys.argv[1])
rec = r.get("record", r)
want = set(sys.argv[2:])
n = collections.Counter()
for o in rec["observations"]:
    if o.get("quantity") == "empty_bar_rest_search":
        d = o.get("detail") or {k: v for k, v in o.items() if k not in ("subject", "quantity", "value")}
        n[(bool(o.get("value")), (d or {}).get("reason") if isinstance(d, dict) else None)] += 1
        c = "/".join(o["subject"].split("/")[1:5])
        if c in want:
            print(o["subject"], json.dumps(o)[:600])
print(n)
vc = collections.Counter()
for v in rec["verdicts"]:
    if v.get("quantity") == "empty_bar_whole_rest":
        vc[(v.get("outcome"), v.get("reason"))] += 1
print(vc)
