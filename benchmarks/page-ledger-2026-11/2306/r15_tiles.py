"""2.306 r15: Sean's blind tiles -- one staff each, a thin red box on ONE stem's ink (the page stroke run the reader joins, or the printed stem it
refuses, given as a box), nothing else drawn; the key (what we said, why picked) goes OUTSIDE the tile folder.
Usage: r15_tiles.py SPEC.json OUTDIR KEY.json   SPEC: [{"dump": pkl, "head": hid, "box": [x0,y0,x1,y1], "kind": "gained"|"refused", ...}, ...]"""
import sys, os, json, pickle
import numpy as np
from PIL import Image, ImageDraw

spec, outd, keyp = json.load(open(sys.argv[1])), sys.argv[2], sys.argv[3]
os.makedirs(os.path.join(outd, 'tiles'), exist_ok=True)
cache, tiles, key = {}, [], []
for n, s in enumerate(spec, 1):
    if s['dump'] not in cache:
        cache[s['dump']] = pickle.load(open(s['dump'], 'rb'))
    D = cache[s['dump']]
    h = next(t for t in D['heads'] if t['id'] == s['head'])
    sp = float(h['sp'])
    b = np.asarray(D['binary'])
    ink = b > 0 if b.max() <= 1 else b < 128
    if ink.mean() > 0.5:
        ink = ~ink
    x0, y0, x1, y1 = s['box']
    cx, cy = (h['box'][0] + h['box'][2]) / 2.0, (h['box'][1] + h['box'][3]) / 2.0
    top, bot = min(y0, cy) - 3.5 * sp, max(y1, cy) + 3.5 * sp
    X0, X1 = int(max(0, cx - 6 * sp)), int(min(ink.shape[1], cx + 6 * sp))
    Y0, Y1 = int(max(0, top)), int(min(ink.shape[0], bot))
    k = 3
    im = Image.fromarray((~ink[Y0:Y1, X0:X1]).astype(np.uint8) * 255).convert('RGB').resize(((X1 - X0) * k, (Y1 - Y0) * k), Image.NEAREST)
    d = ImageDraw.Draw(im)
    d.rectangle([(x0 - X0) * k - 3, (y0 - Y0) * k - 3, (x1 - X0) * k + 3, (y1 - Y0) * k + 3], outline=(230, 0, 0), width=2)
    p = os.path.join(outd, 'tiles', 'tile%02d.png' % n)
    im.save(p)
    tiles.append(im)
    key.append(dict(tile=n, page=D['page'], head=s['head'], members=h['members'], stem_box=s['box'], **{k2: v for k2, v in s.items() if k2 not in ('dump', 'box', 'head')}))
cols = 4
W = max(t.width for t in tiles); H = max(t.height for t in tiles)
sheet = Image.new('RGB', (cols * (W + 12), ((len(tiles) + cols - 1) // cols) * (H + 40)), 'white')
d = ImageDraw.Draw(sheet)
for i, t in enumerate(tiles):
    x, y = (i % cols) * (W + 12), (i // cols) * (H + 40)
    d.text((x + 4, y + 4), 'tile %d' % (i + 1), fill=(0, 0, 0))
    sheet.paste(t, (x, y + 24))
sheet.save(os.path.join(outd, 'sheet.png'))
json.dump(key, open(keyp, 'w'), indent=1)
print(os.path.join(outd, 'sheet.png'), len(tiles))
