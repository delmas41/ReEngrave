"""2.170: OFF vs ON from replay_2_170 outputs, per plate, ON THE FILE.
usage: compare_2_170.py REPLAYDIR DOC"""
import json
import sys
from collections import Counter
from pathlib import Path

RD, DOC = Path(sys.argv[1]), sys.argv[2]
a = json.load(open(RD / ("%s.off.json" % DOC)))
b = json.load(open(RD / ("%s.on.json" % DOC)))
print("== %s" % DOC)
for arm, r in (("off", a), ("on", b)):
    w = r["coverage"].get("written") or {}
    nn = r["coverage"].get("notes_not_written") or {}
    narrowed = sum(1 for x in r["glyphs"].values() if x["outcome"] == "narrowed" and not x["rest"])
    print(" %-3s file notes %s  <note> %s  held bars %s  narrowed live verdicts %d  notes_not_written total %s" % (
        arm, w.get("notes"), r["notes_in_xml"], r["coverage"]["bars_held_out_sum"].get("bars"), narrowed,
        r["coverage"].get("notes_not_written_total")))
    print("     not written by reason:", dict(sorted(nn.items(), key=lambda kv: -kv[1])[:8]))
held_on = {tuple(h) for h in b["held_bars"]}
held_off = {tuple(h) for h in a["held_bars"]}
ch = Counter()
detail = []
for g, y in b["glyphs"].items():
    x = a["glyphs"].get(g)
    if x is None:
        continue
    if (x["outcome"], x["written"], x["dots"]) != (y["outcome"], y["written"], y["dots"]):
        p = g.split("/")
        bar = (int(p[1]), int(p[2]), int(p[3]), int(p[4]))
        kind = "%s->%s" % (x["outcome"] if x["outcome"] != "decided" else x["written"], y["outcome"] if y["outcome"] != "decided" else y["written"])
        ch[(("by_rule" if y["off_tip"] else "knock_on"), kind, "held_on" if bar in held_on else "bar_written_on")] += 1
        detail.append((g, y["off_tip"], x, y, bar in held_off, bar in held_on))
print(" values changed: %d" % len(detail))
for k, v in ch.most_common():
    print("   %5d %s" % (v, k))
print(" heads the rule touched (on):", sum(1 for y in b["glyphs"].values() if y["off_tip"]))
print(" held bars off->on: %d -> %d (released %d, newly held %d)" % (len(held_off), len(held_on), len(held_off - held_on), len(held_on - held_off)))
json.dump(detail, open(RD / ("%s.changed.json" % DOC), "w"))
