import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fixtures import fixtures, root, chdir_root, SCAN, ENGRAVED, CONTESTS  # fail-loud
chdir_root()

import json, glob, os
from collections import Counter
tiers=Counter(); tot=Counter(); rows=0
for f in sorted(fixtures(SCAN, expect_at_least=11)):
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
