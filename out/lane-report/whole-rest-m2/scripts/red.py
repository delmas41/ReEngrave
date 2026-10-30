import json
W = 'out/lane-report/whole-rest-m2/work/'
for pl in ('litolff', 'brahms'):
    off = json.load(open(W + pl + '.off.red-bars.json'))
    on = json.load(open(W + pl + '.on.red-bars.json'))
    k = lambda b: (b['page'], b['system'], b['staff'], b['cell'])
    ko = {k(b): b for b in off}
    kn = {k(b): b for b in on}
    print(pl, len(off), len(on))
    for key in sorted(set(kn) - set(ko)):
        print('  NEW RED', key, kn[key])
    for key in sorted(set(ko) - set(kn)):
        print('  GONE RED', key, ko[key])
