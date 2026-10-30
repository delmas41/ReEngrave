"""2.235 blind tiles. usage: make_tiles.py WORKDIR OUTDIR KEYPATH
12 tiles: gained notes (Brahms 6, Litolff 1), blue->plain notes (Brahms 2, Litolff 1), 2 unchanged controls.
One staff each: a window 15 staff spaces either side of the head and 7 spaces above/below its box, ONE thin orange box sized to the
head (the WRITTEN file's box), nothing else drawn. The key (what we wrote) is OUTSIDE the tile folder."""
import json, os, random, sys
sys.path.insert(0, '/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a26d61ddc53de8906')
from PIL import Image, ImageDraw
from tools.omr.preprocessing import render_page
from tools.omr.staged.lane_report import LIB, PLATES

wd, outdir, keypath = sys.argv[1:4]
rng = random.Random(2235)
os.makedirs(outdir, exist_ok=True)
diff = {p: json.load(open('%s/%s.diff.json' % (wd, p))) for p in ('brahms', 'litolff')}
on = {p: json.load(open('%s/%s.on.symbols.json' % (wd, p)))['hosts'] for p in ('brahms', 'litolff')}


def pick(plate, kind, n, only_blue=None):
    xs = diff[plate].get(kind, [])
    if only_blue is not None:
        xs = [x for x in xs if x['blue'] == only_blue]
    xs = [x for x in xs if x['kind'] == 'note']
    pages = {}
    for x in xs:
        pages.setdefault(x['page'], []).append(x)
    # spread over pages: round robin
    out = []
    keys = sorted(pages)
    rng.shuffle(keys)
    i = 0
    while len(out) < n and any(pages.values()):
        k = keys[i % len(keys)]
        if pages[k]:
            out.append(pages[k].pop(rng.randrange(len(pages[k]))))
        i += 1
    return [(plate, kind, x) for x in out]


chosen = []
chosen += pick('brahms', 'gained_note', 4, only_blue=False)
chosen += pick('brahms', 'gained_note', 2, only_blue=True)
chosen += pick('litolff', 'gained_note', 1)
chosen += pick('brahms', 'blue_to_plain', 2)
chosen += pick('litolff', 'blue_to_plain', 1)
# controls: notes written the same in both arms, plain, away from every changed head
changed = {x['rg'] for p in diff for v in diff[p].values() for x in v}
for plate in ('brahms', 'litolff'):
    pool = [h for h in on[plate] if h['kind'] == 'note' and h['rg'] not in changed and not h['blue']]
    chosen.append((plate, 'control', rng.choice(pool)))
rng.shuffle(chosen)
imgs = {}
key = []
for n, (plate, kind, h) in enumerate(chosen, 1):
    k = (plate, h['page'])
    if k not in imgs:
        imgs[k] = Image.fromarray(render_page(str(LIB / PLATES[plate]['pdf']), h['page'], dpi=600).rgb).convert('RGB')
    im = imgs[k]
    unit = PLATES[plate]['unit']
    b = h['box']
    x0, x1 = int(b[0] - 15 * unit), int(b[2] + 15 * unit)
    y0, y1 = int(b[1] - 7 * unit), int(b[3] + 7 * unit)
    crop = im.crop((x0, y0, x1, y1))
    d = ImageDraw.Draw(crop)
    d.rectangle([b[0] - x0, b[1] - y0, b[2] - x0, b[3] - y0], outline=(255, 140, 0), width=2)
    if plate == 'litolff':
        crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
    crop.save(os.path.join(outdir, 'tile_%02d.png' % n))
    key.append(dict(tile=n, plate=plate, role=kind, rg=h['rg'], page=h['page'], part=h['part'], measure=h['measure'], box=b,
                    written=h['type'], pitch=h.get('pitch'), blue_now=h['blue'], was=h.get('was'), was_blue=h.get('was_blue')))
json.dump(key, open(keypath, 'w'), indent=1)
open(os.path.join(outdir, 'README.md'), 'w').write(
    "# 2.235 tiles\n\nEach picture is one staff of a scanned score page with ONE orange box on it and nothing else drawn.\n\n"
    "**Question, for every tile:** what is the note in the orange box (its value, and a dot if it has one)? Reply by tile number.\n")
print(len(key), [k['role'] for k in key])
