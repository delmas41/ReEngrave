"""2.108 -- census of every pitch-bearing glyph box in a staged record: distance
(staff spaces) from its centre to the NEAREST staff band of its page, whatever
cell it was filed in; plus its verdict.  Which boxes stand far from every staff
in the STAGED gather today?

    python3 .../census.py REC.json [REC2.json ...]
"""
import sys
from collections import Counter, defaultdict

sys.path.insert(0, '.')
from tools.omr.staged.record_io import load_record  # noqa: E402

FAMS = ('notehead', 'rest', 'accidental', 'flag', 'augmentationDot')


def fam(c):
    for f in FAMS:
        if c.startswith(f):
            return f
    return None


for path in sys.argv[1:]:
    doc = load_record(path)
    rec = doc['record'] if 'record' in doc else doc
    staves = defaultdict(list)       # page -> [(top, bottom, spacing)]
    spacing = {}
    lines = {}
    for o in rec['observations']:
        q = o['quantity']
        if q == 'staff_lines':
            lines[o['subject']] = o['value']
        elif q == 'staff_spacing':
            spacing[o['subject']] = o['value']
    for s, ys in lines.items():
        p = int(s.split('/')[1])
        sp = spacing.get(s)
        if sp and len(ys) >= 2:
            staves[p].append((min(ys), max(ys), float(sp)))
    verdict = {}
    for v in rec['verdicts']:
        if v.get('decider') == 'adjudicate_notehead_is_not_a_notehead':
            verdict[v['subject']] = v.get('reason')
    far = []
    hist = Counter()
    n = 0
    for o in rec['observations']:
        if o['quantity'] != 'glyph_box':
            continue
        c = str(o['value'][0])
        f = fam(c)
        if not f:
            continue
        bb = (o.get('detail') or {}).get('bbox_page_px')
        if not bb:
            continue
        p = int(o['subject'].split('/')[1])
        cy = (bb[1] + bb[3]) / 2.0
        best = None
        for top, bot, sp in staves[p]:
            d = max(top - cy, 0.0, cy - bot) / sp
            best = d if best is None else min(best, d)
        if best is None:
            continue
        n += 1
        hist[(f, min(int(best), 8))] += 1
        far.append((best, f, c, o['subject'], verdict.get(o['subject'])))
    far.sort(reverse=True)
    print(path.split('/')[-1], 'pitch-bearing boxes', n)
    for k in sorted(hist):
        print('  %-16s nearest-staff >= %d sp : %d' % (k[0], k[1], hist[k]))
    for r in far[:15]:
        print('  ', round(r[0], 2), r[1], r[2], r[3], r[4])
