"""render Brahms p0 staff strips with Sean's hand arc boxes (numbered by printed arc P) and barline edges, for the key look."""
import sys, json, pathlib
import cv2, numpy as np
sys.path.insert(0, '/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a6fffc49b728dc7cd/probe/2.274-r3')
import page as PG
from load import printed
OUT = pathlib.Path('/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-session-placeholder-setup-6802ad/c91823fb-6cde-4194-b762-519aca0451f9/scratchpad/strips')
OUT.mkdir(exist_ok=True, parents=True)
img = PG.page()
P, H = printed()
EDGES = [2112, 2671, 3101, 3554, 4107, 4684, 5388]
YB = {0: (1391, 1906), 1: (1777, 2289), 2: (2163, 2675), 3: (2548, 2999), 4: (2940, 3395), 5: (3295, 3807), 6: (3764, 4276), 7: (4113, 4628), 8: (4463, 4975), 9: (4969, 5484), 10: (5358, 5870), 11: (5805, 6320), 12: (6200, 6712), 13: (6551, 7063)}
S = float(sys.argv[3]) if len(sys.argv) > 3 else 0.33
a, b = int(sys.argv[1]), int(sys.argv[2])
x0, x1 = (int(sys.argv[4]), int(sys.argv[5])) if len(sys.argv) > 5 else (1200, 5520)
y0, y1 = YB[a][0] - 60, YB[b][1] + 60
im = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_GRAY2BGR)
for e in EDGES:
    if x0 <= e <= x1:
        cv2.line(im, (e - x0, 0), (e - x0, im.shape[0]), (255, 0, 255), 2)
for p in P:
    for r in p['rects']:
        if r[1] < y1 and r[3] > y0 and r[2] > x0 and r[0] < x1:
            col = (0, 140, 255) if p['kind'] == 'slur' else (0, 160, 0)
            cv2.rectangle(im, (int(r[0] - x0), int(r[1] - y0)), (int(r[2] - x0), int(r[3] - y0)), col, 3)
            cv2.putText(im, str(p['n'] if 'n' in p else '?'), (int(r[0] - x0) + 4, int(r[1] - y0) + 40), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 255), 3)
im = cv2.resize(im, None, fx=S, fy=S, interpolation=cv2.INTER_AREA)
cv2.imwrite(str(OUT / ('s%d_%d_%d_%d.png' % (a, b, x0, x1))), im)
print(im.shape)
