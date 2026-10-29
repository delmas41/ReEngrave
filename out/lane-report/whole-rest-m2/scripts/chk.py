import json
W = 'out/lane-report/whole-rest-m2/work/'
arms = {}
for a in ('off', 'on'):
    d = json.load(open(W + 'brahms.%s.symbols.json' % a))
    arms[a] = d
    print(a, len(d['hosts']), 'loose', len(d['loose']))
    for h in d['hosts']:
        p = (h.get('rg') or '').split('/')
        if p[1:5] == ['14', '1', '11', '1']:
            print('  ', h['rg'], h['kind'], h['measure'], h['pitch'], h.get('blue'))
    for h in d['loose']:
        if str(h).find('glyph/14/1/11/1') >= 0:
            print('  loose', str(h)[:200])
m = json.load(open(W + 'brahms.off.mini-record.json'))
for v in m['verdicts']:
    if v['subject'].startswith('glyph/14/1/11/1/') and v['quantity'] in ('duration', 'notehead_is_not_a_notehead'):
        print('off', v['subject'], v['quantity'], v['outcome'], v['value'], v['reason'])
m = json.load(open(W + 'brahms.on.mini-record.json'))
for v in m['verdicts']:
    if v['subject'].startswith('glyph/14/1/11/1/') and v['quantity'] in ('duration', 'notehead_is_not_a_notehead'):
        print('on', v['subject'], v['quantity'], v['outcome'], v['value'], v['reason'])
for o in m['observations']:
    if o['subject'].startswith('glyph/14/1/11/1/') and o['quantity'] == 'glyph_box':
        print(o['subject'], o['value'][0], [round(x) for x in o['detail']['bbox_page_px']])
