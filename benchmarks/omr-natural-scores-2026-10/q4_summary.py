"""Summarise q4_scores.json: per group x weights, the max over overlapping anchors of natural row 61, natural row 171, and max of both."""
import json, sys, collections
d = json.load(open(sys.argv[1]))
W = list(d["weights"])
def q(v, f): v = sorted(v); return v[int(f * (len(v) - 1))] if v else float("nan")
print("inks", len(d["inks"]), collections.Counter((i["plate"], i["grp"]) for i in d["inks"]))
print("check: prod nat61 == 2.193 nat_max on every ink:", all(abs((i["scores"]["prod"]["nat61"] or 0) - i["nat_max_2193"]) < 1e-3 for i in d["inks"]), "(control: replicates 2.193)")
for plate in ("litolff", "brahms", "both"):
    for grp in ("target", "ctrl_natural_read", "ctrl_flat_sharp"):
        ii = [i for i in d["inks"] if (plate == "both" or i["plate"] == plate) and i["grp"] == grp]
        if not ii: continue
        print(f"\n== {plate} / {grp}  n={len(ii)}")
        print("  %-11s %-8s %6s %6s %6s %6s %6s  frac>=.25 frac>=.05" % ("weights", "row", "p10", "p25", "med", "p75", "p90"))
        for w in W:
            for rn in ("nat61", "nat171", "natmax"):
                v = []
                for i in ii:
                    s = i["scores"][w]
                    v.append(max(s["nat61"] or 0, s["nat171"] or 0) if rn == "natmax" else (s[rn] or 0))
                print("  %-11s %-8s %6.3f %6.3f %6.3f %6.3f %6.3f  %5.2f %5.2f" % (w, rn, q(v, .1), q(v, .25), q(v, .5), q(v, .75), q(v, .9), sum(x >= .25 for x in v) / len(v), sum(x >= .05 for x in v) / len(v)))
