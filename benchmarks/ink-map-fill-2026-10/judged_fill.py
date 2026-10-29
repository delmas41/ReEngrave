import sys, json, collections; sys.path.insert(0, sys.argv[1]); from readers import *
idx = json.load(open('/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/plan-ink-map-step6/benchmarks/acceptance/judged-tiles.json'))['tiles']
def iou(a, b):
    x0, y0, x1, y1 = max(a[0],b[0]), max(a[1],b[1]), min(a[2],b[2]), min(a[3],b[3])
    if x1 <= x0 or y1 <= y0: return 0.0
    i = (x1-x0)*(y1-y0); return i / ((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - i)
rows_out = []
for plate in ('litolff','brahms'):
    d, sym = load(plate); H, C, S, V = d['heads'], d['cells'], d['strokes'], d['ver']
    notes = [h for h in sym['hosts'] if h['kind']=='note']
    # twins: another head box in the same cell, IoU >= .5
    bycell = collections.defaultdict(list)
    for gs, g in H.items(): bycell[gs.rsplit('/',1)[0]].append(gs)
    twin = {}
    for c, L in bycell.items():
        for a in L:
            for b in L:
                if a < b and iou(H[a]['page_box'], H[b]['page_box']) >= .5:
                    twin.setdefault(a, []).append(b); twin.setdefault(b, []).append(a)
    seen = set()
    for t in idx:
        if t['doc'] != plate or t['answer_kind'] != 'duration' or t['value'] is None: continue
        s = t['subject']
        if not s or s not in H or not t.get('page_box'): continue
        b = H[s]['page_box']; cx, cy = (b[0]+b[2])/2, (b[1]+b[3])/2; tb = t['page_box']
        if not (tb[0]-40 <= cx <= tb[2]+40 and tb[1]-40 <= cy <= tb[3]+40): continue
        if s in seen: continue
        seen.add(s)
        page = int(s.split('/')[1])
        wr = [h for h in notes if h['page']==page and h['box'][0]-2 <= cx <= h['box'][2]+2 and h['box'][1]-2 <= cy <= h['box'][3]+2]
        truth = 'H' if t['value'] >= 2.0 else 'F'
        f = None if not wr else ('H' if wr[0]['type'] in ('half','whole') else 'F')
        g = H[s]; sp = space(s, C) or 0
        w, h = g['box'][3]/sp if sp else None, g['box'][4]/sp if sp else None
        v = V.get(s, {}).get('duration', {})
        hff = v.get('hff') or {}
        rows_out.append(dict(plate=plate, s=s, truth=truth, file=f, det=det(g['box'][0]), slit=slit(g), win=win(g),
            cls=g['box'][0], w=round(w,2) if w else None, h=round(h,2) if h else None, twin=twin.get(s), hff=hff,
            vo=v.get('o'), vr=v.get('r'), hio=v.get('hio'), item=t['item'], tile=t['tile'], ans=t['answer'], page_box=b,
            twin_cls=[H[x]['box'][0] for x in twin.get(s, [])]))
json.dump(rows_out, open(f'{sys.argv[1]}/judged_fill.json','w'), default=str)
c = collections.Counter((r['plate'], r['truth'], r['file']) for r in rows_out); print(sorted(c.items(), key=str))
