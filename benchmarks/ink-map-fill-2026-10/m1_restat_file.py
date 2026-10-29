"""2.220 m1 CORRECTION (barline lane, lane-2.221-barlines e2d57788b): "written" = the box is a NOTE in the exported ON file (2.202f
work/<plate>.on.symbols.json hosts, matched by glyph key), not "has a duration verdict" (refused boxes keep one).
Reads the m1 reader rows (scratch m_<plate>.json from m1_measure.py) and the m1 tile keys."""
import json, sys, collections
S = sys.argv[1]           # scratch dir holding m_litolff.json / m_brahms.json
W = '/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/2-202-beams-cause-1f79a5/out/lane-report/2.202f/work'
K = '/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a44a05b0ad517dce3/out/print'
PAGES = {'litolff': (4, 6), 'brahms': (5, 14)}
infile = {}
for plate, pages in PAGES.items():
    hosts = json.load(open(f'{W}/{plate}.on.symbols.json'))['hosts']
    notes = {h['rg']: h for h in hosts if h['kind'] == 'note' and h.get('page') in pages}
    infile[plate] = notes
    rows = [r for r in json.load(open(f'{S}/m_{plate}.json')) if r['p'] in pages]
    for name, w in (('halves', 2.0), ('quarters', 1.0), ('eighths', 0.5)):
        old = [r for r in rows if r['written'] == w and str(r['cls']).startswith('notehead')]
        new = [r for r in old if r['s'] in notes]
        hol = sum(1 for r in new if (r['slit'] or 0) >= 0.18)
        noh = sum(1 for r in new if r['noh'])
        print(f"{plate} {name}: verdict-written {len(old)} -> in the file {len(new)}; slit>=0.18 {hol}; not_one_head {noh} "
              f"{dict(collections.Counter(r['noh'] for r in new if r['noh']))}; file types {dict(collections.Counter(notes[r['s']]['type'] for r in new))}")
for n in ('2.220-m1-misses', '2.220-m1-notonehead'):
    key = json.load(open(f'{K}/{n}/key.json'))
    live = [(k['tile'], infile[k['plate']][k['rg']]['type']) for k in key if k['rg'] in infile[k['plate']]]
    print(n, 'tiles in the exported file:', live, 'of', len(key))
