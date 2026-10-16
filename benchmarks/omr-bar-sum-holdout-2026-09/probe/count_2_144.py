"""ROADMAP 2.144 -- head boxes overlapping a detector CLEF box (same page+system+staff), from cache_2_144.py rows."""
import json, sys, collections
d = json.load(open(sys.argv[1])); B = d['boxes']; V = d['verdicts']
def cover(a, b):
    iw = min(a[2], b[2]) - max(a[0], b[0]); ih = min(a[3], b[3]) - max(a[1], b[1])
    if iw <= 0 or ih <= 0: return 0.0
    return iw * ih / min((a[2]-a[0])*(a[3]-a[1]), (b[2]-b[0])*(b[3]-b[1]))
staff = lambda s: '/'.join(s.split('/')[1:4])
clefs = collections.defaultdict(list); heads = []
for s, (c, sc, bb) in B.items():
    if not bb: continue
    if c.startswith('clef'): clefs[staff(s)].append((s, c, bb))
    elif c.startswith('notehead') and s.startswith('glyph/'): heads.append((s, c, sc, bb))
print('heads', len(heads), 'clef boxes', sum(len(v) for v in clefs.values()))
rows = []
for s, c, sc, bb in heads:
    for cs, cc, cb in clefs.get(staff(s), []):
        cv = cover(bb, cb)
        if cv >= 0.3:
            v = V.get(s, {}); nn = v.get('notehead_is_not_a_notehead'); du = v.get('duration')
            rows.append((s, c, round(sc, 2), cs, cc, round(cv, 2), nn and (nn[0], nn[1], nn[2]), du and (du[0], du[1])))
print('overlapping a clef box (cover >= 0.3):', len(rows))
st = collections.Counter(('refused:' + str(r[6][2])) if (r[6] and r[6][1] is True) else 'STANDS' for r in rows)
print(st)
for r in rows:
    if not (r[6] and r[6][1] is True): print(r)
