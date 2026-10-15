import sys, json
from pathlib import Path
sys.path.insert(0, '.')
from tools.omr.staged import judged

def standing(path):
    by = {}
    for v in judged.iter_verdicts(Path(path)):
        if v.get('quantity') in ('duration', 'head_stem'):
            by.setdefault((v['subject'], v['quantity']), []).append(v)
    out = {}
    for k, vs in by.items():
        sup = {x.get('supersedes') for x in vs if x.get('supersedes')}
        live = [x for x in vs if x['id'] not in sup] or vs
        out[k] = live[-1]
    return out

def sig(v):
    if v is None:
        return None
    val = v.get('value')
    w = val.get('written') if isinstance(val, dict) else val
    def cw(c):
        if isinstance(c, dict):
            x = c.get('value')
            return str(x.get('written') if isinstance(x, dict) else x)
        return str(c)
    return (v['outcome'], v.get('reason'), w if not isinstance(w, str) else w, tuple(sorted(cw(c) for c in (v.get('candidates') or []))))

b, a = standing(sys.argv[1]), standing(sys.argv[2])
changed = []
for k in sorted(set(a) | set(b)):
    if sig(b.get(k)) != sig(a.get(k)):
        changed.append((k, sig(b.get(k)), sig(a.get(k))))
n = {q: sum(1 for k in set(a) | set(b) if k[1] == q) for q in ('duration', 'head_stem')}
print('subjects', n, 'changed', len(changed))
by = {}
for k, s0, s1 in changed:
    t = (k[1], s0[0] if s0 else None, s1[0] if s1 else None)
    by[t] = by.get(t, 0) + 1
for t, c in sorted(by.items(), key=lambda x: -x[1]):
    print(' ', t, c)
if len(sys.argv) > 3:
    for k, s0, s1 in changed:
        if k[1] == 'duration':
            print(k[0], s0, '->', s1)
