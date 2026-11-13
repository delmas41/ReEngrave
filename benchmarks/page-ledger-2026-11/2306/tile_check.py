"""Does a tile's written note change between the r4 and r5 ON arms (and is its place still a change OFF vs ON)?  Usage: tile_check.py KEY.json plate PRE4 PRE5"""
import sys, json, collections
key, plate, p4, p5 = sys.argv[1:5]


def hosts(f):
    o = collections.defaultdict(list)
    for h in json.load(open(f))["hosts"]:
        if h.get("rg"):
            o[h["rg"]].append((h.get("kind"), h.get("pitch"), h.get("type"), h.get("voice"),
                               json.dumps({k: v for k, v in (h.get("sub") or {}).items() if v}, sort_keys=True)))
    return o


a, b = hosts(p4 + ".on.json"), hosts(p5 + ".on.json")
for t in json.load(open(key)):
    if t["plate"] != plate:
        continue
    g = t["glyph"]
    print(t["tile"], g, "SAME" if sorted(a.get(g, [])) == sorted(b.get(g, [])) else "CHANGED %s -> %s" % (a.get(g), b.get(g)))
