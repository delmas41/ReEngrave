"""usage: slice_report.py TAG OUTDIR -- from slice_whole.py's output: whole-class glyphs OFF vs ON, by outcome; which are newly refused and why;
the ones still a kept whole (duration 4.0 decided)."""
import collections
import json
import sys

tag, d = sys.argv[1], sys.argv[2]
o = json.load(open("%s/%s.slice.json" % (d, tag)))


def written_whole(r):
    return (r["notehead"] and r["notehead"][0] is False and r["duration"] and r["duration"][0] == "decided" and r["duration"][1] == 4.0)


off, on = o["off"], o["on"]
print(tag, "whole-class glyphs:", len(off), "| kept as decided 4.0 whole OFF:", sum(written_whole(r) for r in off.values()),
      "ON:", sum(written_whole(r) for r in on.values()))
c = collections.Counter()
for g in off:
    a, b = off[g], on.get(g)
    if b and b["notehead"] != a["notehead"]:
        c[(str(a["notehead"]), str(b["notehead"][1]))] += 1
print("notehead verdict changes OFF -> ON:", dict(c))
c2 = collections.Counter()
for g in off:
    if written_whole(off[g]) and not written_whole(on[g]):
        c2[(on[g]["notehead"][1] if on[g]["notehead"][0] else "kept note", str(on[g]["duration"][2:]))] += 1
print("whole -> not whole, by cause:", dict(c2))
rem = [g for g in on if written_whole(on[g])]
json.dump(rem, open("%s/%s.slice.remaining.json" % (d, tag), "w"))
print("remaining kept wholes:", len(rem))
for g in rem[:80]:
    print("  ", g, on[g]["cls"], on[g]["duration"])
