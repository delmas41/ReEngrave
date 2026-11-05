"""One crop per case (red dot = the unboxed head; green = detector box, magenta = rescue-pass box, of the 20261103-night record) and, for every
case cell, the per-cell CONTROL: the cache served at conf 0.25 / iou 0.7 / class-wise vs the record's reader=='detector' boxes in that cell."""
import json
import sys
sys.path.insert(0, 'benchmarks/detector-unboxed-heads-2026-11')
import numpy as np
import cv2
import crop as cr
import pagecache as pc
import cachelook as cl
import recordrows as rr

cases = json.load(open('benchmarks/detector-unboxed-heads-2026-11/analysis.json'))
names = cl.class_names()
import os
os.makedirs('benchmarks/detector-unboxed-heads-2026-11/crops', exist_ok=True)
ctrl = []
for r in cases:
    cs = r['case']
    s = 3.0 if cs['doc'] == 'litolff' else 2.0
    f = 'benchmarks/detector-unboxed-heads-2026-11/crops/%s.png' % cs['id']
    cr.make(cs['doc'], cs['page'], cs['cx'] - 90, cs['cy'] - 60, cs['cx'] + 90, cs['cy'] + 60, f, s, mark=[(cs['cx'], cs['cy'], '')])
    im = cv2.imread(f)
    cv2.putText(im, '%s %s p%d' % (cs['id'], cs['doc'], cs['page']), (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
    cv2.imwrite(f, im)
    pws, cells, local = pc.page(cs['doc'], cs['page'])
    allrows = rr.rows(cs['doc'], cs['page'])
    for cell, key in pc.cells_at(cs['doc'], cs['page'], cs['cx'], cs['cy']):
        isz, o = cl.lookup(cell, confs=(0.25,))
        if 0.25 not in o:
            ctrl.append(dict(id=cs['id'], cell=key, note='no production entry'))
            continue
        served = cl.serve(cell, o[0.25][0], o[0.25][1])
        S = sorted((names[b[0]], *(round(v) for v in (*cl.to_page(cell, b[2], b[3]), *cl.to_page(cell, b[4], b[5])))) for b in served)
        recs = [o_ for o_ in allrows if o_['reader'] == 'detector' and o_['subject'].split('/')[2:5] == [str(key[0]), str(key[1]), str(key[2])]]
        Rr = sorted((o_['value'][0], *(round(v) for v in o_['detail']['bbox_page_px'])) for o_ in recs if o_['detail'].get('bbox_page_px'))
        ok = len(S) == len(Rr) and all(a[0] == b[0] and all(abs(x - y) <= 1.6 for x, y in zip(a[1:], b[1:])) for a, b in zip(S, Rr))
        ctrl.append(dict(id=cs['id'], cell=key, served=len(S), record_detector=len(Rr), identical_within_rounding=ok))
json.dump(ctrl, open('benchmarks/detector-unboxed-heads-2026-11/cell_control.json', 'w'), indent=1)
for c in ctrl:
    print(c)
