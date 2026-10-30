import json, collections, sys
W = '/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-ae06367b155a69fa2/out/lane-report/whole-rest-m1/work/'
for pl in ('litolff', 'brahms'):
    arms = {a: json.load(open(W + '%s.%s.mini-record.json' % (pl, a))) for a in ('off', 'on')}
    obs = {o['subject']: o for o in arms['on']['observations'] if o['quantity'] == 'glyph_box'}
    vs = {}
    for a in arms:
        vs[a] = {}
        for v in arms[a]['verdicts']:
            if v['quantity'] == 'notehead_is_not_a_notehead':
                vs[a][v['subject']] = v
    if pl == 'litolff':
        print(list(vs['on'].values())[0])
        print(list(obs.values())[0])
    reasons = {a: collections.Counter(v.get('reason') for v in vs[a].values()) for a in vs}
    print(pl, 'claimed_by:whole_rest OFF', reasons['off'].get('claimed_by:whole_rest', 0), 'ON', reasons['on'].get('claimed_by:whole_rest', 0))
    allr = set(reasons['off']) | set(reasons['on'])
    for r in sorted(allr, key=str):
        a, b = reasons['off'].get(r, 0), reasons['on'].get(r, 0)
        if a != b:
            print('   ', r, a, '->', b)
    # per box transitions
    trans = collections.Counter()
    for s, v in vs['on'].items():
        o = vs['off'].get(s)
        if o is None:
            continue
        if (o.get('outcome'), o.get('reason')) != (v.get('outcome'), v.get('reason')):
            trans[((o.get('outcome'), o.get('reason')), (v.get('outcome'), v.get('reason')))] += 1
    for k, n in trans.most_common():
        print('   ', k, n)
    cls = collections.Counter()
    for s, v in vs['on'].items():
        if v.get('reason') == 'claimed_by:whole_rest':
            o = obs.get(s)
            cls[(o or {}).get('value', [None])[0] if o else None] += 1
    print('  by class', cls)
