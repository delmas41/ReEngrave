import json, glob, os
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
# ⚠️ TWO roots, not one: `repo_glob` reads COMMITTED artefacts from the tree
# this probe lives in (reading them from elsewhere is the M4 defect);
# `fixture_glob` reads GITIGNORED build products, which exist only in the
# main checkout. Both exit 2 on an empty glob. See fixture_root.py.
from fixture_root import fixture_glob, repo_glob  # noqa: E402
files=fixture_glob("benchmarks/omr-scan-e2e-2026-09/fixtures/*..graft09.omr.json", "scan transcriptions")
tot_flip=0; blocked_at={0.3:0,0.4:0,0.5:0,0.6:0,0.7:0,0.8:0}
for f in files:
    d=json.load(open(f)); nm=os.path.basename(f).split('.')[0]
    for pg in d.get("pages",[]):
        for sy in pg.get("systems",[]):
            for st in sy.get("staves",[]):
                ms=st.get("measures",[])
                seen=[m.get("clef") for m in ms]
                if len(set(x for x in seen if x))<2: continue
                print(f"-- {nm} staff {st.get('staff_index')} inst={st.get('instrument')} "
                      f"staff.clef={st.get('clef')} src={st.get('clef_source')}")
                prev=None
                for i,m in enumerate(ms):
                    c=m.get("clef")
                    cd=[x for x in m.get("detections",[]) if x.get("category")=="clef"]
                    if c!=prev and prev is not None:
                        tot_flip+=1
                        best=max((x.get('confidence') or 0) for x in cd) if cd else None
                        print(f"    m{i}: {prev} -> {c}  clefdets="
                              f"{[(x['class'],round(x['confidence'],2)) for x in cd]}")
                        if best is not None:
                            for t in blocked_at:
                                if best < t: blocked_at[t]+=1
                    prev=c
print("\nmid-staff clef flips:",tot_flip)
print("would be blocked by a confidence floor at:",blocked_at)
