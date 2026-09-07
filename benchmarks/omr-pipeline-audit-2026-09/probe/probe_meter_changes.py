import json, glob, os
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from fixture_root import fixture_glob  # noqa: E402  (see fixture_root.py)
from collections import Counter
def sig(ts):
    if not ts: return None
    return f"{ts.get('beats')}/{ts.get('beat_type')}" + (f"[{ts['symbol']}]" if ts.get('symbol') else "")
for fam,files in (("scan", fixture_glob('benchmarks/omr-scan-e2e-2026-09/fixtures/*..graft09.omr.json', 'scan transcriptions')),
                  ("engraved", fixture_glob('benchmarks/omr-orchestral-e2e/fixtures/*.omr.json', 'engraved transcriptions'))):
    src=Counter(); changed=[]; staves=0; final=Counter(); tsfinal=0
    for f in files:
        d=json.load(open(f)); nm=os.path.basename(f).split('.')[0]
        for pg in d["pages"]:
            for sy in pg["systems"]:
                for st in sy["staves"]:
                    staves+=1
                    ts=st.get("time_signature")
                    src[(ts or {}).get("source")]+=1
                    if st.get("time_signature_final") is not None: tsfinal+=1
                    seq=[sig(m.get("time_signature")) for m in st.get("measures",[])]
                    seen=[x for x in seq if x]
                    if len(set(seen))>1:
                        changed.append((nm, st["staff_index"], st.get("instrument"),
                                        sig(ts), seq[:9]))
    print(f"=== {fam}: {staves} staves")
    print("   staff time_signature.source:", dict(src))
    print("   staves carrying time_signature_final:", tsfinal)
    print("   staves whose per-measure meter CHANGES:", len(changed))
    for c in changed[:14]: print("     ", c)
