"""Notes whose duration was decided using ONLY NOT-JOINED beam witnesses:
crop the head (green bracket) with the decided beam_levels / type, for the
0-level and >=3-level groups."""
import sys, collections, random; sys.path.insert(0, '.')
import fitz, numpy as np, cv2
from tools.omr.staged.record_io import load_record
rec, pdf, pi, tag = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
r = load_record(rec)['record']; obs = {o['id']: o for o in r['observations']}
gb = {o['subject']: o['detail']['bbox_page_px'] for o in r['observations'] if o['quantity'] == 'glyph_box' and (o.get('detail') or {}).get('bbox_page_px')}
pg = fitz.open(pdf)[pi]; pix = pg.get_pixmap(dpi=600, colorspace=fitz.csGRAY)
page = cv2.cvtColor(np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w), cv2.COLOR_GRAY2BGR)
groups = collections.defaultdict(list)
for v in r['verdicts']:
    if v['quantity'] != 'duration' or v['outcome'] != 'decided': continue
    js = [obs[u] for u in (v.get('used') or []) if u in obs and obs[u]['quantity'] == 'beam_stem_join']
    if not js or any(j['value'] for j in js): continue
    lv = (v.get('value') or {}).get('beam_levels')
    groups[str(lv)].append(v)
random.seed(3); tiles = []
for g in ('1', '2'):
    for v in random.sample(groups[g], min(12 if g == '1' else 6, len(groups[g]))):
        b = gb.get(v['subject'])
        if not b: continue
        X0, Y0 = max(0, int(b[0] - 160)), max(0, int(b[1] - 220)); X1, Y1 = int(b[2] + 160), int(b[3] + 220)
        t = page[Y0:Y1, X0:X1].copy()
        x0, y0, x1, y1 = int(b[0] - X0), int(b[1] - Y0), int(b[2] - X0), int(b[3] - Y0)
        for (x, y, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
            cv2.line(t, (x - 4 * dx, y - 4 * dy), (x + 12 * dx, y - 4 * dy), (0, 160, 0), 3); cv2.line(t, (x - 4 * dx, y - 4 * dy), (x - 4 * dx, y + 12 * dy), (0, 160, 0), 3)
        val = v.get('value') or {}
        cv2.putText(t, f"beams={val.get('beam_levels')} {val.get('type', '')}", (3, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 0, 0), 1)
        tiles.append(cv2.copyMakeBorder(t, 3, 3, 3, 3, cv2.BORDER_CONSTANT, value=(200, 200, 200)))
H = max(t.shape[0] for t in tiles); W = max(t.shape[1] for t in tiles)
tiles = [cv2.copyMakeBorder(t, 0, H - t.shape[0], 0, W - t.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in tiles]
while len(tiles) % 6: tiles.append(np.full_like(tiles[0], 255))
cv2.imwrite(f"out/print/beam-stem-ink-2.38/{tag}_levels_check_12.png", np.vstack([np.hstack(tiles[i:i + 6]) for i in range(0, len(tiles), 6)]))
print(tag, {k: len(v) for k, v in groups.items()}, len(tiles))
