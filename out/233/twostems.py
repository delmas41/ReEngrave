"""For heads whose duration verdict says stems_attached>=2: where are the stems relative to the head and to the neighbouring heads."""
import json, sys, collections
sys.path.insert(0, '/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a85d4443ac64d554a')
from tools.omr.staged.geometry import stem_touches_head
cl = json.load(open(sys.argv[1]))
subs = set(cl["C_no_stroke_reading(stems 2)"]) | set(cl.get("C_no_stroke_reading(stems 3)", []))
obs_path = sys.argv[2]
cells = {('cell/' + '/'.join(s.split('/')[1:5])) for s in subs}
stems = collections.defaultdict(list); heads = collections.defaultdict(list)
with open(obs_path) as f:
    for line in f:
        if '"stem"' not in line and '"glyph_box"' not in line:
            continue
        o = json.loads(line)
        if o['quantity'] == 'stem' and o['subject'] in cells:
            stems[o['subject']].append(o['value'])
        elif o['quantity'] == 'glyph_box' and o['subject'].startswith('glyph/'):
            c = 'cell/' + '/'.join(o['subject'].split('/')[1:5])
            if c in cells and o['value'][0].startswith('notehead'):
                heads[c].append((o['subject'], o['value'][1:5]))
out = collections.Counter()
for s in sorted(subs):
    c = 'cell/' + '/'.join(s.split('/')[1:5])
    hb = [h for h in heads[c] if h[0] == s][0][1]
    mine = [st for st in stems[c] if stem_touches_head(st, hb)]
    desc = []
    for st in mine:
        sx = st[0] + st[2] / 2.0
        side = 'L' if sx < hb[0] + hb[2] / 2.0 else 'R'
        top = st[1]; bot = st[1] + st[3]
        hy = hb[1] + hb[3] / 2.0
        ext = ('up' if top < hy - 0.5 * hb[3] else '') + ('dn' if bot > hy + 0.5 * hb[3] else '')
        # other heads touching this stem
        others = [h[0].split('/')[-1] for h in heads[c] if h[0] != s and stem_touches_head(st, h[1])]
        osides = []
        for h in heads[c]:
            if h[0] != s and stem_touches_head(st, h[1]):
                osides.append('nbrL' if sx > h[1][0] + h[1][2] / 2.0 else 'nbrR')
        desc.append('%s:%s:%s' % (side, ext or 'short', '+'.join(osides) or 'alone'))
    key = ' | '.join(sorted(desc))
    out[key] += 1
    print(s, key, 'w=%d' % hb[2], [st[2] for st in mine])
print()
for k, n in out.most_common():
    print(n, k)
