"""2.108 -- from a small staged record: every notehead verdict's `filed_spaces`
(vertical distance of the head's centre from the band of the staff it was filed
on, GATHER/ADJUDICATE's own arithmetic) with the verdict it got.

    python3 .../filed.py REC.json [REC2.json ...]
"""
import json
import sys
from collections import Counter

sys.path.insert(0, '.')
from tools.omr.staged.record_io import load_record  # noqa: E402

for path in sys.argv[1:]:
    doc = load_record(path)
    rec = doc['record'] if 'record' in doc else doc
    rows = []
    for v in rec['verdicts']:
        if v.get('decider') != 'adjudicate_notehead_is_not_a_notehead':
            continue
        sig = (v.get('detail') or {}).get('nearer_staff_signal') or {}
        f = sig.get('filed_spaces')
        rows.append((f, v.get('reason'), v.get('subject'), v.get('value')))
    have = [r for r in rows if r[0] is not None]
    print(path.split('/')[-1], 'noteheads', len(rows), 'with filed_spaces', len(have))
    c = Counter()
    for f, reason, _, _ in have:
        c[(min(int(f), 12), 'kept' if reason == 'notehead' else 'refused')] += 1
    for k in sorted(c):
        print('  filed>=%2d %-7s %d' % (k[0], k[1], c[k]))
    have.sort(key=lambda r: -r[0])
    for r in have[:12]:
        print('  ', round(r[0], 2), r[1], r[2])
