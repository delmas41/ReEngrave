import json, sys
sys.path.insert(0, '/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-ab22b9e5e1af96e0b/benchmarks/omr-arc-binding-2026-10/deep-dive-2026-11')
from slim import slim_verdict
p = sys.argv[1]
d = json.load(open(p))
d['verdicts'] = [slim_verdict(v) if 'considered' in v else v for v in d['verdicts']]
json.dump(d, open(p, 'w'), default=str)
print('slimmed', p)
