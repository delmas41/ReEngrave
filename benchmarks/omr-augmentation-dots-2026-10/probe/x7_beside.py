"""2.180 probe 7: NOTE-side view. Every dot box (any role) that stands BESIDE a notehead by page geometry -- the head immediately
to its left, gap -0.3..1.3 sp from the head's right edge, |dy| <= 1.0 sp, the nearest such head -- and that head's (or, for a ghost,
its owner copy's) standing duration: is the note dotted? Grouped by the dot's role fate.
usage: x7_beside.py PLATE X1.json FATES.json OUT.json"""
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


def iou(a, b):
    x0, y0, x1_, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if x1_ <= x0 or y1 <= y0:
        return 0.0
    i = (x1_ - x0) * (y1 - y0)
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


heads = collections.defaultdict(list)
for k, g in G.items():
    if g.get("bb") and str(g.get("cls", "")).startswith("notehead"):
        heads[k.split("/")[1]].append(k)


def note_state(k):
    """standing duration of k, or of its owner copy when k is a ghost; -> (state, verdict, key)"""
    d = standing((G[k].get("V") or {}).get("duration"))
    if d and d["r"] == "owned_by_another_staff":
        for t in heads[k.split("/")[1]]:
            if t != k and iou(G[t]["bb"], G[k]["bb"]) >= 0.5:
                d2 = standing((G[t].get("V") or {}).get("duration"))
                if d2 and d2["r"] != "owned_by_another_staff":
                    k, d = t, d2
                    break
    nn = standing((G[k].get("V") or {}).get("notehead_is_not_a_notehead"))
    if nn and nn["o"] == "decided" and nn["val"] not in (False, None):
        return "head_refused", d, k
    if d is None:
        return "no_duration", d, k
    if d["o"] == "decided":
        val = d["val"] if isinstance(d["val"], dict) else {}
        if val.get("is_rest"):
            return "rest", d, k
        return ("DOTTED" if val.get("dots") else "UNDOTTED"), d, k
    if d["o"] == "narrowed":
        ds = [int((c or {}).get("dots") or 0) if isinstance(c, dict) else 0 for c in d["c"]]
        return ("narrowed_all_dotted" if ds and all(ds) else "narrowed_some_dotted" if any(ds) else "narrowed_UNDOTTED"), d, k
    return "abstained:" + str(d["r"]), d, k


tab = collections.Counter()
by_note = {}
rows = []
for f in F:
    bb = f["bb"]
    if not bb:
        continue
    dcy = (bb[1] + bb[3]) / 2
    best, bs = None, 1e9
    for k in heads[f["dot"].split("/")[1]]:
        hb = G[k]["bb"]
        gap = (bb[0] - hb[2]) / SP
        dy = (dcy - (hb[1] + hb[3]) / 2) / SP
        if -0.3 <= gap <= 1.3 and abs(dy) <= 1.0:
            s = gap + 2 * abs(dy)
            if s < bs:
                bs, best = s, (k, round(gap, 2), round(dy, 2))
    if best is None:
        tab[(f["fate"][:1], "not_beside_a_head")] += 1
        continue
    k, gap, dy = best
    st, d, nk = note_state(k)
    tab[(f["fate"][:1], st)] += 1
    r = dict(f, near=k, note=nk, gap=gap, dy=dy, state=st, hcls=G[k].get("cls"),
             ndur=(d["o"], d["r"], d["dec"], d["val"]) if d else None)
    rows.append(r)
    by_note.setdefault(nk, []).append(r)
print("dot boxes beside a head, by (role fate letter, the note's state):")
for k, n in sorted(tab.items()):
    print("  %5d %s" % (n, k))
# NOTE-level: a note with >= 1 dot box beside it
nt = collections.Counter()
for nk, rs in by_note.items():
    roles = {r["fate"][:1] for r in rs}
    nt[(rs[0]["state"], "a" if "a" in roles or "f" in roles else ("".join(sorted(roles))))] += 1
print("NOTES with a dot box beside them, by (state, roles of their dots):")
for k, n in sorted(nt.items(), key=lambda t: -t[1]):
    print("  %5d %s" % (n, k))
json.dump(rows, open(out, "w"), default=str)
