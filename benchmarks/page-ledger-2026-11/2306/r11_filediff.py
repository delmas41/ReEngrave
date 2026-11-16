"""2306 r11: what the written file changes at each glyph between two ON replays (e.g. r9 ON vs r11 ON) on given pages: notes gained, lost, value or
dot or pitch changed, blue changed; each with the r11 page stem reading `how`. Usage: r11_filediff.py A.json B.json PAGES [R11_REC] [--list]"""
import sys, json, re, collections
pa, pb, pages = sys.argv[1], sys.argv[2], {int(x) for x in sys.argv[3].split(",")}
rec = sys.argv[4] if len(sys.argv) > 4 and not sys.argv[4].startswith("--") else None
A, B = json.load(open(pa)), json.load(open(pb))


def hosts(D):
    o = collections.defaultdict(list)
    for h in D["hosts"]:
        if h.get("rg") and h.get("kind") == "note" and int(h["rg"].split("/")[1]) in pages:
            o[h["rg"]].append((h.get("pitch"), h.get("type"), len((h.get("sub") or {}).get("dot") or []), bool(h.get("blue"))))
    return o


HA, HB = hosts(A), hosts(B)
how = {}
if rec:
    txt = open(rec, encoding="utf-8").read()
    for m in re.finditer(r'"subject":"(glyph/[0-9/]+)","quantity":"page_stem",("value"|"reader").{0,400}?"how":"([a-z_]+)"', txt):
        how[m.group(1)] = m.group(3)
c = collections.Counter()
rows = []
for g in sorted(set(HA) | set(HB)):
    a, b = sorted(HA.get(g, [])), sorted(HB.get(g, []))
    if a == b:
        continue
    if not a:
        k = "gained"
    elif not b:
        k = "lost"
    elif [x[:3] for x in a] != [x[:3] for x in b]:
        k = "value/pitch/dots changed"
    else:
        k = "blue changed"
    c[(k, how.get(g))] += 1
    rows.append((g, k, a, b, how.get(g), B["fates"].get(g)))
for k, n in sorted(c.items(), key=lambda t: -t[1]):
    print("%4d  %s | r11 page stem: %s" % (n, k[0], k[1]))
if "--list" in sys.argv:
    for r in rows:
        print(*r)
