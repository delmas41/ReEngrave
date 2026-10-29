"""2.229: why is a bar red? From the exporter's report: bars_written_red.bars_list (counted vs wanted quarters) and partial_bars (the why).
usage: redwhy.py REPORT.json NPAGES"""
import json, sys, collections
R = json.load(open(sys.argv[1])); n = int(sys.argv[2])
red = R["bars_written_red"]["bars_list"]
c = collections.Counter(); ex = collections.defaultdict(list)
for b in red:
    want = b["want_quarters"]; got = b["counted_quarters"]
    g = got[0] if got else None
    if g is None: k = "no count"
    elif g > want + 1e-6: k = "overfull (counted > bar)"
    else: k = "underfull (counted < bar)"
    c[k] += 1
    if len(ex[k]) < 4: ex[k].append("%d/%d/%d/%d" % (b["page"], b["system"], b["staff"], b["cell"]))
print("red bars", len(red), "per page %.1f" % (len(red) / n))
for k, v in c.most_common(): print("  %-28s %4d  %.1f/page  e.g. %s" % (k, v, v / n, ex[k]))
pb = R["partial_bars"]["bars"]
w = collections.Counter((b["status"], b["why"]) for b in pb)
print("partial bars", len(pb))
for k, v in w.most_common(): print("  ", k, v)
# rows by kind in red bars
rk = collections.Counter(); st = collections.Counter()
for b in red:
    for r in b.get("rows") or []:
        rk[r["kind"]] += 1; st[r["status"]] += 1
print("rows in red bars by kind", dict(rk), "status", dict(st))
