"""2.180 probe 2: every dot box (a glyph with a Q.AUG_DOT row) by FATE, from x1's extract (the night record's standing verdicts).
usage: x2_fates.py X1.json OUT.json"""
import collections
import json
import sys

G = json.load(open(sys.argv[1]))


def standing(chain):
    if not chain:
        return None
    sup = {x.get("sup") for x in chain if x.get("sup")}
    live = [x for x in chain if x["id"] not in sup]
    return (live or chain)[-1]


def origin(chain, v):
    by = {x["id"]: x for x in chain}
    seen = set()
    while v.get("sup") in by and v["id"] not in seen:
        seen.add(v["id"])
        v = by[v["sup"]]
    return v


def head_key(h):
    if isinstance(h, list):
        h = "/".join(str(x) for x in h)
    if not isinstance(h, str):
        return None
    p = h.split("/")
    return "/".join(p[:6]) if p and p[0] == "glyph" else None


def dots_of(val):
    return int((val or {}).get("dots") or 0) if isinstance(val, dict) else None


tab = collections.Counter()
detail = collections.Counter()
rows = []
for sub, g in G.items():
    if "aug_dot" not in (g.get("O") or {}):
        continue
    V = g.get("V") or {}
    role = standing(V.get("dot_role"))
    row = dict(dot=sub, cls=g.get("cls"), conf=g.get("conf"), bb=g.get("bb"))
    if role is None:
        fate = "c_no_verdict"
    elif role["o"] != "decided":
        fate = "c_role_abstained"
        detail[("c", role["r"])] += 1
        row["why"] = role["r"]
    elif role["val"] in ("staccato", "staccatissimo"):
        fate = "d_" + role["val"]
        row["owner"] = role["det"].get("owner")
    elif role["val"] == "augmentation":
        hk = head_key(role["det"].get("head"))
        row["head"] = hk
        h = G.get(hk) if hk else None
        dch = (h or {}).get("V", {}).get("duration") if h else None
        d = standing(dch)
        shared = bool(h and (h.get("V") or {}).get("stem_value"))
        row["shared_stem"] = shared
        if d is None:
            fate = "b_head_no_duration" if hk else "b_no_head_named"
        else:
            o = origin(dch, d)
            row.update(head_dur=dict(o=d["o"], r=d["r"], dec=d["dec"], val=d["val"], c=d["c"]),
                       origin=dict(o=o["o"], r=o["r"], dec=o["dec"]))
            later = d["dec"] not in ("adjudicate_duration",) and d["id"] != o["id"]
            row["later"] = d["dec"] if later else None
            if d["o"] == "decided":
                n = dots_of(d["val"])
                if (d["val"] or {}).get("is_rest") if isinstance(d["val"], dict) else False:
                    fate = "a_rest_dotted" if n else "x_rest_undotted"
                elif n:
                    fate = "f_applied_by_later_value" if later else "a_applied"
                else:
                    fate = "f_LOST_on_later_value" if later else "x_LOST_decided_undotted"
                detail[(fate, d["dec"], d["r"])] += 1
            elif d["o"] == "narrowed":
                ds = [dots_of(c) for c in d["c"]]
                if ds and all(x for x in ds):
                    fate = "b_narrowed_all_dotted"
                elif any(ds):
                    fate = "b_narrowed_some_dotted"
                else:
                    fate = "b_narrowed_NONE_dotted"
                detail[(fate, d["r"])] += 1
            else:
                fate = "b_head_abstained"
                detail[(fate, d["r"])] += 1
        if shared:
            tab["e_on_shared_stem(" + fate + ")"] += 1
    else:
        fate = "other:" + str(role["val"])
    row["fate"] = fate
    tab[fate] += 1
    rows.append(row)
print("dot boxes:", len(rows))
for k, n in sorted(tab.items()):
    print("  %6d  %s" % (n, k))
print("detail (top):")
for k, n in detail.most_common(45):
    print("  %6d  %s" % (n, k))
json.dump(rows, open(sys.argv[2], "w"), default=str)
