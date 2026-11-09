import sys, json, collections
sys.path.insert(0, '/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a6fffc49b728dc7cd/benchmarks/omr-arc-binding-2026-10')
import tiles_281 as T
D = '/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-session-placeholder-setup-6802ad/c91823fb-6cde-4194-b762-519aca0451f9/scratchpad/arms3/'
for plate in ('brahms', 'litolff'):
    for arm in ('write', 'meet'):
        b, r, runs = T.load(D + '%s.%s.record.json' % (plate, arm))
        c = collections.Counter()
        why = collections.Counter()
        for k, e in runs.items():
            st = e['status']
            c[(k[0], st)] += 1
            if st == 'abstained':
                why[(k[0], e.get('why'))] += 1
            for u in (e.get('unbound') or {}).values():
                if (u or {}).get('unbound') == 'continues_in_another_curve':
                    c[(k[0], 'cont_end')] += 1
        print(plate, arm, dict(sorted(c.items())))
        print('   why', dict(sorted(why.items())))
