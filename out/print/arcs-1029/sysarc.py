"""Does Q.SYSTEM_ARC (2.166, full-curve trace + head anchors) hold the answer for arcs the file drops? usage: sysarc.py PLATE PAGES"""
import json, sys, collections
from tools.omr.staged import lane_report as L
from tools.omr.staged.record_io import load_record
plate, pages = sys.argv[1], {int(x) for x in sys.argv[2].split(",")}
D = json.load(open("/private/tmp/claude-501/arcs/%s.json" % plate))
with L.record_lock():
    res = load_record("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/lane-2.222-one-head/out/lane-report/2.222-gather/%s.record.json" % plate)
    r = res["record"] if "record" in res else res
    sa = [o for o in r["observations"] if o.get("quantity") == "system_arc" and (L.page_of(o.get("subject")) in pages)]
print(plate, "system_arc rows", len(sa))
if sa:
    print(json.dumps(sa[0], default=str)[:1500])
by = {}
for o in sa:
    by[o["subject"]] = o
# fate of the arc by its own subject, shape of its system_arc
fate = {r_["sub"]: r_["fate"] for r_ in D["rows"]}
cnt = collections.Counter()
for o in sa:
    v = o["value"]
    shape = v
    cnt[(fate.get(o["subject"], "?"), shape)] += 1
for k, v in sorted(cnt.items(), key=lambda kv: -kv[1])[:40]:
    print(v, k)
