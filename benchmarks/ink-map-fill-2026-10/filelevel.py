import sys, json, collections; sys.path.insert(0, sys.argv[1]); from readers import *
def iou(a, b):
    x0, y0, x1, y1 = max(a[0],b[0]), max(a[1],b[1]), min(a[2],b[2]), min(a[3],b[3])
    if x1 <= x0 or y1 <= y0: return 0.0
    i = (x1-x0)*(y1-y0); return i / ((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - i)
allrows = {}
for plate in ('litolff','brahms'):
    d, sym = load(plate); H, C, S, V = d['heads'], d['cells'], d['strokes'], d['ver']
    notes = {h['rg']: h for h in sym['hosts'] if h['kind']=='note'}
    bycell = collections.defaultdict(list)
    for gs in H: bycell[gs.rsplit('/',1)[0]].append(gs)
    twin = collections.defaultdict(list)
    for L in bycell.values():
        for a in L:
            for b in L:
                if a != b and iou(H[a]['page_box'], H[b]['page_box']) >= .5: twin[a].append(b)
    rows = []
    for gs, g in H.items():
        sp = space(gs, C) or 0
        w = g['box'][3]/sp if sp else 0; h = g['box'][4]/sp if sp else 0
        sized = 0.9 <= h <= 1.8 and 1.1 <= w <= 1.9
        v = V.get(gs, {}); du = v.get('duration', {}); nn = v.get('notehead_is_not_a_notehead', {})
        n = notes.get(gs)
        rows.append(dict(s=gs, det=det(g['box'][0]), slit=slit(g)[0], sv=slit(g)[1], win=win(g)[0], cls=g['box'][0],
                         w=round(w,2), h=round(h,2), sized=sized, online='OnLine' in g['box'][0],
                         twin=[(t, H[t]['box'][0], t in notes) for t in twin.get(gs, [])],
                         file=None if not n else ('H' if n['type'] in ('half','whole') else 'F'), ftype=n and n['type'],
                         blue=n and n.get('blue'), du_o=du.get('o'), du_r=du.get('r'), nn=(nn.get('o'), nn.get('v'), nn.get('r')),
                         hff=du.get('hff'), page_box=g['page_box'], hio=du.get('hio')))
    allrows[plate] = rows
    W = [r for r in rows if r['file']]
    print('==', plate, 'head boxes', len(rows), 'written notes from head boxes', len(W))
    # reader-level pairwise (all boxes): decisive pairs disagreeing
    for a, b in (('det','slit'), ('det','win'), ('slit','win')):
        both = [r for r in rows if r[a] != 'U' and r[b] != 'U']; dis = [r for r in both if r[a] != r[b]]
        print('  reader %s vs %s: both decisive %d, disagree %d (%.1f%%)' % (a, b, len(both), len(dis), 100*len(dis)/max(1,len(both))))
    und = collections.Counter((r['slit'], r['win']) for r in rows if 'U' in (r['slit'], r['win'])); print('  undecided (slit,win):', dict(und))
    # file level
    c = collections.Counter()
    for r in W:
        ink = r['slit'] if r['slit'] == r['win'] else ('U' if 'U' in (r['slit'], r['win']) and r['slit'] != r['win'] and (r['slit']=='U' or r['win']=='U') else 'X')
        if r['slit'] != 'U' and r['win'] == 'U': ink = r['slit'] + '?'
        if r['win'] != 'U' and r['slit'] == 'U': ink = r['win'] + '?'
        c[(r['file'], r['det'], ink)] += 1
    print('  FILE (written, det, ink[slit&win; ?=one only; X=they disagree; U=neither]):')
    for k, v in sorted(c.items()): print('    ', k, v)
json.dump(allrows, open(sys.argv[1] + '/rows.json', 'w'), default=str)
