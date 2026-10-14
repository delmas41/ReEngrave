"""2.108 -- dry-run the pre-fill prune on a page store (READ ONLY) and check it
against Sean's truth boxes: how many queued boxes go, by region cell kind and
class, and how many of his own boxes would have been caught (must be 0).

    python3 .../prune_probe.py PAGE.json
"""
import json
import sys
from collections import Counter

sys.path.insert(0, '.')
from tools.omr.hand_truth import session as S, store  # noqa: E402
from tools.omr.staged import geometry as G  # noqa: E402

page = store.load(__import__('pathlib').Path(sys.argv[1]))
bands = S.page_staff_bands(page)
print('staves', len(bands), 'queue', len(page.queue), 'truth boxes', len(page.boxes))


def kind_of(rect):
    cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
    for c in page.cells:
        if c.kind != 'measure' and c.rect[0] <= cx <= c.rect[2] and c.rect[1] <= cy <= c.rect[3]:
            return c.kind
    return 'measure'


gone = Counter()
kept = Counter()
for q in page.queue:
    far = S.off_staff_spaces(bands, q.cls, q.rect) is not None
    fam = q.cls[:8] if q.cls.startswith(('notehead', 'accident')) else q.cls
    (gone if far and q.source.startswith('detector:') else kept)[(kind_of(q.rect), fam)] += 1
print('REFUSED from the queue, by (region kind, class):')
for k, v in sorted(gone.items(), key=lambda t: -t[1]):
    print('   ', k, v)
print('refused total', sum(gone.values()), ' remaining pitch-bearing detector boxes in queue by kind:')
rem = Counter()
for q in page.queue:
    if q.source.startswith('detector:') and G.is_pitch_bearing(q.cls) \
            and S.off_staff_spaces(bands, q.cls, q.rect) is None:
        rem[kind_of(q.rect)] += 1
print('   ', dict(rem))
truth_caught = [(b.id, b.cls, round(S.off_staff_spaces(bands, b.cls, b.rect), 1))
                for b in page.boxes if S.off_staff_spaces(bands, b.cls, b.rect) is not None]
print('TRUTH boxes the rule would refuse:', len(truth_caught), truth_caught[:10])
t = Counter(b.cls[:8] for b in page.boxes if G.is_pitch_bearing(b.cls))
print('truth pitch-bearing boxes:', dict(t))
seans = [q for q in page.queue if q.source.startswith('sean-')]
print("Sean's old-label proposals in queue:", len(seans), 'of which off-staff (kept anyway):',
      sum(1 for q in seans if S.off_staff_spaces(bands, q.cls, q.rect) is not None))

print('sensitivity to the reach (queued detector boxes refused / truth boxes caught):')
for R in (5.5, 6.0, 7.0, 8.0, 10.0):
    G.OFF_STAFF_REACH_SPACES = R
    n = sum(1 for q in page.queue if q.source.startswith('detector:')
            and S.off_staff_spaces(bands, q.cls, q.rect) is not None)
    t = sum(1 for b in page.boxes if S.off_staff_spaces(bands, b.cls, b.rect) is not None)
    print('   reach %4.1f: refused %d, truth caught %d' % (R, n, t))
