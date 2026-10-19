"""2.171 probe 6: how much of 2.167d's 'wide crop' gain is the production RULE's own scale change?
imgsz_for_cell rounds the long side to a multiple of 32 and is applied to the WIDE cell separately, so the wide pass is shown a staff space a few percent
different from the bar pass. 'wide' here = same pixel size as the bar (context only); 'wide_rule' = what 2.167d ran.
Bins bars by rho = (ratio the rule used for the wide cell) / (ratio that keeps the bar's symbol size), reports mean change of the wanted-family conf vs prod
for lost / kept symbols. usage: e6_decomp.py"""
import json
import math
import statistics
from collections import defaultdict

ROOT = __file__.rsplit("/probe/", 1)[0]
D = ROOT + "/probe/2.171/data/"
out = []


def P(s=""):
    out.append(s)
    print(s)


def conf(sc, cond):
    v = sc.get(cond)
    return v["want"][1] if v and v.get("want") else 0.0


for plate in ("lit", "bra"):
    R = json.load(open(D + "%s_run.json" % plate))
    SUB = json.load(open(D + "subjects.json"))[plate]["subjects"]
    rhos = {}
    for key, r in R.items():
        if "conds" in r and "wide" in r["conds"] and "wide_rule" in r["conds"]:
            rhos[key] = r["conds"]["wide_rule"]["geo"]["r"] / r["conds"]["wide"]["geo"]["r"]
    P("PLATE %s: rho (wide-rule scale / bar scale) over %d bars: median %.3f, min %.3f, max %.3f; bars with |rho-1| > 3%%: %d" % (
        plate, len(rhos), statistics.median(rhos.values()), min(rhos.values()), max(rhos.values()), sum(1 for v in rhos.values() if abs(v - 1) > 0.03)))
    bins = defaultdict(list)
    for key, r in R.items():
        if key not in rhos:
            continue
        rho = rhos[key]
        b = "rho<0.97 (smaller)" if rho < 0.97 else ("rho>1.03 (larger)" if rho > 1.03 else "|rho-1|<=3%")
        for i, sc in r["subj"].items():
            S = SUB[int(i)]
            g = "lost" if S["role"] == "lost" and S["cause"] in "ABC" else ("kept" if S["role"] == "kept" else None)
            if g:
                bins[(g, b)].append((conf(sc, "wide") - conf(sc, "prod"), conf(sc, "wide_rule") - conf(sc, "prod"), conf(sc, "prod")))
    P("  %-6s %-22s %4s %14s %14s %12s" % ("group", "bin", "n", "d(wide, same px)", "d(wide_rule)", "rule-same"))
    for k in sorted(bins):
        v = bins[k]
        a, b = statistics.mean(x[0] for x in v), statistics.mean(x[1] for x in v)
        P("  %-6s %-22s %4d %+14.3f %+14.3f %+12.3f" % (k[0], k[1], len(v), a, b, b - a))
    allv = [x for k, v in bins.items() if k[0] == "lost" for x in v]
    P("  lost, all bars: d(wide same px) %+.3f   d(wide_rule) %+.3f   share of the rule's gain that is NOT context (rule - same px) / rule: %.0f%%" % (
        statistics.mean(x[0] for x in allv), statistics.mean(x[1] for x in allv),
        100 * (statistics.mean(x[1] for x in allv) - statistics.mean(x[0] for x in allv)) / max(1e-9, statistics.mean(x[1] for x in allv))))
open(D + "decomp.txt", "w").write("\n".join(out))
