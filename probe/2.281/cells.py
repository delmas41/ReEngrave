import json, collections
t = json.load(open('/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a6fffc49b728dc7cd/data/hand-truth/pages/imslp317803/0.json'))
xs = collections.defaultdict(list)
for c in t['cells']:
    if c['kind'] == 'measure':
        xs[c['staff']].append((c['measure'], round(c['rect'][0]), round(c['rect'][2]), round(c['rect'][1]), round(c['rect'][3])))
for s in sorted(xs)[:14]:
    print(s, sorted(xs[s]))
print(collections.Counter(c['kind'] for c in t['cells']))
