"""2.171 probe 10: for each condition, how many of the lost symbols (A/B/C, prod < 0.25) does that ONE run lift to >= 0.25, and how many kept symbols (prod >= 0.25)
does it drop below 0.25? Also the one dot of 2.167d (Brahms 3/0/3/5, 0.13 -> 0.60) under every condition. usage: e10_lifts.py"""
import json

ROOT = __file__.rsplit("/probe/", 1)[0]
D = ROOT + "/probe/2.171/data/"
out = []


def P(s=""):
    out.append(s)
    print(s)


def conf(sc, c):
    v = sc.get(c)
    return v["want"][1] if v and v.get("want") else 0.0


CONDS = ["sc0.5", "sc0.7", "sc0.85", "sc1.20", "sc1.4", "sc2.0", "wide", "wide_rule", "mirror", "foreign", "triple", "system", "L1gray", "L2white", "mw64", "mw128", "mw256", "mv64",
         "area", "wide_area", "phx3", "phx6", "phy4", "phy6", "pos_c", "pos_l", "pos_r"]
for plate in ("lit", "bra"):
    R = json.load(open(D + "%s_run.json" % plate))
    SUB = json.load(open(D + "subjects.json"))[plate]["subjects"]
    lost, kept = [], []
    for key, r in R.items():
        for i, sc in r.get("subj", {}).items():
            S = SUB[int(i)]
            if S["role"] == "lost" and S["cause"] in "ABC" and conf(sc, "prod") < 0.25:
                lost.append((key, S, sc))
            if S["role"] == "kept" and conf(sc, "prod") >= 0.25:
                kept.append((key, S, sc))
    P("PLATE %s: lost with prod < 0.25: %d; kept with prod >= 0.25: %d" % (plate, len(lost), len(kept)))
    P("  %-10s %-18s %-22s" % ("condition", "lost lifted >=0.25", "kept dropped <0.25"))
    for c in CONDS:
        L = [x for x in lost if c in x[2]]
        K = [x for x in kept if c in x[2]]
        if not L:
            continue
        P("  %-10s %2d of %2d  (%3.0f%%)   %2d of %2d  (%3.0f%%)" % (c, sum(1 for x in L if conf(x[2], c) >= 0.25), len(L), 100 * sum(1 for x in L if conf(x[2], c) >= 0.25) / len(L),
                                                                  sum(1 for x in K if conf(x[2], c) < 0.25), len(K), 100 * sum(1 for x in K if conf(x[2], c) < 0.25) / max(1, len(K))))
    # best-of-k re-roll: how many lost are lifted by AT LEAST ONE of the 9 phase runs; by best of any 9 non-phase runs
    PH = ["phx1", "phx2", "phx3", "phx4", "phx5", "phx6", "phy2", "phy4", "phy6"]
    P("  lifted by at least one of the 9 phase runs: %d of %d; kept dropped by at least one: %d of %d" % (
        sum(1 for x in lost if max(conf(x[2], c) for c in PH) >= 0.25), len(lost), sum(1 for x in kept if min(conf(x[2], c) for c in PH) < 0.25), len(kept)))
    if plate == "bra":
        P()
        P("  the 2.167d dot, Brahms 3/0/3/5 (0.13 in the bar crop, 0.60 in the wide crop), conf under every condition:")
        for key, S, sc in lost:
            if key == "3/0/3/5" and S["want"] == "dot":
                P("   " + "  ".join("%s=%.2f" % (c, conf(sc, c)) for c in ["prod"] + CONDS))
open(D + "lifts.txt", "w").write("\n".join(out))
