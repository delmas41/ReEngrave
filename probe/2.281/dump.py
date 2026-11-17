import sys, json
sys.path.insert(0, '/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a6fffc49b728dc7cd/probe/2.274-r3')
from load import printed
P, H = printed()
for p in P:
    print(p['n'], p['staff'], p['kind'], p['cls'], [tuple(round(v) for v in r) for r in p['rects']], p['ids'])
