"""2.220 m1 READER measure: head_ink.read_head_ink on the 600-dpi page raster, detector boxes + written value from 2.202f ON."""
import json, sys, collections, pathlib
WT = '/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a44a05b0ad517dce3'
sys.path.insert(0, WT)
import numpy as np
from tools.omr.preprocessing import render_page
from tools.omr.staged import head_ink as HI
from tools.omr.staged.gather import head_interior_white, notehead_ink_under
S = pathlib.Path('/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-agent-manager-workflow-356c39/7e1ea73e-2fd3-4d6c-a450-36868f7e14c0/scratchpad')
LIB = pathlib.Path('/Users/seanjohnson/Desktop/ReEngrave/library')
PDF = {'litolff': 'editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf',
       'brahms': 'editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf'}
plate, pages = sys.argv[1], [int(p) for p in sys.argv[2].split(',')]
d = json.load(open(S / ('lit.json' if plate == 'litolff' else 'bra.json')))
key = json.load(open(WT + '/out/print/2.220-plan/key.json'))
tiles = {k['subject']: k['tile'] for k in key if k['plate'] == plate}


def page_space(b):
    ink = (b == 0).mean(axis=1)
    rows = np.nonzero(ink >= 0.4)[0]
    bands, cur = [], [rows[0]]
    for r in rows[1:]:
        if r - cur[-1] <= 1:
            cur.append(r)
        else:
            bands.append(np.mean(cur)); cur = [r]
    bands.append(np.mean(cur))
    diffs = np.diff(bands)
    diffs = diffs[(diffs > 8) & (diffs < 40)]
    return float(np.median(diffs))


def wrote(v):
    dur = (v or {}).get('duration') or {}
    if dur.get('o') != 'decided' or not isinstance(dur.get('v'), dict):
        return None
    return dur['v'].get('written')


rows = []
for p in pages:
    pg = render_page(str(LIB / PDF[plate]), p, dpi=600).binary
    sp = page_space(pg)
    cells = collections.defaultdict(list)
    for s, b in d['boxes'].items():
        if int(s.split('/')[1]) == p:
            cells['/'.join(s.split('/')[:5])].append((s, b))
    for ck, items in cells.items():
        foreign = [b['page'] for s, b in items if HI.is_foreign_class(b['cls']) and b['page']]
        for s, b in items:
            if not str(b['cls']).lower().startswith('notehead') or not b['page']:
                continue
            r = HI.read_head_ink(pg, b['page'], sp, foreign, head_interior_white, notehead_ink_under)
            if r is None:
                continue
            rows.append({'s': s, 'p': p, 'cls': b['cls'], 'sp': sp, 'written': wrote(d['ver'].get(s)), 'tile': tiles.get(s),
                         'value': r['value'], 'why': r['why'], 'noh': r['not_one_head'], 'slit': r['slit'],
                         'ext': r['extent_sp'], 'box_sp': [round((b['page'][2] - b['page'][0]) / sp, 2), round((b['page'][3] - b['page'][1]) / sp, 2)],
                         'trimmed': r['trimmed'], 'fs': r['foreign_share'], 'oval': r['oval_width_sp'], 'clip': r['stack_clipped']})
    print(plate, p, 'sp', round(sp, 2), flush=True)
json.dump(rows, open(S / f'm_{plate}.json', 'w'))
for r in rows:
    if r['tile']:
        print('TILE', r['tile'], r['s'], r['value'], r['why'], r['noh'], r['slit'], r['ext'], r['box_sp'], r['fs'])
