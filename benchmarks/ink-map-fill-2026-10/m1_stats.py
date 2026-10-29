import json, sys, collections
import numpy as np
S = '/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-agent-manager-workflow-356c39/7e1ea73e-2fd3-4d6c-a450-36868f7e14c0/scratchpad'
plate = sys.argv[1]
pages = [int(p) for p in sys.argv[2].split(',')]
rows = [r for r in json.load(open(f'{S}/m_{plate}.json')) if r['p'] in pages]
for name, w in (('halves', 2.0), ('quarters', 1.0), ('eighths', 0.5)):
    pop = [r for r in rows if r['written'] == w and str(r['cls']).startswith('notehead')]
    n = len(pop)
    c = collections.Counter(r['value'] or ('noh:' + str(r['noh']) if r['noh'] else r['why']) for r in pop)
    slit_hollow = sum(1 for r in pop if (r['slit'] or 0) >= 0.18)
    ext = np.array([r['ext'] for r in pop if r['ext']])
    print(f'{plate} {name} n={n} slit>=0.18 on {slit_hollow} ({100.0*slit_hollow/max(1,n):.1f}%)', dict(c.most_common()))
    if len(ext):
        print('   width p1/p50/p99', np.percentile(ext[:, 0], [1, 50, 99]).round(2), 'height p1/p50/p99', np.percentile(ext[:, 1], [1, 50, 99]).round(2))
