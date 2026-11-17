import shutil
S = '/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-session-placeholder-setup-6802ad/c91823fb-6cde-4194-b762-519aca0451f9/scratchpad/'
for src, dst in (('off', 'base'), ('on', 'write')):
    for e in ('record.json', 'musicxml', 'report.json'):
        shutil.copy(S + 'arms_brahms/%s.%s' % (src, e), S + 'arms3/brahms.%s.%s' % (dst, e))
print('ok')
