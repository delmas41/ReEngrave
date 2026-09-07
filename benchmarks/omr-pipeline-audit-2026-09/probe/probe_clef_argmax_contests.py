import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fixtures import fixtures, root, chdir_root, SCAN, ENGRAVED, CONTESTS  # fail-loud
chdir_root()

import json, glob, os
from collections import Counter
FAM={"scan":sorted(fixtures(SCAN, expect_at_least=11)),
     "engraved":sorted(fixtures(ENGRAVED, expect_at_least=11))}
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
