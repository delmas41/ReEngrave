import sys
sys.path.insert(0, '/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a6fffc49b728dc7cd/benchmarks/omr-arc-binding-2026-10')
import score_key as K
D = '/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-session-placeholder-setup-6802ad/c91823fb-6cde-4194-b762-519aca0451f9/scratchpad/arms3'
want = sys.argv[1]
k = [a for a in K.KEY['arcs'] if a['id'] == want][0]
print(k['id'], k['kind'], k['x0'], k['x1'], k['y0'], k['y1'])
for arm in ('brahms.write', 'brahms.meet'):
    print(arm)
    for s in K.written(D, arm):
        if abs(s['xa'] - k['x0']) < 200 and abs(s['xz'] - k['x1']) < 250 and K.yd(s['ya'], k['y0'], k['y1']) < 250:
            print('  ', s['kind'], round(s['xa']), round(s['xz']), round(s['ya']), round(s['yz']), s['start'], s['stop'])
