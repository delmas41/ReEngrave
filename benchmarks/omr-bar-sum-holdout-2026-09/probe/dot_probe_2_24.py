"""ROADMAP 2.24 scratch probe: dump every Q.AUG_DOT / Q.DOT_ROLE / Q.NOTEHEAD_CLASS
/ Q.REST row filed in a given list of cells, for the fresh Breitkopf p1 record.
"""
import sys
sys.path.insert(0, '.')
from tools.omr.staged.record_io import load_record
from tools.omr.staged.record import Q

doc = load_record('benchmarks/omr-bar-sum-holdout-2026-09/out/r224/brahms-p1.record.json')
rec = doc['record'] if 'record' in doc else doc


def cell_of(sub):
    p = sub.split('/')
    if len(p) >= 6 and p[0] == 'glyph':
        return tuple(int(x) for x in p[1:5])
    return None


CELLS = [(1, 0, 2, 5), (1, 1, 12, 4), (1, 1, 11, 6), (1, 0, 3, 4), (1, 0, 3, 3)]

obs_by_cell = {}
for o in rec['observations']:
    q = o['quantity']
    if q not in (Q.AUG_DOT, Q.GLYPH_BOX, Q.NOTEHEAD_CLASS, Q.REST, Q.CELL_STAFF_SPACE):
        continue
    c = cell_of(o['subject'])
    if c not in CELLS:
        continue
    obs_by_cell.setdefault(c, {}).setdefault(q, []).append(o)

from tools.omr.staged.review import rerun as RR
vidx = RR._verdict_index(rec['verdicts'])

for c in CELLS:
    print('=== cell', c)
    d = obs_by_cell.get(c, {})
    boxes = {o['subject']: o['value'] for o in d.get(Q.GLYPH_BOX, [])}
    for o in d.get(Q.AUG_DOT, []):
        sub = o['subject']
        v = vidx.get((Q.DOT_ROLE, sub))
        print('  AUG_DOT', sub, 'value', o['value'], 'detail', o.get('detail'),
              'box', boxes.get(sub), '-> DOT_ROLE', v)
    for o in d.get(Q.NOTEHEAD_CLASS, []):
        print('  NOTEHEAD_CLASS', o['subject'], o['value'], 'box', boxes.get(o['subject']))
    for o in d.get(Q.REST, []):
        print('  REST', o['subject'], o['value'], 'box', boxes.get(o['subject']))
    for o in d.get(Q.CELL_STAFF_SPACE, []):
        print('  CELL_STAFF_SPACE', o['subject'], o['value'])
