# ROADMAP 2.107 probe. Record-based REACH of ROADMAP 2.107's letter look: runs `letter_look.find_groups` / `read_page_group`
# (the entry points `gather_letter_look` uses) over a dumped glyph table + the PDF.
# python3 2.107_reach.py TAG PDF PAGE [PAGE...]  -> $LETTER_LOOK_SCRATCH/TAG.reach.json
"""record-based reach for letter_look, sharing gather's entry points.
usage: reach.py TAG PDF PAGE [PAGE...]   (needs TAG.glyphs.json from dump.py)"""
import sys, json, time, collections
sys.path.insert(0, '.')
import cv2, numpy as np
from tools.omr.staged import letter_look as LL
from tools.omr.preprocessing import render_page
S = os.environ.get('LETTER_LOOK_SCRATCH', '.')
import os
if os.environ.get('LL_MIN_SCALES'):
    LL.STRONG_MIN_SCALES = int(os.environ['LL_MIN_SCALES']); LL.WEAK_DECISIVE_SCALES = LL.STRONG_MIN_SCALES
if os.environ.get('LL_OUT'):
    OUTTAG = os.environ['LL_OUT']
tag, pdf = sys.argv[1], sys.argv[2]
OUTTAG = os.environ.get('LL_OUT', tag)
pages = [int(p) for p in sys.argv[3:]]
d = json.load(open(f'{S}/{tag}.glyphs.json'))
rows, geo = d['rows'], d['geo']
from tools.omr.yolo_detector import YoloDetector
det = YoloDetector('/Users/seanjohnson/Desktop/ReEngrave/omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt')
detect = lambda img, imgsz: det.detect_image(img, LL.LOOK_CONF_FLOOR, imgsz)
results = []
for pg in pages:
    t0 = time.time()
    page = render_page(pdf, pg, d['dpi'] or 600)
    gray = cv2.cvtColor(page.rgb, cv2.COLOR_BGR2GRAY)
    _, ink = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
    H, W = ink.shape
    g = geo[str(pg)]
    prow = [r for r in rows if r['page'] == pg and r['box']]
    dynboxes = [tuple(r['box']) for r in prow if str(r['cls']).startswith('dynamic')]
    cls_of = {r['key']: r['cls'] for r in prow}
    n_seeds = n_groups = 0
    for sysn, sd in g.items():
        sp = float(np.median([(st[2][-1] - st[2][0]) / max(1, len(st[2]) - 1) for st in sd['staves'] if len(st[2]) > 1] or [15.0]))
        ys = [y for st in sd['staves'] for y in st[2]]
        y0 = int(max(0, min(ys) - 8 * sp)); y1 = int(min(H, max(ys) + 8 * sp))
        clean = np.zeros((H, W), np.uint8); clean[y0:y1] = LL.erase_staff_lines(ink[y0:y1], sp)
        alt = np.zeros((H, W), np.uint8); alt[y0:y1] = LL.erase_staff_lines(ink[y0:y1], sp, slack_px=LL.ERASE_SLACK_TIGHT_PX)
        members = [(r['key'], tuple(r['box'])) for r in prow if r['system'] == int(sysn) and LL.is_seed_class(r['cls'])]
        n_seeds += len(members)
        boxes = dict(members)
        for grp in LL.find_groups(clean, members, sp):
            n_groups += 1
            t1 = time.time()
            gr = LL.read_page_group(clean, grp, boxes, sp, detect, dynboxes, clean_alt=alt)
            sp_ = gr.spelling
            results.append(dict(
                page=pg, sys=int(sysn), box_page=list(gr.box), status=gr.status, reason=gr.reason,
                text=sp_.text if sp_ else None, cands=list(sp_.candidates) if sp_ else None,
                tried=list(sp_.tried) if sp_ else None, near=gr.near, rival=gr.rival, unstable=gr.unstable,
                cover=gr.cover, seeds=[(k, cls_of.get(k)) for k in gr.seed_ids], secs=round(time.time() - t1, 2),
                regions=[(r.how, r.letters, [round(v) for v in r.box], r.conf, r.scales_seen, r.evidence) for r in (sp_.regions if sp_ else [])]))
    print(f'page {pg}: seeds {n_seeds} groups {n_groups} {round(time.time() - t0, 1)}s', flush=True)
json.dump(results, open(f'{S}/{OUTTAG}.reach.json', 'w'), default=str)
c = collections.Counter((r['status'], r['reason']) for r in results)
for k, v in c.most_common():
    print(v, k)
