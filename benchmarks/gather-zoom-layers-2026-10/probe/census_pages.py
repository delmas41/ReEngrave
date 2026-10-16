"""2.152 P1 -- does a PAGE census differ from a DOCUMENT census? Per page median w/h (staff spaces) of confident black
heads, quarter rests and 8th rests; the spread of page medians vs the within-page spread. usage: census_pages.py DOC"""
import statistics
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import ctx  # noqa: E402

D = ctx.Doc("tmp_2152/%s.pkl" % sys.argv[1])
for fam in ("head:black", "head:half", "restQuarter", "rest8th"):
    pages = sorted({k[0] for k in D.census if k[1] == fam})
    meds, mads, ns = [], [], []
    for p in pages:
        pool = D.census[(p, fam)]
        if len(pool) < ctx.MIN_N:
            continue
        for i, nm in ((1, "w"), (2, "h")):
            pass
        w = [t[1] for t in pool]
        h = [t[2] for t in pool]
        meds.append((statistics.median(w), statistics.median(h)))
        mads.append((statistics.median([abs(x - meds[-1][0]) for x in w]) * 1.4826,
                     statistics.median([abs(x - meds[-1][1]) for x in h]) * 1.4826))
        ns.append(len(pool))
    if not meds:
        print(fam, "no page has >= %d confident instances" % ctx.MIN_N)
        continue
    allw = [t[1] for t in D.census_doc[fam]]
    allh = [t[2] for t in D.census_doc[fam]]
    print("%-12s pages_used %2d/%2d n/page med %d | page-median w: min %.2f med %.2f max %.2f (sd %.3f) | within-page "
          "w MAD %.3f | doc w med %.2f MAD %.3f | page-median h: min %.2f max %.2f (sd %.3f) within h MAD %.3f doc h MAD %.3f"
          % (fam, len(meds), len(pages), statistics.median(ns), min(m[0] for m in meds), statistics.median(m[0] for m in meds),
             max(m[0] for m in meds), statistics.pstdev([m[0] for m in meds]), statistics.median(m[0] for m in mads),
             statistics.median(allw), statistics.median([abs(x - statistics.median(allw)) for x in allw]) * 1.4826,
             min(m[1] for m in meds), max(m[1] for m in meds), statistics.pstdev([m[1] for m in meds]),
             statistics.median(m[1] for m in mads),
             statistics.median([abs(x - statistics.median(allh)) for x in allh]) * 1.4826))
