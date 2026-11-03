import json, collections
for pl in "LB":
    d = json.load(open('out/2.255/own_%s_on.json' % pl))['heads']
    first = []; rest = []
    for s, h in d.items():
        c = h['cap']
        if not c.get('rungs'):
            continue
        sp = c['sp']; e = c['edge']
        ys = sorted(abs(r - e) for r in c['rungs'])
        g = [ys[0] / sp] + [(ys[i] - ys[i - 1]) / sp for i in range(1, len(ys))]
        ok = h['got'][0] == 'pos'
        for i, x in enumerate(g):
            (first if i == 0 else rest).append((round(x, 2), ok))
    for nm, l in (('first', first), ('rest', rest)):
        h = collections.Counter((int(x * 10) / 10, ok) for x, ok in l)
        print(pl, nm, len(l), sorted(h.items()))
