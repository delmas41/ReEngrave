"""How often does the far-head ledger reading's on/space claim disagree with cv_ledger's per-step read of the SAME staff
(whole-movement night slices, document shape pool)?  Reader ON ledger n -> cv says step n is no ledger; reader in the SPACE beyond
ledger n -> cv says step n+1 (through the head) IS a ledger.  usage: contest.py PLATE [subject ...]"""
import collections
import json
import re
import sys

S = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261029-night/%s/observations.jsonl"
plate = sys.argv[1]
show = set(sys.argv[2:])
far, rung = {}, collections.defaultdict(dict)
for line in open(S % plate):
    if '"far_head_ledger_position"' not in line and '"ledger_rung_ink"' not in line:
        continue
    o = json.loads(line)
    if o["quantity"] == "far_head_ledger_position":
        far[o["subject"]] = o
    elif o["quantity"] == "ledger_rung_ink":
        d = o["detail"]
        rung[(o["subject"], d["candidate"])][d["step"]] = (o["value"], d.get("left"), d.get("right"))


def own_staff(sub):
    p = sub.split("/")
    return "staff/%s/%s/%s" % (p[1], p[2], p[3])


c = collections.Counter()
how_c = collections.Counter()
for s, o in far.items():
    p = int(o["value"])
    why = o["detail"].get("ledger_reason") or ""
    how = (re.search(r"\(([a-z_]+)", why) or [None, "?"])[1]
    if p < 0:
        dist = -p
    elif p > 8:
        dist = p - 8
    else:
        c["inside"] += 1
        continue
    on = dist % 2 == 0
    n = dist // 2
    steps = rung.get((s, own_staff(s)))
    if not steps:
        c["no cv rows"] += 1
        continue
    probe = n if on else n + 1
    got = steps.get(probe)
    if got is None:
        c["cv no row at probe"] += 1
        continue
    contest = (on and not got[0]) or ((not on) and got[0])
    key = ("ON" if on else "SPACE") + (" CONTESTED" if contest else " agrees")
    c[key] += 1
    how_c[(how, key)] += 1
    if s in show:
        print(s, p, why, "probe step", probe, got, key)
print(plate, "far heads read", len(far), dict(c))
for k, v in sorted(how_c.items(), key=lambda t: -t[1]):
    print("   ", k, v)

# distribution of the stub reading at the ON step, by how
hist = collections.defaultdict(list)
for s, o in far.items():
    p = int(o["value"])
    dist = -p if p < 0 else (p - 8 if p > 8 else None)
    if dist is None or dist % 2:
        continue
    why = o["detail"].get("ledger_reason") or ""
    how = (re.search(r"\(([a-z_]+)", why) or [None, "?"])[1]
    got = (rung.get((s, own_staff(s))) or {}).get(dist // 2)
    if got and got[1] is not None:
        hist[how].append(max(got[1], got[2] or 0))
for how, v in hist.items():
    v.sort()
    print("ON", how, len(v), "max-stub quantiles", [round(v[int(q * (len(v) - 1))], 2) for q in (0, .05, .1, .25, .5)],
          "n<0.25:", sum(x < 0.25 for x in v))
