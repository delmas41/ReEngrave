"""2.108 -- crop glyph subjects from a staged record out of the page render.

    python3 .../crop.py REC.json PDF OUTDIR subj [subj ...]
Boxes are drawn in red (a probe, for the lane's own eyes; blind tiles are cut
by tiles.py with nothing of ours drawn).
"""
import sys
from pathlib import Path

import cv2

sys.path.insert(0, '.')
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402

rec_path, pdf, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
doc = load_record(rec_path)
rec = doc['record'] if 'record' in doc else doc
boxes = {}
for o in rec['observations']:
    if o['quantity'] == 'glyph_box' and o['subject'] in sys.argv[4:]:
        boxes[o['subject']] = o
pages = {}
for s, o in boxes.items():
    pg = int(s.split('/')[1])
    if pg not in pages:
        pages[pg] = render_page(Path(pdf), pg, dpi=600).rgb
    x0, y0, x1, y1 = o['detail']['bbox_page_px']
    pad = 220
    img = pages[pg][max(0, int(y0) - pad):int(y1) + pad, max(0, int(x0) - pad):int(x1) + pad].copy()
    cv2.rectangle(img, (int(x0) - max(0, int(x0) - pad), int(y0) - max(0, int(y0) - pad)),
                  (int(x1) - max(0, int(x0) - pad), int(y1) - max(0, int(y0) - pad)), (255, 0, 0), 3)
    name = s.replace('/', '_') + '_' + str(o['value'][0]) + '.png'
    cv2.imwrite(str(out / name), img[..., ::-1])
    print(name, [round(v) for v in (x0, y0, x1, y1)])
