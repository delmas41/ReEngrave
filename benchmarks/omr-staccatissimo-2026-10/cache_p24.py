"""2.138: load the 20261014-night Brahms record ONCE, cache page-24 rows + dot_role/articulation abstain counts to JSON.
STAGED reader output. python3 cache_p24.py RECORD OUT.json"""
import json, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.omr.staged.record_io import load_record
rec = load_record(sys.argv[1])
r = rec.get("record", rec)
print({k: (len(v) if hasattr(v, "__len__") else v) for k, v in r.items()}, flush=True)
def on24(s):
    p = str(s).split("/")
    return len(p) > 1 and p[1] == "24"
out = {"keys": list(r.keys())}
for k, v in r.items():
    if isinstance(v, list) and v and isinstance(v[0], dict):
        out[k] = [x for x in v if on24(x.get("subject", ""))]
        print(k, len(v), "->", len(out[k]), flush=True)
# whole-record counts of dot_role abstain reasons
cnt = collections.Counter()
for v in r.get("verdicts", []):
    if v.get("rule", "").startswith("dot_role") or v.get("question", "") == "dot_role":
        cnt[(v.get("outcome"), str(v.get("reason") or v.get("detail", {}).get("reason")))] += 1
out["dot_role_counts"] = [[list(k), n] for k, n in cnt.items()]
json.dump(out, open(sys.argv[2], "w"))
