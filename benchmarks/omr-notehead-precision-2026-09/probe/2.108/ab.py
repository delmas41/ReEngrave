"""2.108 -- base vs arm on two small staged records: every verdict that differs
(all deciders), `off_staff_glyph` count, and the farthest-from-staff boxes either
record kept.   python3 .../ab.py BASE.json ARM.json"""
import sys
from collections import Counter

sys.path.insert(0, '.')
from tools.omr.staged.record_io import load_record  # noqa: E402


def verdicts(path):
    doc = load_record(path)
    rec = doc['record'] if 'record' in doc else doc
    return {(v['subject'], v['quantity'], v['decider']): (v.get('outcome'), str(v.get('value')), v.get('reason'))
            for v in rec['verdicts']}, rec


base, brec = verdicts(sys.argv[1])
arm, arec = verdicts(sys.argv[2])
print('verdicts base', len(base), 'arm', len(arm))
diff = [(k, base.get(k), arm.get(k)) for k in set(base) | set(arm) if base.get(k) != arm.get(k)]
print('differing verdicts:', len(diff))
for k, b, a in sorted(diff)[:20]:
    print('  ', k[0], k[2], b, '->', a)
off = [k for k, v in arm.items() if v[2] == 'off_staff_glyph']
print('off_staff_glyph in arm:', len(off), off[:10])
print('off_staff_glyph in base:', sum(1 for v in base.values() if v[2] == 'off_staff_glyph'))
print('reasons changed:', Counter((b[2] if b else None, a[2] if a else None) for _, b, a in diff).most_common(10))
