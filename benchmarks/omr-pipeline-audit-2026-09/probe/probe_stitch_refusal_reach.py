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
for fam,pat in (("scan",'benchmarks/omr-scan-e2e-2026-09/fixtures/*..graft09.omr.json'),
                ("engraved",'benchmarks/omr-orchestral-e2e/fixtures/*.omr.json')):
    ok=refuse=0; rows=[]; frag=0; joined=0
    for f in fixtures(pat):
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
