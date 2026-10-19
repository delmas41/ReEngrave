"""2.170 step 2b: tally the narrowed-beam notes of extract_2_170's output by what the verdict's own detail says.
usage: tally_2_170.py EX.json"""
import json
import sys
from collections import Counter

ex = json.load(open(sys.argv[1]))
N = ex["narrowed"]
t = Counter()
by = Counter()
standing = Counter()
for s, f in N.items():
    d = f["detail"] or {}
    st = ex["standing"][s]
    standing[(f["reason"], st["outcome"], st["decider"])] += 1
    key = [f["reason"]]
    key.append("stem" if d.get("stems_attached") else "NOSTEM")
    if f["reason"] == "beam_discounted_uncertain":
        whys = sorted({r["why"] for r in d.get("refused_strokes") or []})
        tips = sorted({str(r.get("at_tip")) for r in d.get("refused_strokes") or []})
        key.append("+".join(whys) or "-")
        key.append("tip:" + "/".join(tips))
        key.append("clean" if d.get("bare_stem_tip_window_clean") else "tipwin_not_clean")
    else:
        key.append("c%s/p%s" % (d.get("levels_certain"), d.get("levels_possible")))
        key.append("cv%s yk%s byst%s" % (d.get("cv_beams"), d.get("yolo_kept"), d.get("beams_by_stem")))
    by[tuple(key[:3])] += 1
    t[tuple(key)] += 1
print("STANDING (reason, final outcome, final decider):")
for k, v in standing.most_common():
    print(" ", v, k)
print("\nBY reason/stem/why:")
for k, v in by.most_common(40):
    print(" ", v, k)
print("\nFULL:")
for k, v in t.most_common(40):
    print(" ", v, k)
