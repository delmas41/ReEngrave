import json, glob, os
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from fixture_root import fixture_glob  # noqa: E402  (see fixture_root.py)
from collections import Counter
for fam,files in (("scan", fixture_glob('benchmarks/omr-scan-e2e-2026-09/fixtures/*..graft09.omr.json', 'scan transcriptions')),
                  ("engraved", fixture_glob('benchmarks/omr-orchestral-e2e/fixtures/*.omr.json', 'engraved transcriptions'))):
    ok=refuse=0; rows=[]; frag=0; joined=0
    for f in files:
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
