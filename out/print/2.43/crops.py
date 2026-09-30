"""Print check for ROADMAP 2.43: every duration verdict that CHANGED between
the base arm (claude/acceptance-measure-notehead-box-e75821) and this arm,
at GATHER+ADJUDICATE (--through adjudicate). Crops cut from the PDF at the
gather's own DPI (600 CLI default). Subject = corner bracket on the head;
stem = green; beam stroke(s) = blue; the old value and the new value are
both printed on the tile so the crop states what changed and lets the print
answer which is right.

Usage: python3 out/print/2.43/crops.py <diff.json> <arm_record.json> <pdf>
                                        <page_idx> <tag> [--sample N --seed S]
"""
import sys
import json
import random
import collections

sys.path.insert(0, '.')
import fitz
import numpy as np
import cv2

from tools.omr.staged.record_io import load_record

diff_path, rec_path, pdf, page_idx, tag = (
    sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5])
sample_n = None
seed = 1
rest = sys.argv[6:]
for i, a in enumerate(rest):
    if a == "--sample":
        sample_n = int(rest[i + 1])
    if a == "--seed":
        seed = int(rest[i + 1])

out = "out/print/2.43/"

diff = json.load(open(diff_path))
changed = [p for p in diff["changed_pairs"]
           if p.get("family") == "note"
           and any(c.startswith("duration:") for c in p.get("changes", []))]
print(f"{tag}: {len(changed)} duration-changed note pairs in the diff")

if sample_n is not None and len(changed) > sample_n:
    random.seed(seed)
    changed = random.sample(changed, sample_n)
    print(f"{tag}: sampled {sample_n} with seed={seed}")

r = load_record(rec_path)['record']
obs_by_id = {o['id']: o for o in r['observations']}

glyph_box_page = {}   # subject -> bbox_page_px
glyph_box_canon = {}  # subject -> (smufl, x, y, w, h) canonical
for o in r['observations']:
    if o['quantity'] == 'glyph_box':
        d = o.get('detail') or {}
        if d.get('bbox_page_px'):
            glyph_box_page[o['subject']] = d['bbox_page_px']
        glyph_box_canon[o['subject']] = o['value']

doc = fitz.open(pdf)
pg = doc[page_idx]
pix = pg.get_pixmap(dpi=600, colorspace=fitz.csGRAY)
img = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w)
page = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)


def bracket(im, x0, y0, x1, y1, col, L=14, t=3):
    for (x, y, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1),
                          (x0, y1, 1, -1), (x1, y1, -1, -1)):
        cv2.line(im, (x, y), (x + dx * L, y), col, t)
        cv2.line(im, (x, y), (x, y + dy * L), col, t)


def crop(x0, y0, x1, y1, pad=110):
    X0, Y0 = max(0, int(x0 - pad)), max(0, int(y0 - pad))
    X1, Y1 = min(page.shape[1], int(x1 + pad)), min(page.shape[0], int(y1 + pad))
    return page[Y0:Y1, X0:X1].copy(), X0, Y0


def draw_staff_lines(t, X0, Y0, cell_key):
    """Draw this cell's own staff lines (Q.STAFF_LINES), in light grey."""
    staff_key = 'staff/' + '/'.join(cell_key.split('/')[:3])
    lines = [o for o in r['observations']
            if o['quantity'] == 'staff_lines'
            and o['subject'] == staff_key]
    if not lines:
        return
    v = lines[-1]['value']
    if not isinstance(v, (list, tuple)):
        return
    for ln in v:
        try:
            y = float(ln)
        except (TypeError, ValueError):
            continue
        yy = int(y - Y0)
        if 0 <= yy < t.shape[0]:
            cv2.line(t, (0, yy), (t.shape[1], yy), (180, 180, 180), 1)


def cell_affine(cell_key):
    """(origin_x_page, origin_y_page, up_scale) recovered from one glyph_box
    row in this cell that carries BOTH the canonical value and bbox_page_px
    -- same trick as `beam-stem-ink-2.38/crops.py`."""
    for s, bb in glyph_box_page.items():
        if s.startswith('glyph/' + cell_key + '/'):
            v = glyph_box_canon.get(s)
            if not v:
                continue
            cx, cy, cw = float(v[1]), float(v[2]), float(v[3])
            up = cw / (bb[2] - bb[0])
            return bb[0] - cx / up, bb[1] - cy / up, up
    return None


