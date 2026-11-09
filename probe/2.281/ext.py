import sys, json
B = json.load(open('/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a6fffc49b728dc7cd/probe/2.274-r3/buckets.json'))
SP = 32.0
for r in B:
    runs = [x for x in r['runs'] if x['cov'] >= 0.8]
    if not runs:
        print(r['n'], r['staff'], r['kind'], r['x0'], r['x1'], 'NO RUN', 'ghost' if r['ghost'] else '', 'chain' if r['chain'] else '', r['dup_of'])
        continue
    x = max(runs, key=lambda q: q['cov'])
    eL = (r['x0'] - x['run_x0']) / SP
    eR = (x['run_x1'] - r['x1']) / SP
    flag = ''
    if eL > 1.5: flag += ' EXT_L%.1f' % eL
    if eR > 1.5: flag += ' EXT_R%.1f' % eR
    if (r['open_L'] or r['open_R']) or flag:
        print(r['n'], r['staff'], r['kind'], r['x0'], r['x1'], 'openL' if r['open_L'] else '', 'openR' if r['open_R'] else '', 'run', round(x['run_x0']), round(x['run_x1']), flag)
