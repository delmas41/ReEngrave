import json
spec = []
for plate in ('brahms', 'litolff'):
    d = json.load(open('/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a26d61ddc53de8906/out/lane-report/2.235/work/%s.diff.json' % plate))
    for x in d.get('lost_note', []):
        spec.append(dict(plate=plate, page=x['page'], boxes=[x['box']], name='lost_' + plate + '_' + x['rg'].replace('/', '_'), pad=200))
json.dump(spec, open('/private/tmp/claude-501/lostspec.json', 'w'))
print(spec)
