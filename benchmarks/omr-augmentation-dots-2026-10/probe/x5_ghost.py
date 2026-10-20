"""2.180 probe 5: a dot decided augmentation on a GHOST head (its duration abstained `owned_by_another_staff`): does the
OWNER's copy of the same ink (another glyph, same page, box IoU >= 0.5) carry the dot in its standing duration?
usage: x5_ghost.py X1.json FATES.json"""
import collections
import json
import sys

G = json.load(open(sys.argv[1]))
F = json.load(open(sys.argv[2]))


def standing(chain):
    if not chain:
        return None
    sup = {x.get("sup") for x in chain if x.get("sup")}
    return ([x for x in chain if x["id"] not in sup] or chain)[-1]


def iou(a, b):
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    i = (x1 - x0) * (y1 - y0)
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


by_page = collections.defaultdict(list)
for k, g in G.items():
    if g.get("bb") and str(g.get("cls", "")).startswith("notehead"):
        by_page[k.split("/")[1]].append(k)
tab = collections.Counter()
out = []
for f in F:
    if f["fate"] != "b_head_abstained" or (f.get("head_dur") or {}).get("r") != "owned_by_another_staff":
        continue
    h = f["head"]
    hb = G[h]["bb"]
    twins = [k for k in by_page[h.split("/")[1]] if k != h and iou(G[k]["bb"], hb) >= 0.5]
    best = None
    for k in twins:
        d = standing((G[k].get("V") or {}).get("duration"))
        if d and d.get("r") != "owned_by_another_staff":
            best = (k, d)
    if best is None:
        tab["owner_copy_not_found" if not twins else "owner_copy_also_abstained"] += 1
        continue
    k, d = best
    val = d["val"] if isinstance(d["val"], dict) else {}
    if d["o"] == "decided":
        key = "owner_decided_dotted" if val.get("dots") else "owner_decided_UNDOTTED"
    elif d["o"] == "narrowed":
        ds = [int((c or {}).get("dots") or 0) if isinstance(c, dict) else 0 for c in d["c"]]
        key = "owner_narrowed_all_dotted" if ds and all(ds) else ("owner_narrowed_some_dotted" if any(ds) else "owner_narrowed_NONE_dotted")
    else:
        key = "owner_abstained:" + str(d["r"])
    tab[key] += 1
    out.append(dict(dot=f["dot"], ghost=h, owner=k, owner_dur=dict(o=d["o"], r=d["r"], dec=d["dec"], val=d["val"], c=d["c"]), key=key))
for k, n in tab.most_common():
    print("  %5d %s" % (n, k))
json.dump(out, open(sys.argv[2].replace("fates", "ghost"), "w"), default=str)
