"""(ii) head boxes ADJUDICATE refuses that still claim strokes; (iii) system arcs whose trace does not bow; (iv) narrow-rest blockers."""
import json, collections, sys
S = '/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261029-night'
PAGES = {'litolff': {2, 4, 6, 8, 9, 10, 11, 16}, 'brahms': {0, 4, 5, 8, 12, 14, 19, 25}}
d = json.load(open(sys.argv[1]))
for plate, pages in PAGES.items():
    rows = {r['g']: r for r in d[plate]}
    gs = {}; arcs = []; nrs = []
    for l in open(f'{S}/{plate}/observations.jsonl'):
        if '"glyph_strokes"' in l[:200]:
            o = json.loads(l)
            if o['subject'] in rows and o['value']: gs[o['subject']] = o['value']
        elif '"system_arc"' in l[:200]:
            o = json.loads(l)
            if int(o['subject'].split('/')[1]) in pages: arcs.append(o)
        elif '"narrow_box_shape"' in l[:200]:
            o = json.loads(l)
            if int(o['subject'].split('/')[1]) in pages: nrs.append(o)
    ref = collections.Counter(); refc = collections.Counter()
    for g, r in rows.items():
        if r['cls'].lower().startswith('notehead') and r['nh'] and r['nh'][0] == 'decided' and r['nh'][1] is True:
            ref[r['nh'][2]] += 1
            if g in gs: refc[r['nh'][2]] += 1
    print('==', plate, 'refused head boxes by reason (all / still claiming strokes):')
    for k in ref: print('   %-40s %5d %5d' % (k, ref[k], refc[k]))
    # (iii) bow of the system arc trace: max |centre - chord| in spaces
    straight = 0; tot = 0; ex = []
    for o in arcs:
        t = (o.get('detail') or {}).get('trace') or []
        sp = (o.get('detail') or {}).get('space_page_px') or 0
        if len(t) < 10 or not sp: continue
        tot += 1
        xs = [p[0] for p in t]; cs = [(p[1] + p[2]) / 2 for p in t]
        x0, x1, c0, c1 = xs[0], xs[-1], cs[0], cs[-1]
        dev = max(abs(c - (c0 + (c1 - c0) * (x - x0) / max(1, x1 - x0))) for x, c in zip(xs, cs)) / sp
        width = (x1 - x0) / sp
        if width >= 3 and dev < 0.15:
            straight += 1; ex.append((o['subject'], round(width, 1), round(dev, 2), (o['detail'] or {}).get('piece_classes')))
    print('   system arcs traced %d, >=3 sp wide with bow < 0.15 sp: %d' % (tot, straight))
    for e in ex[:8]: print('     ', e)
    print('   narrow boxes measured', len(nrs))
