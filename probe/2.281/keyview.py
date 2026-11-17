"""draw the corrected key's arcs (one box each, x0..x1 x y0..y1) on Brahms p0 for the look.  python3 keyview.py STAFF_A STAFF_B X0 X1 SCALE"""
import sys, json, pathlib
import cv2
sys.path.insert(0, '/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a6fffc49b728dc7cd/probe/2.274-r3')
import page as PG
KEY = json.load(open('/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a6fffc49b728dc7cd/benchmarks/omr-arc-binding-2026-10/key-brahms-p0-corrected.json'))
OUT = pathlib.Path('/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-session-placeholder-setup-6802ad/c91823fb-6cde-4194-b762-519aca0451f9/scratchpad/strips')
YB = {0: (1391, 1906), 1: (1777, 2289), 2: (2163, 2675), 3: (2548, 2999), 4: (2940, 3395), 5: (3295, 3807), 6: (3764, 4276), 7: (4113, 4628), 8: (4463, 4975), 9: (4969, 5484), 10: (5358, 5870), 11: (5805, 6320), 12: (6200, 6712), 13: (6551, 7063)}
a, b, X0, X1, S = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5])
img = PG.page()
y0, y1 = YB[a][0] - 60, YB[b][1] + 60
im = cv2.cvtColor(img[y0:y1, X0:X1], cv2.COLOR_GRAY2BGR)
for e in [2112, 2671, 3101, 3554, 4107, 4684, 5388]:
    if X0 <= e <= X1:
        cv2.line(im, (e - X0, 0), (e - X0, im.shape[0]), (255, 0, 255), 1)
for k in KEY['arcs']:
    if k['y1'] < y0 or k['y0'] > y1 or k['x1'] < X0 or k['x0'] > X1:
        continue
    col = (0, 140, 255) if k['kind'] == 'slur' else (0, 170, 0)
    if k['cross_system']:
        col = (200, 0, 200)
    cv2.rectangle(im, (k['x0'] - X0, k['y0'] - y0), (k['x1'] - X0, k['y1'] - y0), col, 3)
    cv2.putText(im, k['id'][1:], (k['x0'] - X0 + 5, k['y0'] - y0 + 38), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 255), 3)
im = cv2.resize(im, None, fx=S, fy=S, interpolation=cv2.INTER_AREA)
name = 'k%d_%d_%d_%d.png' % (a, b, X0, X1)
cv2.imwrite(str(OUT / name), im)
print(name, im.shape)
