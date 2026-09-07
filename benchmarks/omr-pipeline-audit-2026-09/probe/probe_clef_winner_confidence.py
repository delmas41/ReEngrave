import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fixtures import fixtures, root, chdir_root, SCAN, ENGRAVED, CONTESTS
# ⚠️ `fixtures()` is the fail-loud one; importing it and then calling
# `glob.glob` yourself buys nothing. An unguarded glob that matches
# nothing prints a clean all-zero table and exits 0 — the failure this
# audit has now produced three ways. Fixed 2026-09-07.
chdir_root()

import json, glob, os
from collections import Counter
for fam,pat in (("scan","benchmarks/omr-scan-e2e-2026-09/fixtures/*..graft09.omr.json"),
                ("engraved","benchmarks/omr-orchestral-e2e/fixtures/*.omr.json")):
    winconf=[]; wincls=Counter(); octave=Counter(); nullclef=Counter()
    for f in fixtures(pat):
        d=json.load(open(f))
        for pg in d.get("pages",[]):
            for sy in pg.get("systems",[]):
                for st in sy.get("staves",[]):
                    if st.get("clef_source") is None:
                        nullclef[st.get("clef")]+=1
                    for m in st.get("measures",[]):
                        cd=[x for x in m.get("detections",[]) if x.get("category")=="clef"]
                        for x in m.get("detections",[]):
                            if x.get("class") in ("clef8","clef15"): octave[x["class"]]+=1
                        if cd:
                            cd.sort(key=lambda x:-(x.get("confidence") or 0))
                            winconf.append(cd[0]["confidence"]); wincls[cd[0]["class"]]+=1
    winconf.sort(); n=len(winconf); q=lambda p: round(winconf[int(p*n)],3)
    print(f"=== {fam}: winning clef detections n={n}")
    print(f"   conf p10={q(.10)} p25={q(.25)} median={q(.5)} p75={q(.75)}")
    for t in (0.3,0.4,0.5,0.6):
        print(f"   winners under {t}: {sum(1 for c in winconf if c<t)}")
    print("   winning classes:", dict(wincls.most_common()))
    print("   octave markers detected:", dict(octave))
    print("   staves with clef_source None -> positional default:", dict(nullclef))
