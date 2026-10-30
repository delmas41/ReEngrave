import json, collections
W = 'out/lane-report/whole-rest-m2/work/'
for pl in ('litolff', 'brahms'):
    off = json.load(open(W + pl + '.off.owner.json'))
    on = json.load(open(W + pl + '.on.owner.json'))
    print(pl, 'cells with an owner verdict OFF/ON', len(off), len(on))
    trans = collections.Counter()
    changed_cells = collections.defaultdict(list)
    for cell, o in on.items():
        f = off.get(cell, {'strokes': {}, 'boxes': {}})
        keys = set(o['strokes']) | set(f['strokes'])
        for k in keys:
            a = f['strokes'].get(k)
            b = o['strokes'].get(k)
            fa = (a[0], a[1]) if a else None
            fb = (b[0], b[1]) if b else None
            if fa != fb:
                trans[(fa, fb)] += 1
                changed_cells[cell].append((k, fa, fb))
    print(' strokes whose owner changed ON vs OFF:', sum(trans.values()), 'in', len(changed_cells), 'cells')
    for k, n in trans.most_common():
        print('   ', k, n)
    # which families took the strokes a whole rest now claims
    wr = collections.Counter()
    for cell, o in on.items():
        for k, s in o['strokes'].items():
            if s[1] == 'whole_rest':
                wr[s[0]] += 1
    print(' strokes owned by whole_rest ON:', dict(wr))
    # boxes refused/contested in ON, not in OFF
    nb = collections.Counter()
    ex = []
    for cell, o in on.items():
        f = off.get(cell, {'boxes': {}})
        for bk, bv in o['boxes'].items():
            if bk not in f['boxes'] or f['boxes'][bk][0] != bv[0]:
                nb[(bv[0], tuple(sorted(set(str(x[2]) for x in bv[1]))))] += 1
                ex.append((cell, bk, bv))
    print(' boxes newly refused/contested ON:', dict(nb))
    for e in ex[:10]:
        print('    ', e)
    json.dump({c: v for c, v in list(changed_cells.items())}, open(W + pl + '.owner-changes.json', 'w'))
