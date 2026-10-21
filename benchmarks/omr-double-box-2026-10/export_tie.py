"""2.185: Litolff only -- tie clusters to the REAL exporter's per-box fate (export_fates.py). usage: export_tie.py ROWS.json FATES.json
A box has an export fate only if it is a notehead or a rest (`_place_notes`); other classes are reported as 'n/a'."""
import json, sys, collections
rows = json.load(open(sys.argv[1])); fates = json.load(open(sys.argv[2]))
W = ("written", "written_relocated")
t = collections.Counter(); ex = collections.defaultdict(list)
for x in rows:
    ms = x["members"]
    tr = [m for m in ms if m["subject"] in fates]
    if not tr: continue
    nw = sum(fates[m["subject"]] in W for m in tr)
    fam = "+".join(sorted({m["fam"] for m in tr}))
    kind = "same_cell" if x["cause"].startswith(("same_cell", "view", "stem", "lowconf", "pass")) else "cross_staff"
    ctype = x["ct"]
    reasons = tuple(sorted(collections.Counter(fates[m["subject"]] for m in tr if fates[m["subject"]] not in W).items()))
    key = (kind, fam, ctype, "written=%d of %d traced" % (nw, len(tr)))
    t[key] += 1
    if len(ex[key]) < 3: ex[key].append([m["subject"] for m in tr])
for k, v in sorted(t.items(), key=lambda kv: -kv[1]): print("%5d  %s" % (v, k))
