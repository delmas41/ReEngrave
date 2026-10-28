import sys, json, pathlib
sys.path.insert(0, '/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/lane-2.216')
from tools.omr.staged.judged import iter_array
rec, out = sys.argv[1], sys.argv[2]
Q = {'head_stem_reach', 'far_head_owner_ledger', 'ledger_owner_density', 'glyph_box'}
reach, farl, box = {}, {}, {}
for o in iter_array(pathlib.Path(rec), 'observations'):
    q = o['quantity']
    if q == 'head_stem_reach':
        reach[o['subject']] = o['value']
    elif q == 'far_head_owner_ledger':
        farl[o['subject']] = {'v': o['value'], 'cand': o['detail'].get('candidate')}
    elif q == 'glyph_box' and isinstance(o['value'], list) and o['value'] and o['value'][0] not in ('staff',) and o.get('detail', {}).get('bbox_page_px'):
        box[o['subject']] = [o['value'][0], o['detail']['bbox_page_px']]
ver = {}
for v in iter_array(pathlib.Path(rec), 'verdicts'):
    if v['quantity'] != 'glyph_owner': continue
    d = v.get('detail') or {}
    ver[v['subject']] = {'outcome': v['outcome'], 'reason': v.get('reason'), 'value': v.get('value'),
        'stem_owner': d.get('stem_owner'), 'ledger_owner': d.get('ledger_owner'),
        'stem': (d.get('stem') or {}).get('direction') if isinstance(d.get('stem'), dict) else None,
        'stem_agrees': bool(d.get('ledger_note_first', {}) and d.get('stem_agrees')) or bool(d.get('stem_agrees')),
        'against': d.get('against')}
keep = set(ver) | set(reach) | set(farl)
json.dump({'reach': reach, 'farl': farl, 'ver': ver, 'box': {k: box[k] for k in keep if k in box}}, open(out, 'w'))
print(len(reach), len(farl), len(ver), len(box))
