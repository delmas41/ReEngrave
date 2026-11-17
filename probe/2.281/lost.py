"""the arcs the flag removes (write -> meet): is each one REPLACED by a meet arc at the same place (a duplicate/twin the page run now owns) or is a printed arc gone?"""
import sys, collections
sys.path.insert(0, '/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a6fffc49b728dc7cd/benchmarks/omr-arc-binding-2026-10')
import score_key as K
D = '/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-session-placeholder-setup-6802ad/c91823fb-6cde-4194-b762-519aca0451f9/scratchpad/arms3'
W = K.written(D, 'brahms.write')
M = K.written(D, 'brahms.meet')
key = lambda s: (s['kind'], s['start'], s['stop'])
mk = {key(s) for s in M}
wk = {key(s) for s in W}
lost = [s for s in W if key(s) not in mk]
gained = [s for s in M if key(s) not in wk]
print('p0 lost', len(lost), 'gained', len(gained))
SP = 32
tw = collections.Counter()
for s in lost:
    rep = [g for g in gained if abs(g['xa'] - s['xa']) <= 1.5 * SP and abs(g['xz'] - s['xz']) <= 1.5 * SP and abs(g['ya'] - s['ya']) <= 4 * SP]
    near_same = [g for g in M if key(g) in mk and key(g) in wk and abs(g['xa'] - s['xa']) <= 1.5 * SP and abs(g['xz'] - s['xz']) <= 1.5 * SP and abs(g['ya'] - s['ya']) <= 4 * SP]
    tag = 'replaced_by_gained' if rep else ('twin_of_kept' if near_same else 'NOTHING_THERE')
    tw[tag] += 1
    print(tag, s['kind'], round(s['xa']), round(s['xz']), round(s['ya']), s['start'], s['stop'])
print(dict(tw))
rows_w = K.score(W)[1]
usedw = {(r[5]['start'], r[5]['stop']) for r in rows_w if r[5]}
rows_m = K.score(M)[1]
usedm = {(r[5]['start'], r[5]['stop']) for r in rows_m if r[5]}
print('lost arcs that satisfied a key arc in write:', sum(1 for s in lost if (s['start'], s['stop']) in usedw), 'of', len(lost))
print('gained arcs that satisfy a key arc in meet:', sum(1 for s in gained if (s['start'], s['stop']) in usedm), 'of', len(gained))
