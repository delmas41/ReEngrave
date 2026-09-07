import json, glob, os
from collections import Counter
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
# ⚠️ TWO roots, not one: `repo_glob` reads COMMITTED artefacts from the tree
# this probe lives in (reading them from elsewhere is the M4 defect);
# `fixture_glob` reads GITIGNORED build products, which exist only in the
# main checkout. Both exit 2 on an empty glob. See fixture_root.py.
from fixture_root import fixture_glob, repo_glob  # noqa: E402
FAM={"scan": fixture_glob("benchmarks/omr-scan-e2e-2026-09/fixtures/*..graft09.omr.json", "scan transcriptions"),
     "engraved": fixture_glob("benchmarks/omr-orchestral-e2e/fixtures/*.omr.json", "engraved transcriptions")}
for fam,files in FAM.items():
    print("===",fam)
    pairs=Counter(); midstaff=0; firstcell=0; changes=[]
    for f in files:
        d=json.load(open(f)); nm=os.path.basename(f).split('.')[0]
        for pg in d.get("pages",[]):
            for sy in pg.get("systems",[]):
                for st in sy.get("staves",[]):
                    seen=[]
                    for i,m in enumerate(st.get("measures",[])):
                        cd=[x for x in m.get("detections",[]) if x.get("category")=="clef"]
                        if cd:
                            if i==0: firstcell+=1
                            else: midstaff+=1
                        if len(cd)>=2:
                            cd.sort(key=lambda x:-(x.get("confidence") or 0))
                            if cd[0]["class"]!=cd[1]["class"]:
                                pairs[(cd[0]["class"],round(cd[0]["confidence"],2),
                                       cd[1]["class"],round(cd[1]["confidence"],2))]+=1
                        if m.get("clef"): seen.append(m["clef"])
                    if len(set(seen))>1:
                        changes.append((nm,st.get("staff_index"),st.get("clef_source"),
                                        st.get("instrument"),seen[:8]))
    print(" cells with a clef det: first cell of staff =",firstcell," LATER cell =",midstaff)
    print(" different-class argmax pairs (winner, conf, runner-up, conf):")
    for k,v in pairs.most_common(14): print("   ",k,"x",v)
    print(" staves with a mid-staff clef CHANGE:")
    for c in changes: print("   ",c)
