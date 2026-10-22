"""2.167c probe 4: contact sheets of sampled held bars for MY OWN eyes (scratch, not evidence).
usage: c4_sheet.py lit|bra HELD.json COVERAGE.json SEED N OUTDIR [PER_SHEET=5]"""
import json
import os
import random
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
import c3_render as R   # noqa: E402

key, held_p, cov_p, seed, n, outdir = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
per = int(sys.argv[7]) if len(sys.argv) > 7 else 5
rows = json.load(open(held_p))
cov = json.load(open(cov_p))
H = {(b['page'], b['system'], b['staff'], b['cell']) for b in cov['bars_held_out_sum']['held']}
pool = sorted([r for r in rows if (r['page'], r['system'], r['staff'], r['cell']) in H and r['box']],
              key=lambda r: (r['page'], r['system'], r['staff'], r['cell']))
random.Random(seed).shuffle(pool)
pick = pool[:n]
os.makedirs(outdir, exist_ok=True)
json.dump([[r['page'], r['system'], r['staff'], r['cell']] for r in pick], open(os.path.join(outdir, 'sample.json'), 'w'))
fo = R.font(14)
for si in range(0, len(pick), per):
    chunk = pick[si:si + per]
    ims = []
    for j, r in enumerate(chunk):
        zoom = 1.4 if key == 'lit' else 0.9
        im = R.render_bar(key, r, zoom=zoom)
        lines = R.events_text(r)
        h = r['held']
        hd = "#%d  p%d s%d staff%d cell%d  %s  want %.4g q, got %s  voices_judged=%d" % (
            si + j, r['page'], r['system'], r['staff'], r['cell'], r['name'], h['want_quarters'], h['quarters'], len(h['voices']))
        tw = 330
        H_ = max(im.height, 16 * len(lines) + 24) + 22
        tile = Image.new("RGB", (im.width + tw, H_), "white")
        tile.paste(im, (0, 22))
        d = ImageDraw.Draw(tile)
        d.text((4, 3), hd, fill=R.BLACK, font=fo)
        for q, (t, c) in enumerate(lines):
            d.text((im.width + 8, 26 + 16 * q), t, fill=c, font=fo)
        ims.append(tile)
    W = max(t.width for t in ims)
    Hh = sum(t.height for t in ims) + 6 * len(ims)
    sheet = Image.new("RGB", (W, Hh), (235, 235, 235))
    y = 0
    for t in ims:
        sheet.paste(t, (0, y))
        y += t.height + 6
    sheet.save(os.path.join(outdir, 'sheet_%02d.png' % (si // per)))
print('sheets', (len(pick) + per - 1) // per)
