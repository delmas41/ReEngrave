"""whole-rest m2: 12 NEW blind tiles. Nothing of ours drawn; each crop is the BAR (the cell's width) of a rest the flags gained.
usage (from the worktree root): PYTHONPATH=. python3 out/lane-report/whole-rest-m2/make_tiles.py
Weighted toward plain rests (8) and, among them, bars that also hold another mark (>= 5); 4 blue (a head or rest box also stands in the bar).
key.json goes OUTSIDE the tiles folder."""
import json, collections, random, pathlib
from PIL import Image
from tools.omr.staged import lane_report as L
from tools.omr.preprocessing import render_page

W = pathlib.Path('out/lane-report/whole-rest-m2/work')
M1KEY = json.load(open('/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-ae06367b155a69fa2/out/lane-report/whole-rest-m1/key.json'))
used_m1 = {k['rg'] for k in M1KEY}
OUT = pathlib.Path('out/print/whole-rest-m2-tiles')
(OUT / 'tiles').mkdir(parents=True, exist_ok=True)
rng = random.Random(4102)
cands = []
for pl in ('litolff', 'brahms'):
    off = json.load(open(W / (pl + '.off.symbols.json')))['hosts']
    on = json.load(open(W / (pl + '.on.symbols.json')))['hosts']
    offrg = collections.Counter(h.get('rg') for h in off if h['kind'] == 'rest')
    mini = json.load(open(W / (pl + '.on.mini-record.json')))
    cells = collections.defaultdict(list)
    for o in mini['observations']:
        if o['quantity'] == 'glyph_box' and (o.get('detail') or {}).get('bbox_page_px'):
            p = o['subject'].split('/')
            cells[tuple(p[1:5])].append((o['subject'], o['value'][0], o['detail']['bbox_page_px']))
    for h in on:
        if h['kind'] != 'rest':
            continue
        if offrg[h.get('rg')] > 0:
            offrg[h['rg']] -= 1
            continue
        if h['rg'] in used_m1:
            continue
        p = h['rg'].split('/')
        cl = cells[tuple(p[1:5])]
        staffs = [b for s, c, b in cl if c == 'staff']
        if not staffs:
            continue
        x0 = min(b[0] for b in staffs); x1 = max(b[2] for b in staffs)
        y0 = min(b[1] for b in staffs); y1 = max(b[3] for b in staffs)
        others = sorted({c for s, c, b in cl if c not in ('staff',) and s != h['rg']})
        nonhr = [c for c in others if not (c.lower().startswith('notehead') or c.lower().startswith('rest'))]
        cands.append(dict(plate=pl, rg=h['rg'], page=int(p[1]), blue=h['blue'], measure=h['measure'], part=h['part'], bar=[x0, y0, x1, y1],
                          other_classes=others, other_marks=nonhr, other_head_or_rest=[c for c in others if c not in nonhr]))
print('new rests', len(cands), 'plain', sum(not c['blue'] for c in cands), 'blue', sum(c['blue'] for c in cands),
      'plain with another mark', sum((not c['blue']) and bool(c['other_marks']) for c in cands))
plain_mark = [c for c in cands if not c['blue'] and c['other_marks']]
plain_bare = [c for c in cands if not c['blue'] and not c['other_marks']]
blue = [c for c in cands if c['blue']]
for g in (plain_mark, plain_bare, blue):
    rng.shuffle(g)
def take(g, n, seen_bars, plate_cap):
    out = []
    for c in g:
        k = (c['plate'], c['page'], tuple(round(v / 50) for v in c['bar']))
        if k in seen_bars:
            continue
        if sum(1 for o in out if o['plate'] == c['plate']) >= plate_cap:
            continue
        seen_bars.add(k); out.append(c)
        if len(out) == n:
            break
    return out
seen = set()
pick = take(plain_mark, 5, seen, 3) + take(plain_bare, 3, seen, 2) + take(blue, 4, seen, 2)
if len(pick) < 12:
    pick += take(plain_mark, 12 - len(pick), seen, 4)
for c in pick:
    c['role'] = 'blue' if c['blue'] else ('plain+other mark' if c['other_marks'] else 'plain')
rng.shuffle(pick)
key = []
ims = {}
for n, c in enumerate(pick, 1):
    k = (c['plate'], c['page'])
    if k not in ims:
        ims.clear()
        ims[k] = Image.fromarray(render_page(str(L.LIB / L.PLATES[c['plate']]['pdf']), c['page'], dpi=600).rgb).convert('RGB')
    im = ims[k]
    u = L.PLATES[c['plate']]['unit']
    x0, y0, x1, y1 = c['bar']
    crop = im.crop((max(0, int(x0 - 0.5 * u)), max(0, int(y0 - 3 * u)), int(x1 + 0.5 * u), int(y1 + 3 * u)))
    wdt = 700
    crop = crop.resize((wdt, max(1, int(wdt * crop.height / crop.width))), Image.LANCZOS)
    crop.save(OUT / 'tiles' / ('tile_%02d.png' % n))
    key.append(dict(c, tile=n))
(OUT / 'tiles' / 'README.md').write_text(
    "# Whole-rest m2 tiles\n\nEach picture is one BAR cut from a scanned score page. Nothing of ours is drawn on it.\n\n"
    "**Question, for every tile:** what is in this bar (a whole-bar rest, other rests, notes, or something else)? Anything "
    "that looks odd about it?\n\nAnswer by tile number.\n")
(OUT / 'key.json').write_text(json.dumps(key, indent=1, default=str))
for k in key:
    print(k['tile'], k['plate'], k['role'], k['rg'], 'blue' if k['blue'] else 'plain', k['other_classes'][:6])
