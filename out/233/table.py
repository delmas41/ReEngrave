import json, collections
S = {'lit': [2, 4, 6, 8, 9, 10, 11, 16], 'bra': [0, 4, 5, 8, 12, 14, 19, 25]}
for pl in ('lit', 'bra'):
    d = json.load(open('/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a85d4443ac64d554a/out/233/%s.c2.json' % pl))
    n = len(S[pl])
    c = collections.Counter()
    for r in d['rows']:
        pg = int(r['sub'].split('/')[1])
        if pg not in S[pl]:
            continue
        f = r['fate']
        kind = 'REST' if f.startswith('rest_') else ('NO_PITCH' if f == 'no_pitch' else 'HEAD')
        c[(kind, f, r['reason'])] += 1
    print(pl, 'pages', n)
    tot = collections.Counter()
    for (k, f, rs), v in sorted(c.items(), key=lambda x: (x[0][0], -x[1])):
        tot[k] += v
        print('  %-8s %-26s %-48s %4d  %.1f/pg' % (k, f, rs, v, v / n))
    print('  totals', dict(tot), {k: round(v / n, 1) for k, v in tot.items()})
