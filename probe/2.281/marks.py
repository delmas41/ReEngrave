import sys, json
sys.path.insert(0, '/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a6fffc49b728dc7cd/probe/2.274-r3')
from load import marks
M, H, pa = marks()
B = json.load(open('/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a6fffc49b728dc7cd/probe/2.274-r3/buckets.json'))
print(len(pa), len(M))
for m in M:
    if len(m['members']) > 1 or m['rel']:
        print(m['n'], m['members'], m['staff'], m['kinds'], round(m['x0']), round(m['x1']), m['rel'])
print('---- open arcs and their page-ink runs (run extents in px)')
for r in B:
    if r['open_L'] or r['open_R']:
        runs = [(x['ordinal'], round(x['run_x0']), round(x['run_x1']), x['cov']) for x in r['runs'][:3]]
        print(r['n'], r['staff'], r['kind'], r['x0'], r['x1'], 'L' if r['open_L'] else '-', 'R' if r['open_R'] else '-', 'ghost' if r['ghost'] else '', runs)
