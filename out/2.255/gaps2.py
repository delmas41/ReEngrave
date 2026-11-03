import json, collections, statistics as st
d = json.load(open('out/2.255/own_L_on.json'))['heads']
by = collections.defaultdict(list)
for s, h in d.items():
    c = h['cap']
    if h['got'][0] != 'pos' or not c.get('rungs'):
        continue
    p = s.split('/')
    sp = c['sp']; e = c['edge']
    ys = sorted(abs(r - e) for r in c['rungs'])
    k = c['nf'].get('k')
    by[(p[1], p[2])].append(round(ys[0] / sp, 2))
for k in sorted(by):
    v = by[k]
    print(k, len(v), 'median', st.median(v), 'min', min(v), 'max', max(v), sorted(v))
