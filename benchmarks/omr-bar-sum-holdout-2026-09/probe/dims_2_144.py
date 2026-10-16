"""ROADMAP 2.144 -- clef box dimensions (staff spaces) and head-inside-clef fraction for every head on a clef box."""
import json, sys, collections
d = json.load(open(sys.argv[1])); B = d['boxes']; V = d['verdicts']; SL = d['stafflines']
def inside(h, c):
    iw = min(h[2], c[2]) - max(h[0], c[0]); ih = min(h[3], c[3]) - max(h[1], c[1])
    return 0.0 if iw <= 0 or ih <= 0 else iw * ih / ((h[2]-h[0]) * (h[3]-h[1]))
skey = lambda s: 'staff/' + '/'.join(s.split('/')[1:4])
clefs = collections.defaultdict(list)
for s, (c, sc, bb) in B.items():
    if bb and c.startswith('clef'): clefs[skey(s)].append((s, c, sc, bb))
for s, (c, sc, bb) in B.items():
    if not (bb and c.startswith('notehead') and s.startswith('glyph/')): continue
    for cs, cc, csc, cb in clefs.get(skey(s), []):
        f = inside(bb, cb)
        if f >= 0.3:
            ls = SL.get(skey(s)); sp = (ls[-1] - ls[0]) / 4.0 if ls else None
            nn = V.get(s, {}).get('notehead_is_not_a_notehead')
            print(s.replace('glyph/', ''), c[9:], round(sc, 2), '|', cc, round(csc, 2), 'in=%.2f' % f,
                  'h=%.2fsp w=%.2fsp' % ((cb[3]-cb[1])/sp, (cb[2]-cb[0])/sp), 'head=%.2fx%.2f' % ((bb[2]-bb[0])/sp, (bb[3]-bb[1])/sp),
                  'REFUSED:' + nn[2] if nn and nn[1] is True else 'stands')
