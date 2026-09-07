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
def sig(ts):
    # ROUND 3 FIX: the first version read `beats`/`beat_type`, which these dicts
    # do NOT carry -- every meter stringified to "None/None", every staff looked
    # constant, and the probe printed a clean table at exit 0. The assert is the
    # guard against that class of silent failure. (The corrected key reproduces
    # the same VERDICT here -- 0 flips -- but did not on the key signature.)
    if not ts: return None
    assert "numerator" in ts and "denominator" in ts, f"unexpected meter dict: {ts!r}"
    return (ts["numerator"], ts["denominator"], ts.get("symbol"))
for fam,pat in (("scan",'benchmarks/omr-scan-e2e-2026-09/fixtures/*..graft09.omr.json'),
                ("engraved",'benchmarks/omr-orchestral-e2e/fixtures/*.omr.json')):
    src=Counter(); changed=[]; staves=0; final=Counter(); tsfinal=0
    for f in fixtures(pat):
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