def to_page(box, aff):
    """box = (x, y, w, h) in CELL CANONICAL px -> page px, given `aff`."""
    ox, oy, up = aff
    x, y, w, h = box
    return (ox + x / up, oy + y / up, ox + (x + w) / up, oy + (y + h) / up)


def sheet(tiles, name):
    if not tiles:
        print(f"{tag}: nothing to draw for {name}")
        return
    tiles = [cv2.copyMakeBorder(t, 4, 4, 4, 4, cv2.BORDER_CONSTANT,
                                value=(200, 200, 200)) for t in tiles]
    H = max(t.shape[0] for t in tiles)
    tiles = [cv2.copyMakeBorder(t, 0, H - t.shape[0], 0, 0,
                                cv2.BORDER_CONSTANT, value=(255, 255, 255))
            for t in tiles]
    rows = [np.hstack(tiles[i:i + 3]) for i in range(0, len(tiles), 3)]
    W = max(x.shape[1] for x in rows)
    rows = [cv2.copyMakeBorder(x, 0, 0, 0, W - x.shape[1],
                               cv2.BORDER_CONSTANT, value=(255, 255, 255))
           for x in rows]
    cv2.imwrite(out + name, np.vstack(rows))
    print(f"{tag}: wrote {out}{name} ({len(tiles)} tiles)")


def short(v):
    if isinstance(v, str) and len(v) > 46:
        return v[:46] + "..."
    return v


tiles = []
manifest = []
for p in changed:
    gid = p['b']  # the ARM's own subject id (this record)
    hb = glyph_box_page.get(gid)
    if hb is None:
        print(f"{tag}: SKIP {gid} -- no page box on the arm record")
        continue
    cell_key = '/'.join(gid.split('/')[1:-1])
    aff = cell_affine(cell_key)
    xs = [hb[0], hb[2]]
    ys = [hb[1], hb[3]]
    stem_boxes, beam_boxes = [], []
    if aff is not None:
        for o in r['observations']:
            if o['subject'] != 'cell/' + cell_key:
                continue
            if o['quantity'] == 'stem':
                b = to_page(o['value'], aff)
                stem_boxes.append(b)
                xs += [b[0], b[2]]
                ys += [b[1], b[3]]
            elif o['quantity'] == 'beam_stroke':
                b = to_page(o['value'], aff)
                beam_boxes.append(b)
                xs += [b[0], b[2]]
                ys += [b[1], b[3]]
    t, X0, Y0 = crop(min(xs), min(ys), max(xs), max(ys))
    draw_staff_lines(t, X0, Y0, cell_key)
    for b in beam_boxes:
        cv2.rectangle(t, (int(b[0] - X0), int(b[1] - Y0)),
                      (int(b[2] - X0), int(b[3] - Y0)), (255, 150, 0), 2)
    for b in stem_boxes:
        cv2.rectangle(t, (int(b[0] - X0), int(b[1] - Y0)),
                      (int(b[2] - X0), int(b[3] - Y0)), (0, 160, 0), 2)
    bracket(t, int(hb[0] - X0), int(hb[1] - Y0),
           int(hb[2] - X0), int(hb[3] - Y0), (0, 0, 255))
    ch = [c for c in p['changes'] if c.startswith('duration:')][0]
    old, new = ch.split(' -> ')
    old = old[len('duration: '):]
    cv2.putText(t, gid, (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
    cv2.putText(t, f"WAS {short(old)}", (3, 30), cv2.FONT_HERSHEY_SIMPLEX,
               0.42, (0, 0, 160), 1)
    cv2.putText(t, f"NOW {short(new)}", (3, 46), cv2.FONT_HERSHEY_SIMPLEX,
               0.42, (0, 110, 0), 1)
    tiles.append(t)
    manifest.append({"subject": gid, "was": old, "now": new})

sheet(tiles, f"{tag}_changed.png")
with open(f"{out}{tag}_manifest.json", "w") as f:
    json.dump(manifest, f, indent=2)
print(f"{tag}: manifest -> {out}{tag}_manifest.json ({len(manifest)} entries)")
