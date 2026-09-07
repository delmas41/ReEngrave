import json, glob, os
from collections import Counter
for fam,pat in (("scan",'benchmarks/omr-scan-e2e-2026-09/fixtures/*..graft09.omr.json'),
                ("engraved",'benchmarks/omr-orchestral-e2e/fixtures/*.omr.json')):
    rev=0; meas=0; warned=0; sev=Counter(); recon=0; pages=0
    for f in sorted(glob.glob(pat)):
        d=json.load(open(f))
        recon+=d.get('n_rhythm_reconciliations',0)
        for pg in d["pages"]:
            pages+=1
            rev+=pg.get('uncorroborated_meter_changes_reverted',0)
            for sy in pg["systems"]:
                for st in sy["staves"]:
                    for m in st.get("measures",[]):
                        meas+=1
                        w=m.get("rhythm_sum_warning")
                        if w:
                            warned+=1
                            sev[(w.get("severity") if isinstance(w,dict) else "?")]+=1
    print(f"=== {fam}: {pages} pages, {meas} measures")
    print(f"   uncorroborated meter changes REVERTED: {rev}")
    print(f"   rhythm_reconciliations: {recon}")
    print(f"   measures carrying rhythm_sum_warning: {warned} ({warned/max(meas,1):.1%})  severity {dict(sev)}")
