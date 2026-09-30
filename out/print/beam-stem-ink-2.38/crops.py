"""Print check for two CV readers on one gathered page (--through adjudicate):
 ledger: Q.LEDGER_RUNG_INK windows drawn on the page (why ~all read False);
 beam:   Q.BEAM_STEM_JOIN rows a duration verdict actually USED (2.38).
Crops cut from the PDF at the gather's own DPI (600). Subject = corner bracket."""
import sys, json, collections, random
sys.path.insert(0, '.')
import fitz, numpy as np, cv2
from tools.omr.staged.record_io import load_record
rec_path, pdf, page_idx, tag = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
out = "out/print/beam-stem-ink-2.38/"
r = load_record(rec_path)['record']
obs = {o['id']: o for o in r['observations']}
doc = fitz.open(pdf); pg = doc[page_idx]
pix = pg.get_pixmap(dpi=600, colorspace=fitz.csGRAY)
img = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w)
page = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

def bracket(im, x0, y0, x1, y1, col, L=14, t=3):
    for (x, y, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        cv2.line(im, (x, y), (x + dx * L, y), col, t); cv2.line(im, (x, y), (x, y + dy * L), col, t)

def crop(x0, y0, x1, y1, pad=90):
    X0, Y0 = max(0, int(x0 - pad)), max(0, int(y0 - pad))
    X1, Y1 = min(page.shape[1], int(x1 + pad)), min(page.shape[0], int(y1 + pad))
    return page[Y0:Y1, X0:X1].copy(), X0, Y0

def sheet(tiles, name):
    tiles = [cv2.copyMakeBorder(t, 4, 4, 4, 4, cv2.BORDER_CONSTANT, value=(200, 200, 200)) for t in tiles]
    H = max(t.shape[0] for t in tiles)
    tiles = [cv2.copyMakeBorder(t, 0, H - t.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in tiles]
    rows = [np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)]
    W = max(x.shape[1] for x in rows)
    rows = [cv2.copyMakeBorder(x, 0, 0, 0, W - x.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for x in rows]
    cv2.imwrite(out + name, np.vstack(rows))

# ---------- ledger ----------
glyph_box = {}
for o in r['observations']:
    if o['quantity'] == 'glyph_box' and (o.get('detail') or {}).get('bbox_page_px'):
        glyph_box[o['subject']] = o['detail']['bbox_page_px']
lr = [o for o in r['observations'] if o['quantity'] == 'ledger_rung_ink']
fail = collections.Counter()
for o in lr:
    d = o['detail']
    if o['value']: fail['FOUND'] += 1; continue
    why = []
    if d['center'] < 0.55: why.append('center')
    if d['left'] < 0.55 or d['right'] < 0.55: why.append('overhang')
    if d.get('adjacent') is not None and d['adjacent'] > 0.35: why.append('adjacent')
    if d.get('slant') is not None and why == []: why.append('slant')
    fail['+'.join(why) or 'other'] += 1
print(tag, 'ledger rows', len(lr), dict(fail.most_common()))
random.seed(1)
pick = random.sample([o for o in lr if not o['value']], min(8, sum(1 for o in lr if not o['value'])))
tiles = []
for o in pick:
    d = o['detail']; wx0, wy0, wx1, wy1 = d['window_page_px']
    hb = glyph_box.get(o['subject'])
    xs = [wx0, wx1] + ([hb[0], hb[2]] if hb else []); ys = [wy0, wy1] + ([hb[1], hb[3]] if hb else [])
    t, X0, Y0 = crop(min(xs), min(ys), max(xs), max(ys))
    cv2.rectangle(t, (int(wx0 - X0), int(wy0 - Y0)), (int(wx1 - X0), int(wy1 - Y0)), (0, 0, 255), 2)
    if hb: bracket(t, int(hb[0] - X0), int(hb[1] - Y0), int(hb[2] - X0), int(hb[3] - Y0), (0, 160, 0))
    cv2.putText(t, f"step{d['step']} c{d['center']:.2f} a{d.get('adjacent')}", (3, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
    tiles.append(t)
if tiles: sheet(tiles, f"{tag}_ledger_windows.png")

# ---------- beam join rows that a duration verdict USED ----------
def cell_affine(cell_key):
    for s, bb in glyph_box.items():
        if s.startswith('glyph/' + cell_key + '/'):
            for o in r['observations']:
                if o['quantity'] == 'glyph_box' and o['subject'] == s:
                    v = o['value']; cx, cy, cw = float(v[1]), float(v[2]), float(v[3])
                    up = cw / (bb[2] - bb[0]); return bb[0] - cx / up, bb[1] - cy / up, up
    return None
used = collections.Counter(); rows = []
for v in r['verdicts']:
    if v['quantity'] != 'duration': continue
    for u in v.get('used') or []:
        o = obs.get(u)
        if o and o['quantity'] == 'beam_stem_join':
            used[(o['value'], v['outcome'])] += 1; rows.append((o, v))
print(tag, 'beam_stem_join rows used by a duration verdict:', dict(used))
random.seed(2)
tiles = []
for val in (True, False):
    sel = [x for x in rows if x[0]['value'] is val]
    for o, v in random.sample(sel, min(4, len(sel))):
        ck = o['subject'].split('/', 1)[1]
        aff = cell_affine(ck)
        if not aff: continue
        ox, oy, up = aff
        stem = obs[o['detail']['stem_row_id']]['value']; beam = obs[o['detail']['beam_row_id']]['value']
        def pbox(b):  # b = [cls?, x, y, w, h] or [x,y,w,h]
            b = b[1:] if isinstance(b[0], str) else b
            return ox + b[0] / up, oy + b[1] / up, ox + (b[0] + b[2]) / up, oy + (b[1] + b[3]) / up
        try:
            s, b = pbox(stem), pbox(beam)
        except Exception as e:
            print('box shape', stem, beam); continue
        t, X0, Y0 = crop(min(s[0], b[0]), min(s[1], b[1]), max(s[2], b[2]), max(s[3], b[3]), pad=60)
        cv2.rectangle(t, (int(b[0] - X0), int(b[1] - Y0)), (int(b[2] - X0), int(b[3] - Y0)), (255, 150, 0), 2)
        bracket(t, int(s[0] - X0) - 6, int(s[1] - Y0), int(s[2] - X0) + 6, int(s[3] - Y0), (0, 160, 0) if val else (0, 0, 255))
        cv2.putText(t, ("JOINED" if val else "NOT JOINED") + f" -> {v['outcome']}", (3, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
        tiles.append(t)
if tiles: sheet(tiles, f"{tag}_beam_join_used.png")
