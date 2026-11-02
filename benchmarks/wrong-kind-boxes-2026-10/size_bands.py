import json, collections, sys
d = json.load(open(sys.argv[1]))
def band(x, cuts):
    for c in cuts:
        if x < c: return '<%.2f' % c
    return '>=%.2f' % cuts[-1]
for plate, rows in d.items():
    heads = [r for r in rows if r['cls'].lower().startswith('notehead')]
    print('==', plate, len(heads), 'with nh verdict', sum(1 for r in heads if r['nh']))
    for key, cuts in (('w', [0.5, 0.75, 0.9, 1.0, 1.6, 2.0, 2.5, 3.0]), ('h', [0.5, 0.65, 0.75, 0.85, 1.4, 1.7, 2.0, 2.5])):
        c = collections.Counter(); kept = collections.Counter()
        for r in heads:
            b = band(r[key], cuts); c[b] += 1
            if r['nh'] and r['nh'][0] == 'decided' and r['nh'][1] is False: kept[b] += 1
        print(' ', key, [(b, c[b], kept[b]) for b in sorted(c, key=lambda s: (s[0] != '<', float(s.lstrip('<>='))))])
    # the four
    for r in rows:
        if r['g'] in ('glyph/10/1/9/7/12', 'glyph/4/0/8/5/8', 'glyph/5/0/4/4/15', 'glyph/19/0/9/1/17'):
            print('  CASE', r['g'], r['cls'], round(r['w'], 2), round(r['h'], 2), round(r['conf'], 3), r['nh'], r['arc'])
