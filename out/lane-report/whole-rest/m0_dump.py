"""whole-rest m0: dump the observations + verdicts of the sample pages of a saved record to a pickle.
usage: m0_dump.py PLATE PAGES OUT.pkl"""
import json, pickle, sys
from tools.omr.staged.record_io import load_record
from tools.omr.staged import lane_report as L
rec = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/lane-2.222-one-head/out/lane-report/2.222-gather/%s.record.json" % sys.argv[1]
pages = {int(x) for x in sys.argv[2].split(",")}
res = load_record(rec)
r = res["record"] if "record" in res else res
keep = lambda it: (lambda pg: pg is None or pg in pages)(L.page_of(it.get("subject")))
out = {k: [x for x in r[k] if keep(x)] for k in ("observations", "verdicts")}
pickle.dump(out, open(sys.argv[3], "wb"))
print({k: len(v) for k, v in out.items()})
vs = [v for v in out["verdicts"] if "rest_touches_two" in json.dumps(v)][:2]
for v in vs:
    print(json.dumps(v)[:1500])
