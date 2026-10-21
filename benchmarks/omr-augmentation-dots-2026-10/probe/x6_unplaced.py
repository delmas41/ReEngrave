"""2.180 probe 6: every dot whose role ABSTAINED (or was read as a wedge with no head): the nearest notehead box to its LEFT on
the page (any staff, any cell), gap and height in staff spaces, staff steps, and that head's own standing verdicts.
usage: x6_unplaced.py PLATE X1.json FATES.json OUT.json"""
import collections
import json
import sys

plate, x1, fates, out = sys.argv[1:5]
SP = {"lit": 20.0, "bra": 32.0}[plate]
G = json.load(open(x1))
F = json.load(open(fates))


def standing(chain):
    if not chain:
        return None
    sup = {x.get("sup") for x in chain if x.get("sup")}
    return ([x for x in chain if x["id"] not in sup] or chain)[-1]


heads = collections.defaultdict(list)
for k, g in G.items():
    if g.get("bb") and str(g.get("cls", "")).startswith("notehead"):
        heads[k.split("/")[1]].append(k)
tab = collections.Counter()
rows = []
for f in F:
    if not (f["fate"] == "c_role_abstained" or f["fate"] == "d_staccatissimo"):
        continue
    bb = f["bb"]
    dcy = (bb[1] + bb[3]) / 2
    best, bs = None, 1e9
    for k in heads[f["dot"].split("/")[1]]:
        hb = G[k]["bb"]
        gap = (bb[0] - hb[2]) / SP
        dy = (dcy - (hb[1] + hb[3]) / 2) / SP
        if -0.3 <= gap <= 2.0 and abs(dy) <= 1.3:
            s = gap + 2 * abs(dy)
            if s < bs:
                bs, best = s, (k, round(gap, 2), round(dy, 2))
    r = dict(dot=f["dot"], fate=f["fate"], why=f.get("why"), cls=f["cls"], conf=f["conf"], bb=bb,
             dstep=(G[f["dot"]].get("O") or {}).get("dot_staff_position"))
    if best is None:
        r["near"] = None
        key = "no_head_left_within_2sp"
    else:
        k, gap, dy = best
        h = G[k]
        V = h.get("V") or {}
        d = standing(V.get("duration"))
        nn = standing(V.get("notehead_is_not_a_notehead"))
        own = standing(V.get("glyph_owner"))
        r.update(near=k, gap=gap, dy=dy, hcls=h.get("cls"), hstep=(h.get("O") or {}).get("notehead_staff_position"),
                 hdur=(d["o"], d["r"], d["val"]) if d else None, refused=(nn["o"], nn["val"], nn["r"]) if nn else None,
                 owner=(own["o"], own["val"]) if own else None,
                 same_cell="/".join(k.split("/")[:5]) == "/".join(f["dot"].split("/")[:5]))
        refused = bool(nn and nn["o"] == "decided" and nn["val"] not in (False, None, "no", "false"))
        key = ("head_refused" if refused else ("head_other_cell" if not r["same_cell"] else "head_same_cell")) \
            + ("_hollow" if "Half" in str(h.get("cls")) or "Whole" in str(h.get("cls")) else "_black")
    r["key"] = key
    tab[(f["fate"], f.get("why"), key)] += 1
    rows.append(r)
for k, n in sorted(tab.items(), key=lambda t: -t[1]):
    print("  %5d %s" % (n, k))
json.dump(rows, open(out, "w"), default=str)
