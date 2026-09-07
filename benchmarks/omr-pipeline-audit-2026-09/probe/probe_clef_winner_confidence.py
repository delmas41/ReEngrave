import json, glob, os
from collections import Counter
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
# ⚠️ TWO roots, not one: `repo_glob` reads COMMITTED artefacts from the tree
# this probe lives in (reading them from elsewhere is the M4 defect);
# `fixture_glob` reads GITIGNORED build products, which exist only in the
# main checkout. Both exit 2 on an empty glob. See fixture_root.py.
from fixture_root import fixture_glob, repo_glob  # noqa: E402
for fam,files in (("scan", fixture_glob("benchmarks/omr-scan-e2e-2026-09/fixtures/*..graft09.omr.json", "scan transcriptions")),
                  ("engraved", fixture_glob("benchmarks/omr-orchestral-e2e/fixtures/*.omr.json", "engraved transcriptions"))):
    winconf=[]; wincls=Counter(); octave=Counter(); nullclef=Counter()
    for f in files:
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
