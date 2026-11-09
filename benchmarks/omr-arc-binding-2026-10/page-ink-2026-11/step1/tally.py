"""2.274 step 1: tally why detector curves have no whole run.   python3 tally.py WORKDIR [PLATE-pPAGE ...]"""
import collections
import json
import pathlib
import re
import sys

wd = pathlib.Path(sys.argv[1])
names = sys.argv[2:] or sorted(p.name.replace(".step1.json", "") for p in wd.glob("*.step1.json"))
tot = collections.Counter()
for n in names:
    J = json.load(open(wd / (n + ".step1.json")))
    s = J["summary"]
    c = collections.Counter()
    for k in J["curves"]:
        if k["refused"] or k["best"] >= 0.8:
            continue
        why = re.sub(r"\(.*", "", k["why_no_run"] or "?")
        bs = "blanked>=.3" if k["blank_share"] >= 0.3 else "open"
        c["%s/%s" % (why, bs)] += 1
        tot["%s/%s" % (why, bs)] += 1
    print(n, "kept", s["curves_kept"], "whole", s["whole"], "after seed", s["whole_after_seed"], dict(c))
print("TOTAL", dict(tot))
