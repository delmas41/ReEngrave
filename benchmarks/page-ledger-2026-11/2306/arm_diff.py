"""2306 r8: compare two ON replays of the same gather.
  guard:   A = ON with the r7 no-stem guard off (ng8), B = ON as built (rf8): heads whose first duration reading is DECIDED in A and NARROWED in B;
           of those, written (a note host) in A and not in B; and OFF (rf8 off) wrote them.
  retire:  A = ON pre-retire (rf8 on), B = ON with the retire commit (rt8): heads with a DECIDED head_stem in A and none in B ("stems lost"), red bars
           OFF / A / B, notes written in A and not in B.
Usage: arm_diff.py guard|retire A.json B.json OFF.json"""
import sys, json, collections
mode, pa, pb, poff = sys.argv[1:5]
A, B, O = (json.load(open(p)) for p in (pa, pb, poff))


def first(D, q):
    o = {}
    for v in D["verdicts"]:
        if v["q"] == q and v["s"] not in o:
            o[v["s"]] = v
    return o


def last(D, q):
    return {v["s"]: v for v in D["verdicts"] if v["q"] == q}


def written(D):
    return {h["rg"] for h in D["hosts"] if h.get("rg") and h.get("kind") == "note"}


WA, WB, WO = written(A), written(B), written(O)
if mode == "guard":
    da, db = first(A, "duration"), first(B, "duration")
    moved = [g for g, v in db.items() if v["o"] == "narrowed" and (da.get(g) or {}).get("o") == "decided"]
    reasons = collections.Counter((da[g]["r"], db[g]["r"]) for g in moved)
    lost = [g for g in moved if g in WA and g not in WB]
    print("decided (guard off) -> narrowed (guard on):", len(moved), dict(reasons))
    print("  of those written with the guard off and not with it on:", len(lost), "| of those OFF wrote:", sum(1 for g in lost if g in WO))
    print("  fates ON:", collections.Counter(B["fates"].get(g) for g in moved))
    print("  examples:", lost[:8])
else:
    ha, hb = last(A, "head_stem"), last(B, "head_stem")
    gone = [g for g, v in ha.items() if v["o"] == "decided" and (hb.get(g) or {}).get("o") != "decided"]
    nn = last(A, "notehead_is_not_a_notehead")
    own = last(A, "glyph_owner")
    real = [g for g in gone if not ((nn.get(g) or {}).get("o") == "decided" and (nn.get(g) or {}).get("v") is True)
            and not ((own.get(g) or {}).get("o") == "decided" and isinstance((own.get(g) or {}).get("v"), str)
                     and own[g]["v"] != "staff/" + "/".join(g.split("/")[1:4]))]
    print("  of those, real heads of their own staff (not refused, not another staff's copy):", len(real))
    print("heads with a decided stem pre-retire and none with retire:", len(gone), collections.Counter((hb.get(g) or {}).get("r") for g in gone).most_common(6))
    print("  pre-retire stem reason of those:", collections.Counter(ha[g]["r"] for g in gone).most_common(6))
    print("red bars OFF %d | ON pre-retire %d | ON retire %d" % (len(O["red"]), len(A["red"]), len(B["red"])))
    print("notes written pre-retire and not with retire:", len(WA - WB), "| written with retire and not pre-retire:", len(WB - WA),
          "| of the lost, OFF wrote:", len((WA - WB) & WO))
