"""ROADMAP 2.153 -- Sean's judged NOTE tiles (2.152's tile_rows.json, skind == note) by the reason string that wrote the
live duration at the time each tile was cut: right / narrowed / value_error per reason. Sean's answer is the truth."""
import collections
import json

r = json.load(open("benchmarks/gather-zoom-layers-2026-10/probe/out/tile_rows.json"))
c = collections.defaultdict(collections.Counter)
for x in r:
    if x.get("skind") != "note":
        continue
    d = x.get("dur")
    key = "none" if not d else "%s/%s" % (d[0], d[2])
    c[key][x["status"]] += 1
for k, v in sorted(c.items(), key=lambda kv: -sum(kv[1].values())):
    print("%4d  %-70s %s" % (sum(v.values()), k, dict(v)))
