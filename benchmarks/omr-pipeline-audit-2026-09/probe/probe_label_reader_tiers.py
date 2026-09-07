import json, glob, os
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from fixture_root import fixture_glob  # noqa: E402  (see fixture_root.py)
from collections import Counter
tiers=Counter(); tot=Counter(); rows=0
for f in fixture_glob('benchmarks/omr-scan-e2e-2026-09/fixtures/*..graft09.omr.json', 'scan transcriptions'):
    d=json.load(open(f)); c=d.get('contextual') or {}
    if not c.get('available'): continue
    rows+=1
    for k,v in (c.get('label_tiers') or {}).items(): tiers[k]+=v if isinstance(v,int) else 0
    tot['labelled_staves']+=c.get('labelled_staves',0)
    tot['unresolved']+=len(c.get('unresolved_labels') or [])
    tot['low_conf']+=len(c.get('low_confidence_labels') or [])
    tot['instruments_from_score_order']+=c.get('instruments_from_score_order',0)
print('rows',rows)
print('label_tiers (which reader supplied labels):', dict(tiers))
print(dict(tot))
