import sys, json, collections, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))
from tools.omr.staged.record_io import load_record
r = load_record(sys.argv[1])["record"]
n = 0
c = collections.Counter()
for v in r["verdicts"]:
    if "page_claim" in str(v.get("reason")):
        d = v.get("detail") or {}
        c[(v["quantity"], v.get("reason"), (d.get("ink_consult") or {}).get("by"), tuple((d.get("ink_consult") or {}).get("also") or ()))] += 1
        if n < 0:
            print(json.dumps({k: x for k, x in v.items() if k not in ("considered", "correlated")}, default=str)[:2500])
            n += 1
for k, x in c.most_common(20):
    print(x, k)
