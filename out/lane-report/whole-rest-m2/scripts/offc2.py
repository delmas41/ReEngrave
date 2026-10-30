import json
W = 'out/lane-report/whole-rest-m2/work/'
cand = {'litolff': ['glyph/9/1/1/5/2', 'glyph/8/0/0/13/5', 'glyph/2/0/10/0/1', 'glyph/6/1/0/1/14', 'glyph/6/1/0/0/2', 'glyph/10/0/0/9/2',
                    'glyph/10/0/0/10/3', 'glyph/10/0/0/12/2', 'glyph/11/0/2/4/5'],
        'brahms': ['glyph/8/1/6/0/12', 'glyph/12/1/1/6/11', 'glyph/12/1/1/6/13', 'glyph/14/1/11/1/0', 'glyph/14/1/11/1/6', 'glyph/0/0/4/6/6']}
for pl, subs in cand.items():
    arms = {}
    for a in ('off', 'on'):
        d = json.load(open(W + '%s.%s.symbols.json' % (pl, a)))
        arms[a] = {h.get('rg'): h for h in d['hosts']}
    # also boxes
    d = json.load(open(W + '%s.on.mini-record.json' % pl))
    bx = {o['subject']: o for o in d['observations'] if o['quantity'] == 'glyph_box'}
    for s in subs:
        o = bx.get(s)
        print(pl, s, 'OFF written' if s in arms['off'] else 'OFF -', '| ON', ('written blue=%s measure=%s' % (arms['on'][s]['blue'], arms['on'][s]['measure'])) if s in arms['on'] else '-',
              o['value'][0] if o else None, (o['detail'] or {}).get('bbox_page_px') if o else None)
