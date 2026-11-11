"""2.280 r3: what the RED bars hold. A bar goes red when its written events do not add up; one value-uncertain head can cost the whole bar.
For each red bar of heads.py's .red.json (page, system, staff, cell): the kept heads of that cell (any fate) -- how many are not written for a VALUE reason
(duration_narrowed / duration_abstained / chord_value_undecided), written BLUE for value, not written for another reason, and do they sit in the chain
classes (i)-(iii) of chain.py. usage: redbars.py HEADS.jsonl"""
import collections
import json
import sys

heads = sys.argv[1]
rows = [json.loads(l) for l in open(heads)]
red = json.load(open(heads + ".red.json"))["places"]
VALUE = ("duration_narrowed", "duration_abstained", "chord_value_undecided")
by_cell = collections.defaultdict(list)
for r in rows:
    if r["kept"]:
        by_cell["/".join(r["sub"].split("/")[1:5])].append(r)
tot = collections.Counter()
bars = collections.Counter()
for p in red:
    k = "%s/%s/%s/%s" % (p["page"], p["system"], p["staff"], p["cell"])
    hs = by_cell.get(k, [])
    nv = [r for r in hs if r["fate"] in VALUE]
    bv = [r for r in hs if r.get("guess") and r["guess"][2] == "duration"]
    other = [r for r in hs if r["fate"] not in VALUE and r["fate"] not in ("written", "written_relocated", "ink_is_a_whole_rest") and not r["fate"].startswith("not_a_notehead")
             and r["fate"] not in ("owned_by_another_staff", "mark_group_duplicate")]
    bars["red bars"] += 1
    bars["  holding >= 1 head not written for value"] += bool(nv)
    bars["  holding >= 1 head written BLUE for value (and none not-written)"] += bool(bv and not nv)
    bars["  holding neither (a rest/other/pitch/gap cause, or the bar's own sum)"] += not nv and not bv
    bars["  holding a head not written for ANOTHER named reason"] += bool(other)
    tot["heads in red bars"] += p["rows"]
    tot["  of them in bars that hold a not-written-for-value head"] += p["rows"] if nv else 0
for k, v in list(bars.items()) + list(tot.items()):
    print("%5d %s" % (v, k))
