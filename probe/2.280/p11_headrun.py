"""2.280 probe 11: how far would a HEAD-ANCHORED thin-run read go? For every stratum-A head (labels R/N/H/D/S, my look) and the stratum-B heads (decided, written, no stem row):
is there a vertical ink run >= 1.5 sp in a narrow band at a head side (the p2 raw_runs: erased image, then original), on the engraving side or either side?
This is the CANDIDATE for the micro test (not built). The not-a-head labels (R rests, N accidentals/clef pieces) are the control that can fail: a reader that gives them a 'stem' is wrong.
usage: p11_headrun.py"""
import collections
import json

for plate in ("litolff", "brahms"):
    R = json.load(open("out/2.280/rerunfull_%s.json" % plate))
    L = json.load(open("out/2.280/labels_%s.json" % plate))
    ct = collections.Counter()
    for s, lab in L.items():
        rr = R[s]["raw_runs"]
        e = max((v["len_sp"] for k, v in rr.items() if k.startswith("erased")), default=0)
        o = max((v["len_sp"] for k, v in rr.items() if k.startswith("original")), default=0)
        m = max(e, o)
        ct[(lab, "run>=1.5" if m >= 1.5 else "run<1.5", "run>=2.5" if m >= 2.5 else "")] += 1
    print(plate, "stratum A by my label")
    for k, v in sorted(ct.items()):
        print("   %s %-9s %-9s %d" % (k[0], k[1], k[2], v))
