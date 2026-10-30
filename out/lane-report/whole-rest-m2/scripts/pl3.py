import json, collections
W = 'out/lane-report/whole-rest-m2/work/'
M1 = '/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-ae06367b155a69fa2/out/lane-report/whole-rest-m1/work/'
def cellkey(s):
    p = s.split('/')
    return tuple(p[1:5])
for pl in ('litolff', 'brahms'):
    fs = set()
    for l in open('library/_shared-records/lane-report-slices-wr1029/%s/observations.jsonl' % pl):
        if '"empty_bar_rest_search"' in l:
            o = json.loads(l)
            if o.get('value'):
                fs.add(cellkey(o['subject']))
    for tag, base in (('m2', W), ('m1', M1)):
        off = json.load(open(base + pl + '.off.symbols.json'))['hosts']
        on = json.load(open(base + pl + '.on.symbols.json'))['hosts']
        offrg = collections.Counter(h.get('rg') for h in off if h['kind'] == 'rest')
        newh = []
        for h in on:
            if h['kind'] != 'rest':
                continue
            if offrg[h.get('rg')] > 0:
                offrg[h.get('rg')] -= 1
            else:
                newh.append(h)
        c = collections.Counter(('in a found-search bar' if cellkey(h['rg']) in fs else 'other (ink-rescued)', 'blue' if h['blue'] else 'plain') for h in newh)
        print(pl, tag, len(newh), dict(c))
