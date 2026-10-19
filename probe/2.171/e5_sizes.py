"""2.171 probe 5: how big is each subject in staff spaces and in pixels the model is shown? (box = the detector's own box, record or 0.05-floor re-run)
and the response curve of conf against shown staff space per class (pooled lost+kept+D, only f != 1 compared with each other so the selection on prod cancels).
usage: e5_sizes.py -> prints; writes probe/2.171/data/sizes.txt"""
import json
import statistics
from collections import defaultdict

ROOT = __file__.rsplit("/probe/", 1)[0]
D = ROOT + "/probe/2.171/data/"
out = []


def P(s=""):
    out.append(s)
    print(s)


for plate in ("lit", "bra"):
    R = json.load(open(D + "%s_run.json" % plate))
    SUB = json.load(open(D + "subjects.json"))[plate]["subjects"]
    grp = defaultdict(list)
    shown = []
    for key, r in R.items():
        if "subj" not in r:
            continue
        sp = r["meta"]["spacing"]
        S0 = r["meta"]["space_shown"]
        shown.append(S0)
        for i in r["subj"]:
            S = SUB[int(i)]
            if S["region"]:
                continue
            b = S["bbox"]
            g = ("lost" if S["role"] == "lost" and S["cause"] in "ABC" else ("D" if S["role"] == "lost" else S["role"]), S["want"])
            grp[g].append(((b[2] - b[0]) / sp, (b[3] - b[1]) / sp, (b[2] - b[0]) / sp * S0, (b[3] - b[1]) / sp * S0))
    P("PLATE %s: staff space shown to the detector in the bar crop: median %.1f px (min %.1f, max %.1f)" % (plate, statistics.median(shown), min(shown), max(shown)))
    P("  %-20s %4s  %-26s %-26s" % ("group/class", "n", "box w x h in staff spaces", "box w x h in net px at prod"))
    for g in sorted(grp):
        v = grp[g]
        if len(v) < 3:
            continue
        P("  %-20s %4d  %5.2f x %5.2f (medians)       %5.1f x %5.1f px" % ("%s/%s" % g, len(v), statistics.median(x[0] for x in v), statistics.median(x[1] for x in v),
                                                                   statistics.median(x[2] for x in v), statistics.median(x[3] for x in v)))
open(D + "sizes.txt", "w").write("\n".join(out))
