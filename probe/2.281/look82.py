import sys, json
sys.path.insert(0, '/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a6fffc49b728dc7cd/benchmarks/omr-arc-binding-2026-10')
import tiles_281 as T
D = '/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-session-placeholder-setup-6802ad/c91823fb-6cde-4194-b762-519aca0451f9/scratchpad/arms3/'
for arm in ('write', 'meet'):
    b, r, runs = T.load(D + 'brahms.%s.record.json' % arm)
    for k in [k for k in runs if k[1] in (82, 83, 21, 93)]:
        e = runs[k]
        print(arm, k, e['status'], e.get('why'), e.get('witnesses'), json.dumps(e.get('unbound'))[:200])
