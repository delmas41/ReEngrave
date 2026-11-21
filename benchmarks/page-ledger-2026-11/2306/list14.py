"""2306 r12: notes the file writes differently r9 ON -> r11 ON in the bars whose page stem reading changed. Usage: list14.py CELLS.json A.json B.json PLATE"""
import sys, json, collections
cells, pa, pb, plate = sys.argv[1:5]
ok = set(json.load(open(cells))[plate])
A, B = json.load(open(pa)), json.load(open(pb))


def hosts(D):
    o = collections.defaultdict(list)
    for h in D["hosts"]:
        if h.get("rg") and h.get("kind") == "note" and "/".join(h["rg"].split("/")[1:5]) in ok:
            o[h["rg"]].append((h.get("pitch"), h.get("type"), len((h.get("sub") or {}).get("dot") or [])))
    return o


HA, HB = hosts(A), hosts(B)
for g in sorted(set(HA) | set(HB)):
    a, b = sorted(HA.get(g, [])), sorted(HB.get(g, []))
    if a != b:
        print(g, a, "->", b, "| fate r9", A["fates"].get(g), "| fate r11", B["fates"].get(g))
