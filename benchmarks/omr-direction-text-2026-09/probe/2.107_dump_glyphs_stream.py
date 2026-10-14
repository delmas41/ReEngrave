# ROADMAP 2.107 probe. The same for a record too big to load (streams `observations`).
# python3 2.107_dump_glyphs_stream.py RECORD.json TAG PDF
import os
"""dump.py for a record too big to load whole: stream the observations array."""
import sys, json, pathlib, re, collections
sys.path.insert(0, '.')
from tools.omr.staged.judged import iter_array
S = os.environ.get('LETTER_LOOK_SCRATCH', '.')
path, tag, pdf = sys.argv[1], sys.argv[2], sys.argv[3]
rows, lines = [], {}
GK = re.compile(r'^glyph/(\d+)/(\d+)/(\d+)/(\d+)/(\d+)$')
n = 0
for o in iter_array(pathlib.Path(path), 'observations'):
    n += 1
    q = o['quantity']
    if q == 'glyph_box':
        m = GK.match(o['subject'])
        if not m:
            continue
        p, s, st, c, g = (int(v) for v in m.groups())
        v = o.get('value')
        bp = (o.get('detail') or {}).get('bbox_page_px')
        rows.append(dict(key=o['subject'], page=p, system=s, staff=st, cell=c, idx=g,
                         cls=v[0] if v else None, score=o.get('score'), box=bp, status=None, notes=[]))
    elif q == 'staff_lines' and o['subject'].startswith('staff/'):
        p, s, st = (int(v) for v in o['subject'].split('/')[1:4])
        lines[(p, s, st)] = [float(y) for y in o['value']]
geo = collections.defaultdict(dict)
for (p, s, st), ys in lines.items():
    geo[str(p)].setdefault(str(s), {'staves': []})['staves'].append([st, f'staff/{p}/{s}/{st}', ys, None])
json.dump(dict(rows=rows, geo=geo, dpi=600, pdf=pdf), open(f'{S}/{tag}.glyphs.json', 'w'), default=str)
print(n, 'observations', len(rows), 'glyphs', sorted(int(p) for p in geo))
