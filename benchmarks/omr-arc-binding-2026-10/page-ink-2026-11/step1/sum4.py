"""python3 /tmp/r4/sum.py DIR [BASEDIR]: pooled numbers; with BASEDIR: per-curve lost/gained whole and NEW run delta."""
import json, glob, collections, sys, pathlib
d = pathlib.Path(sys.argv[1])
b = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else None
tk = tw = nn = nr = tu = 0
rej = collections.Counter()
lost = gained = 0
for f in sorted(d.glob('*.step1.json')):
    J = json.load(open(f))
    s = J['summary']
    tk += s['curves_kept']; tw += s['whole']; nn += s['runs_new']; nr += s['runs']; tu += s.get('whole_union', 0)
    for k, v in s['rejected'].items():
        rej[k] += v
    if b:
        B = json.load(open(b / f.name))
        for x, y in zip([c for c in B['curves'] if not c['refused']], [c for c in J['curves'] if not c['refused']]):
            if x['best'] >= .8 and y['best'] < .8:
                lost += 1
                print('LOST', f.name, [round(v) for v in x['box']], y.get('why_no_run'))
            if x['best'] < .8 and y['best'] >= .8:
                gained += 1
print('kept %d whole %d (%.1f%%) union %d (%.1f%%) runs %d NEW %d' % (tk, tw, 100. * tw / tk, tu, 100. * tu / tk, nr, nn), 'lost', lost, 'gained', gained)
print({k: v for k, v in rej.items() if k in ('bad_fit', 'beam_raw', 'beam_like', 'straight', 'arc', 'short_flat', 'rough', 'sparse')})
