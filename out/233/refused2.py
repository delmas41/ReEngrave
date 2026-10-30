import json, sys, collections
rows = {r['sub']: r for r in json.load(open(sys.argv[2]))['rows'] if r['fate'] == 'duration_narrowed' and r['reason'] == 'beam_discounted_uncertain'}
c = collections.Counter()
chord = collections.Counter()
with open(sys.argv[1]) as f:
    for line in f:
        if '"duration"' not in line:
            continue
        v = json.loads(line)
        if v['subject'] not in rows or v['quantity'] != 'duration':
            continue
        d = v.get('detail') or {}
        rs = d.get('refused_strokes') or []
        tip = sorted({x['why'] for x in rs if x.get('at_tip')})
        c[('at_tip:' + ','.join(tip)) if tip else 'no refused stroke at tip'] += 1
        c['ALL cands=' + '/'.join(str(x['value']['beats']) for x in v.get('candidates') or [])] += 1
        c['dots=' + str(d.get('dots_attached'))] += 1
        c['stems_attached=%s' % d.get('stems_attached')] += 1
for k, n in sorted(c.items(), key=lambda x: (x[0].split(':')[0].split('=')[0], -x[1])):
    print(n, k)
