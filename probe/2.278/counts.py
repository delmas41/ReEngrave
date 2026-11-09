import sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
from tools.omr.staged.record_io import load_record
d = load_record(sys.argv[1])
print(list(d.keys())[:20])
for k, v in d.items():
    if isinstance(v, list) and v and isinstance(v[0], dict) and 'quantity' in v[0]:
        c = collections.Counter(x['quantity'] for x in v)
        print(k, len(v), {q: c[q] for q in c if any(s in q for s in ('beam', 'stem', 'flag', 'tip'))})
