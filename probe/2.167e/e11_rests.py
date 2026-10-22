"""2.167e probe 11 (Q2): every rest-class box at >=0.25 in the record, by the gate that refused it; and how many refused as `rest_is_a_duplicate_box`
were refused because of a box that was ITSELF refused (the chain: A kept, B refused as A's duplicate, C refused as B's, C never overlapped A).
Rests the rescue reader found. usage: e11_rests.py ALL.json OUT.json"""
import json
import sys
import collections

G = json.load(open(sys.argv[1]))
RESTCLS = ("restWhole", "restHalf", "restQuarter", "rest8th", "rest16th", "rest32nd", "rest64th", "rest128th")
cells = collections.defaultdict(list)
for sub, g in G.items():
    if g.get("cls") in RESTCLS:
        cells[tuple(sub.split("/")[1:5])].append(sub)


def iou(a, b):
    iw = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    ih = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    i = iw * ih
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def refused(g):
    v = g.get("V", {}).get("rest_is_not_a_rest")
    return v is not None and v[2] is True


def final_reason(g):
    v = g.get("V", {}).get("rest_is_not_a_rest")
    return None if v is None else (v[1] if v[2] is True else "kept")


tab = collections.Counter()
chain = []
for key, subs in cells.items():
    for s in subs:
        g = G[s]
        r = final_reason(g)
        tab[(g["cls"], r)] += 1
        if r == "rest_is_a_duplicate_box":
            # the boxes this one overlaps (same class, higher priority); are they ALL refused?
            better = []
            for s2 in subs:
                if s2 == s:
                    continue
                g2 = G[s2]
                if g2["cls"] != g["cls"] or not g.get("bb") or not g2.get("bb"):
                    continue
                if iou(g["bb"], g2["bb"]) >= 0.02 and (g2.get("conf", 0), -int(s2.split("/")[-1])) > (g.get("conf", 0), -int(s.split("/")[-1])):
                    better.append(s2)
            others_diff = [s2 for s2 in subs if s2 != s and G[s2]["cls"] != g["cls"] and G[s2].get("bb") and g.get("bb") and iou(g["bb"], G[s2]["bb"]) >= 0.02]
            if better and all(refused(G[b]) for b in better) and not others_diff:
                chain.append(dict(sub=s, cls=g["cls"], conf=g.get("conf"), bb=g["bb"], better=better, better_conf=[G[b].get("conf") for b in better]))
print("rest-class boxes by (class, standing rest_is_not_a_rest outcome):")
for (c, r), n in sorted(tab.items(), key=lambda t: (t[0][0], -t[1])):
    print("  ", c, r, n)
print("duplicate-refused with every 'better' overlapping box itself refused (chain drop):", len(chain), collections.Counter(c["cls"] for c in chain))
unb = collections.Counter()
for sub, g in G.items():
    v = g.get("V", {}).get("unboxed_ink_is_a_rest")
    if v:
        unb[(v[0], v[1], str(v[2])[:20])] += 1
print("unboxed_ink_is_a_rest (rescue reader):", unb.most_common(12))
json.dump(chain, open(sys.argv[2], "w"))
