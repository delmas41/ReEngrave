"""ROADMAP 2.108 blind tiles for Sean (`out/print/2.108-review/`).

Phone-sized (12 staff spaces x 32 px = 384 px wide), big tile NUMBER, the
question *What is the bracketed mark?*, the print as printed with ONE red corner
bracket on the subject box. NOTHING of ours is on a tile; what the detector
called it, what the rule did and where each came from is in manifest.json only.

The subjects are boxes of the pre-fill queue / truth of the Brahms 317803 pdf 0
hand-truth page store (a READ-ONLY copy):
  * REFUSED: detector pitch-bearing boxes at or past the reach of every staff
    (the title, a name in the margin, the page footer, a rest/accidental class);
  * CONTROLS the rule must keep: Sean's own confirmed heads standing farthest
    from a staff (the real far notes), and one queued box the rule KEEPS that
    stands in text just inside the reach.

usage: tiles.py OUTDIR PAGE_STORE.json PDF
"""
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, '.')
from tools.omr.hand_truth import session as S, store  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged import geometry as G  # noqa: E402

HDR = 56
QUESTION = "What is the bracketed mark?"
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
page = store.load(Path(sys.argv[2]))
img = render_page(Path(sys.argv[3]), page.pdf_page_index, dpi=page.dpi).rgb
bands = S.page_staff_bands(page)
sp = float(np.median([b[4] for b in bands]))


def dist(r):
    return G.distance_to_staff_spaces((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, bands)


def region(r):
    cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
    for c in page.cells:
        if c.kind != 'measure' and c.rect[0] <= cx <= c.rect[2] and c.rect[1] <= cy <= c.rect[3]:
            return c.kind
    return 'measure'


det = [q for q in page.queue if q.source.startswith('detector:') and G.is_pitch_bearing(q.cls)]
refused = sorted((q for q in det if dist(q.rect) >= G.OFF_STAFF_REACH_SPACES), key=lambda q: -((q.rect[2] - q.rect[0]) * (q.rect[3] - q.rect[1])))
picked, seen = [], set()
for q in refused:                       # largest box first (a letter's bowl, not a speck), one per ~600 px bucket, mixed regions
    key = (region(q.rect), round(q.rect[0] / 700), round(q.rect[1] / 500))
    if key in seen:
        continue
    seen.add(key)
    picked.append(q)
want = {'top': 2, 'margin': 2, 'bottom': 1}
chosen = []
for q in picked:
    k = region(q.rect)
    if want.get(k, 0) > 0:
        want[k] -= 1
        chosen.append(q)
rest_acc = [q for q in refused if not q.cls.startswith('notehead')]
if rest_acc:
    chosen.append(rest_acc[0])

items = [{"kind": "refused_off_staff", "id": q.id, "cls": q.cls, "rect": q.rect,
          "region": region(q.rect), "nearest_staff_spaces": round(dist(q.rect), 1),
          "source": q.source, "conf": q.score} for q in chosen]

truth_far = sorted((b for b in page.boxes if b.cls.startswith('notehead') and dist(b.rect) is not None),
                   key=lambda b: -dist(b.rect))[:3]
items += [{"kind": "control_real_far_note", "id": b.id, "cls": b.cls, "rect": b.rect,
           "region": region(b.rect), "nearest_staff_spaces": round(dist(b.rect), 1),
           "source": f"truth:{b.origin}"} for b in truth_far]
kept = sorted((q for q in det if dist(q.rect) < G.OFF_STAFF_REACH_SPACES and region(q.rect) != 'measure'),
              key=lambda q: -dist(q.rect))[:1]
items += [{"kind": "control_kept_just_inside_reach", "id": q.id, "cls": q.cls, "rect": q.rect,
           "region": region(q.rect), "nearest_staff_spaces": round(dist(q.rect), 1),
           "source": q.source, "conf": q.score} for q in kept]

random.Random(20261013).shuffle(items)
tiles = []
for n, it in enumerate(items, 1):
    x0, y0, x1, y1 = it["rect"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    half_w, half_h = 6 * sp, 6.5 * sp
    ax0, ay0 = int(max(0, cx - half_w)), int(max(0, cy - half_h))
    ax1, ay1 = int(min(img.shape[1], cx + half_w)), int(min(img.shape[0], cy + half_h))
    crop = img[ay0:ay1, ax0:ax1].copy()
    s = 32.0 / sp
    crop = cv2.resize(crop, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    bx0, by0, bx1, by1 = [int(round(v * s)) for v in (x0 - ax0, y0 - ay0, x1 - ax0, y1 - ay0)]
    L = 10
    for (px, py, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1), (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
        cv2.line(crop, (px, py), (px + dx * L, py), (220, 30, 30), 2)
        cv2.line(crop, (px, py), (px, py + dy * L), (220, 30, 30), 2)
    h, w = crop.shape[:2]
    canvas = np.full((h + HDR, max(w, 384), 3), 255, np.uint8)
    canvas[HDR:, :w] = crop
    cv2.putText(canvas, str(n), (10, HDR - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.9, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(canvas, QUESTION, (70 if n < 10 else 110, HDR - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                (60, 60, 60), 1, cv2.LINE_AA)
    cv2.line(canvas, (0, HDR - 1), (canvas.shape[1], HDR - 1), (200, 200, 200), 1)
    f = out / f"tile_{n:02d}.png"
    cv2.imwrite(str(f), cv2.cvtColor(canvas, cv2.COLOR_RGB2BGR))
    tiles.append({"n": n, "file": f.name, "question": QUESTION, "hidden": it,
                  "page_box_600dpi": [round(v) for v in it["rect"]], "dpi": page.dpi})
(out / "manifest.json").write_text(json.dumps(
    {"question": QUESTION, "tile_scale": "32 px per staff space",
     "reach_spaces": G.OFF_STAFF_REACH_SPACES, "tiles": tiles}, indent=1))
(out / "answers.template.json").write_text(json.dumps({f"tile_{t['n']:02d}": None for t in tiles}, indent=1))
print("wrote", len(tiles), "tiles to", out)
for t in tiles:
    print(t["n"], t["hidden"]["kind"], t["hidden"]["cls"], t["hidden"]["region"], t["hidden"]["nearest_staff_spaces"])
