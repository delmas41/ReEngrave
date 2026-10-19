"""2.167d probe 11: is the staff space the detector is shown the same in the bar crop and in the re-cuts? Prints median shown staff space (px at imgsz) and
imgsz per variant, and the fraction of variants whose shown space differs from base by more than 10%. usage: d11_scale.py"""
import json
import os
import statistics

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = ROOT + "/probe/2.167d/data/"
for pl in ("lit", "bra"):
    rr = json.load(open(D + "%s_rerun.json" % pl))
    for v in ("base", "shiftR", "shiftL", "wide", "system"):
        sp = [R["variants"][v]["space_shown"] for R in rr.values() if "space_shown" in R["variants"].get(v, {})]
        sz = [R["variants"][v]["imgsz"] for R in rr.values() if "imgsz" in R["variants"].get(v, {})]
        diff = sum(1 for R in rr.values() if "space_shown" in R["variants"].get(v, {}) and abs(R["variants"][v]["space_shown"] - R["variants"]["base"]["space_shown"]) > 0.1 * R["variants"]["base"]["space_shown"])
        print(pl, v, "median staff space shown %.1f px, imgsz median %d, bars where it differs from base by >10%%: %d of %d" % (statistics.median(sp), statistics.median(sz), diff, len(sp)))
