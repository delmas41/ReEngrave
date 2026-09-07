import json, glob, os
from collections import Counter
tot=Counter(); rejected=[]; conflicts=[]; readers=Counter(); bywin=Counter(); eng=Counter()
rows=0
for f in sorted(glob.glob('benchmarks/omr-scan-e2e-2026-09/fixtures/*..graft09.omr.json')):
    d=json.load(open(f)); dt=d.get('direction_text') or {}
    if not dt.get('available'): continue
    rows+=1
    tot['n_placed']+=dt.get('n_placed',0)
    for pg in dt.get('pages',[]):
        for k in ('n_candidates','n_read','n_accepted'): tot[k]+=pg.get(k,0)
        rejected += pg.get('rejected',[])
        conflicts += pg.get('conflicts',[])
        for r in pg.get('readers',[]) or []: readers[r]+=1
        for k,v in (pg.get('by_reader') or {}).items(): bywin[k]+=v
        eng[pg.get('page_is_engraved')]+=1
        if pg.get('reason'): tot['reason:'+pg['reason']]+=1
print('rows with a report:',rows)
print('FUNNEL:', dict(tot))
print('readers present per page:', dict(readers), ' page_is_engraved:', dict(eng))
print('winning reader (by_reader):', dict(bywin))
print('CONFLICTS between rungs:', len(conflicts))
for c in conflicts[:15]: print('   ', c)
print('REJECTED strings (lexicon refused):', len(rejected))
c=Counter(r.strip() for r in rejected)
for k,v in c.most_common(40): print(f'   {v:3d}  {k!r}')
