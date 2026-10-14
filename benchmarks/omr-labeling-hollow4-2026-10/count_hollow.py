"""Count notehead-class boxes on one page of a staged record (GATHER view and ADJUDICATE standing).

    python3 benchmarks/omr-labeling-hollow4-2026-10/count_hollow.py PAGE_INDEX record.json [record.json ...]
"""
import collections
import sys

sys.path.insert(0, '.')
from tools.omr.hand_truth import score as SC  # noqa: E402
from tools.omr.staged import readout as RO  # noqa: E402

HOL = ('noteheadHalf', 'noteheadWhole')

for p in sys.argv[2:]:
    run = RO.load_run(p)
    gl = SC.read_glyphs(run, int(sys.argv[1]))
    c = collections.Counter(g.cls for g in gl if g.cls.startswith('notehead'))
    st = collections.Counter((g.cls[8:], g.status) for g in gl if g.cls.startswith(HOL))
    print(p.split('/')[-1], 'hollow total', sum(v for k, v in c.items() if k.startswith(HOL)),
          'black', sum(v for k, v in c.items() if k.startswith('noteheadBlack')))
    print('  ', dict(c))
    print('  status', dict(st))
