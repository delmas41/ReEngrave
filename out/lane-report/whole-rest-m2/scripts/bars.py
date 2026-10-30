import json
W = 'out/lane-report/whole-rest-m2/work/'
want = {(2, 1, 3, 0), (11, 0, 2, 4)}
for arm in ('off', 'on'):
    d = json.load(open(W + 'litolff.%s.symbols.json' % arm))
    if arm == 'off':
        print(d['hosts'][0])
    for h in d['hosts']:
        if (h.get('page'), h.get('system'), h.get('staff'), h.get('cell')) in want:
            print(arm, {k: h[k] for k in h if k in ('page', 'system', 'staff', 'cell', 'kind', 'glyph', 'type', 'value', 'color', 'guess', 'pitch', 'duration', 'box')})
# glyph boxes in those cells
d = json.load(open(W + 'litolff.on.mini-record.json'))
for o in d['observations']:
    if o['quantity'] != 'glyph_box':
        continue
    p = o['subject'].split('/')
    if len(p) >= 5 and (int(p[1]), int(p[2]), int(p[3]), int(p[4])) in want:
        print(o['subject'], o['value'], o['detail'].get('bbox_page_px'))
vs = {}
for arm in ('off', 'on'):
    d = json.load(open(W + 'litolff.%s.mini-record.json' % arm))
    for v in d['verdicts']:
        p = v['subject'].split('/')
        if len(p) >= 5 and (int(p[1]), int(p[2]), int(p[3]), int(p[4])) in want and v['quantity'] in ('duration', 'notehead_is_not_a_notehead'):
            print(arm, v['subject'], v['quantity'], v['outcome'], v['value'], v['reason'])
