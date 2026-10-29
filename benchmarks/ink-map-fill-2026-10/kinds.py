import sys, json, collections; sys.path.insert(0, sys.argv[1]); from readers import *
for plate in ('litolff','brahms'):
    d, sym = load(plate); H, C, S = d['heads'], d['cells'], d['strokes']
    file = {h['rg']: ('H' if h['type'] in ('half','whole') else 'F') for h in sym['hosts'] if h['kind']=='note'}
    for want in ('H','F'):
        comp = collections.Counter(); cover = []; nhole=0; n=0; line=collections.Counter()
        for gs, g in H.items():
            if file.get(gs) != want: continue
            n += 1
            st = head_blob(gs, g, S)
            comp[tuple(sorted(collections.Counter(s['k'] for s in st).items()))] += 1
            bl = [s for s in st if s['k']=='blob']
            x,y,w,h = g['box'][1:]
            if bl:
                b = max(bl, key=lambda s: s['box'][2]*s['box'][3])
                cover.append(round(b['box'][2]*b['box'][3]/float(w*h),1))
            line['OnLine' in g['box'][0]] += 1
        print(plate, 'file', want, n, 'online', dict(line))
        for k,v in comp.most_common(8): print('   ', k, v)
        print('   largest blob bbox / head box area:', sorted(collections.Counter(cover).items()))
