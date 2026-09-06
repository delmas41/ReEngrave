import json, os, sys
sys.path.insert(0, os.getcwd())
from tools.omr.accuracy_record import BENCHMARK_WORKS
from tools.omr.instruments import lookup
out = {}
for w in BENCHMARK_WORKS:
    p = f'data/dossiers/{w}.json'
    if not os.path.exists(p):
        out[w] = {'__missing__': True}; continue
    d = json.load(open(p))
    parts = d.get('parts') or []
    rec = {}
    for part in parts:
        n = part.get('name') if isinstance(part, dict) else part
        if not n: continue
        m = lookup(n)
        inst = getattr(m, 'instrument', None)
        rec[n] = {
            'inst': getattr(inst, 'name', None),
            'range': list(getattr(inst, 'written_range', []) or []),
            'conf': getattr(m, 'confidence', None),
        }
    out[w] = rec
json.dump(out, open(sys.argv[1], 'w'), indent=1, sort_keys=True)
print('works:', len(out), 'names:', sum(len(v) for v in out.values()))
