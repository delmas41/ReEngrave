"""2.108 -- how far from its staff is a REAL note (Sean's hand truth) and how far
are the detector's pre-fill boxes?  Reads a page store (truth + queue), detects
the page's staves, prints distance-to-nearest-staff histograms in staff spaces.

    python3 benchmarks/omr-notehead-precision-2026-09/probe/2.108/reach.py PAGE.json PDF PAGEIDX
"""
import json
import sys
from collections import Counter

sys.path.insert(0, '.')
from tools.omr.hand_truth import session as S  # noqa: E402
from tools.omr.staged import geometry as G  # noqa: E402

page_json, pdf, pidx = sys.argv[1], sys.argv[2], int(sys.argv[3])
d = json.load(open(page_json))
img = S._render(__import__('pathlib').Path(pdf), pidx, d['dpi'])
pws, _ = S.measure_cells(img)
staves = [s for s in pws.staves if len(s.line_ys) >= 5]
print('staves', len(staves))
bands = G.staff_bands(staves)


def fam(c):
    if c.startswith('notehead'):
        return 'notehead'
    if c.startswith('rest'):
        return 'rest'
    if c.startswith('accidental'):
        return 'accidental'
    if c.startswith('flag'):
        return 'flag'
    return None


def dist(r):
    cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
    return G.distance_to_staff_spaces(cx, cy, bands)


def hist(vals):
    c = Counter()
    for v in vals:
        c[min(int(v // 2) * 2, 40)] += 1
    return dict(sorted(c.items()))


for label, items in (('TRUTH', [(b['cls'], b['rect']) for b in d['boxes']]),
                     ('QUEUE', [(q['cls'], q['rect']) for q in d['queue']])):
    for f in ('notehead', 'rest', 'accidental', 'flag'):
        v = sorted(dist(r) for c, r in items if fam(c) == f)
        if not v:
            continue
        print(label, f, 'n', len(v), 'max', round(v[-1], 2),
              'top5', [round(x, 1) for x in v[-5:]], 'hist(2sp)', hist(v))
