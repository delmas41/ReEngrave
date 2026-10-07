"""quick look: raw crops of given Brahms arcs with the box in orange. python3 arc_line_look.py out.png arc [arc ...]"""
import sys, pickle
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2, numpy as np
from PIL import Image
from frame import render_page_matching_gather
from tools.library.score_library import library_root
PDF = library_root() / "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"
d = pickle.load(open('/private/tmp/claude-501/arc/brh.pkl', 'rb'))
A = {o['subject']: o for o in d['obs'] if o['quantity'] == 'arc_box'}
sp = {o['subject']: float(o['value']) for o in d['obs'] if o['quantity'] == 'staff_spacing'}
ims = []
for a in sys.argv[2:]:
    page = int(a.split('/')[1])
    G = cv2.cvtColor(np.asarray(render_page_matching_gather(PDF, page, 600).rgb), cv2.COLOR_RGB2BGR)
    b = A[a]['detail']['bbox_page_px']
    s = sp['staff/' + '/'.join(a.split('/')[1:4])]
    x0, x1, y0, y1 = int(b[0] - 3 * s), int(b[2] + 3 * s), int(b[1] - 3 * s), int(b[3] + 3 * s)
    c = G[y0:y1, x0:x1].copy()
    cv2.rectangle(c, (int(b[0]) - x0, int(b[1]) - y0), (int(b[2]) - x0, int(b[3]) - y0), (0, 120, 255), 2)
    sc = min(1.0, 700 / c.shape[1])
    c = cv2.resize(c, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
    cv2.putText(c, a, (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 200), 1)
    ims.append(c)
H = sum(i.shape[0] for i in ims) + 6 * len(ims)
W = max(i.shape[1] for i in ims)
out = np.full((H, W, 3), 255, np.uint8)
y = 0
for i in ims:
    out[y:y + i.shape[0], :i.shape[1]] = i; y += i.shape[0] + 6
cv2.imwrite(sys.argv[1], out)
