"""Ledger-ink windows where the DETECTOR boxed every expected rung for that
candidate but the ink reader found none. Red = the ink window tested; green
bracket = the head; blue = the detector's ledgerLine boxes."""
import sys, collections; sys.path.insert(0, '.')
import fitz, numpy as np, cv2
from tools.omr.staged.record_io import load_record
rec, pdf, pi, tag = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
r = load_record(rec)['record']; obs = {o['id']: o for o in r['observations']}
pg = fitz.open(pdf)[pi]; pix = pg.get_pixmap(dpi=600, colorspace=fitz.csGRAY)
page = cv2.cvtColor(np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w), cv2.COLOR_GRAY2BGR)
gb = {o['subject']: o['detail']['bbox_page_px'] for o in r['observations']
      if o['quantity'] == 'glyph_box' and (o.get('detail') or {}).get('bbox_page_px')}
lad = {}
for o in r['observations']:
    if o['quantity'] == 'glyph_ladder':
        d = o.get('detail') or {}; lad[(o['subject'], d.get('candidate'))] = d
ink = collections.defaultdict(list)
for o in r['observations']:
    if o['quantity'] == 'ledger_rung_ink': ink[(o['subject'], o['detail']['candidate'])].append(o)
tiles = []
for k, rows in ink.items():
    d = lad.get(k) or {}
    if not d.get('found') or d.get('found') != d.get('expected') or any(o['value'] for o in rows): continue
    hb = gb.get(k[0]); 
    if not hb: continue
    ws = [o['detail']['window_page_px'] for o in rows]
    rungs = [gb.get(obs[x]['subject']) for x in (d.get('rungs') or []) if x in obs]
    rungs = [b for b in rungs if b]
    xs = [hb[0], hb[2]] + [w[0] for w in ws] + [w[2] for w in ws]; ys = [hb[1], hb[3]] + [w[1] for w in ws] + [w[3] for w in ws]
    X0, Y0 = max(0, int(min(xs) - 80)), max(0, int(min(ys) - 80)); X1, Y1 = int(max(xs) + 80), int(max(ys) + 80)
    t = page[Y0:Y1, X0:X1].copy()
    for b in rungs: cv2.rectangle(t, (int(b[0]-X0), int(b[1]-Y0)), (int(b[2]-X0), int(b[3]-Y0)), (255, 120, 0), 1)
    for o in rows:
        w = o['detail']['window_page_px']; cv2.rectangle(t, (int(w[0]-X0), int(w[1]-Y0)), (int(w[2]-X0), int(w[3]-Y0)), (0, 0, 255), 2)
    cv2.rectangle(t, (int(hb[0]-X0)-3, int(hb[1]-Y0)-3), (int(hb[2]-X0)+3, int(hb[3]-Y0)+3), (0, 160, 0), 2)
    o = rows[0]['detail']; cv2.putText(t, f"c{o['center']} L{o['left']} R{o['right']} a{o.get('adjacent')}", (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 0, 0), 1)
    tiles.append(t)
    if len(tiles) == 8: break
H = max(t.shape[0] for t in tiles)
tiles = [cv2.copyMakeBorder(t, 0, H - t.shape[0], 4, 4, cv2.BORDER_CONSTANT, value=(220, 220, 220)) for t in tiles]
rows_ = [np.hstack(tiles[i:i+4]) for i in range(0, len(tiles), 4)]
W = max(x.shape[1] for x in rows_)
rows_ = [cv2.copyMakeBorder(x, 0, 6, 0, W - x.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for x in rows_]
cv2.imwrite(f"out/print/beam-stem-ink-2.38/{tag}_ledger_missed.png", np.vstack(rows_)); print(len(tiles), 'tiles')
