import sys, json, collections; sys.path.insert(0, sys.argv[1]); from readers import *
for plate in ('litolff','brahms'):
    d, sym = load(plate); H, C, S = d['heads'], d['cells'], d['strokes']
    file = {}
    for h in sym['hosts']:
        if h['kind'] == 'note': file[h['rg']] = 'H' if h['type'] in ('half','whole','breve') else 'F'
    t = collections.Counter(); hb = collections.defaultdict(list); nb = collections.Counter(); sizes=collections.Counter()
    for gs, g in H.items():
        D = det(g['box'][0]); sl = slit(g)[0]; wi = win(g)[0]; f = file.get(gs, '-')
        t[(D, sl, wi, f)] += 1
        bl = [s for s in head_blob(gs, g, S) if s['k']=='blob']
        nb[len(bl)] += 1
        if bl:
            b = max(bl, key=lambda s: s['box'][2]*s['box'][3]); hb[(D,f)].append(b['hole'])
    print(plate, 'blobs per head', sorted(nb.items())[:8])
    for k, v in sorted(hb.items()):
        v = sorted(x for x in v if x is not None); n=len(v)
        print(' hole_share', k, n, 'zero', sum(1 for x in v if x==0), 'q25/50/75', v[n//4] if n else None, v[n//2] if n else None, v[3*n//4] if n else None, '>=.1', sum(1 for x in v if x>=.1))
    print(' (DET,SLIT,WIN,FILE) top:')
    for k, v in t.most_common(30): print('  ', k, v)
