import json, glob, os
from collections import Counter
for fam,pat in (("scan",'benchmarks/omr-scan-e2e-2026-09/fixtures/*..graft09.omr.json'),
                ("engraved",'benchmarks/omr-orchestral-e2e/fixtures/*.omr.json')):
    ok=refuse=0; rows=[]; frag=0; joined=0
    for f in sorted(glob.glob(pat)):
        d=json.load(open(f)); nm=os.path.basename(f).split('.')[0]
        counts=[len(sy["staves"]) for pg in d["pages"] for sy in pg["systems"]]
        n_sys=len(counts)
        if n_sys<=1:
            ok+=1; joined+=counts[0] if counts else 0; continue
        if len(set(counts))==1:
            ok+=1; joined+=counts[0]
        else:
            refuse+=1; frag+=sum(counts)
            rows.append((nm, counts))
    print(f"=== {fam}: rows where _stitch_slots JOINS = {ok}, REFUSES = {refuse}")
    print(f"   parts emitted: {joined} continuous (joined rows) + {frag} per-system fragments (refused rows)")
    for r in rows: print("    refused:", r)
