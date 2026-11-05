"""Montage of census candidates (red dot = the unboxed hole's centre; green = detector box, magenta = rescue-pass box). 6 per image."""
import json
import sys
import numpy as np
import cv2
sys.path.insert(0, 'benchmarks/detector-unboxed-heads-2026-11')
import crop as cr

src = sys.argv[1]
cands = json.load(open(src))
S = 3.0
tag = sys.argv[2]
tiles = []
for i, c in enumerate(cands):
    f = 'out/print/2.267-unboxed/_tmp.png'
    x, y = c['cx'], c['cy']
    cr.make(c['doc'], c['page'], x - 80, y - 55, x + 80, y + 55, f, S, mark=[(x, y, '')])
    im = cv2.imread(f)
    cv2.putText(im, '%s#%d p%d (%d,%d)' % (tag, i, c['page'], x, y), (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
    tiles.append(im)
    cv2.imwrite('out/print/2.267-unboxed/%s_%02d_p%d_%d_%d.png' % (tag, i, c['page'], x, y), im)
for k in range(0, len(tiles), 6):
    grp = tiles[k:k + 6]
    while len(grp) % 2:
        grp.append(np.full_like(grp[0], 255))
    rows = [np.hstack(grp[j:j + 2]) for j in range(0, len(grp), 2)]
    cv2.imwrite('out/print/2.267-unboxed/%s_montage_%d.png' % (tag, k // 6), np.vstack(rows))
