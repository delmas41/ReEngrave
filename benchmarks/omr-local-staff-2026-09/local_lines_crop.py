"""lane-local-staff-lines probe: a crop (x4) of a truth-set head with the old (red) and new (blue) local lines.
  python3 local_lines_crop.py <doc> <page> <subject> <out.png>"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import jut_from_ink_eval as J
from tools.omr.annotate import far_head_reader as FH
doc, page, s, out = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
L, fp, far = J.prepare(doc, page)
h = [x for x in far if x["subject"] == s][0]
gl = L["staff_lines"]["staff/" + "/".join(s.split("/")[1:4])]
g = L["gray_B"]
x0, y0, x1, y1 = h["box"]
X0, X1, Y0, Y1 = int(x0 - 60), int(x1 + 60), int(y0 - 30), int(y1 + 110)
sc = 5
img = cv2.cvtColor(cv2.resize(g[Y0:Y1, X0:X1], None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST), cv2.COLOR_GRAY2BGR)
for kw, col in ((False, (0, 0, 255)), (True, (255, 120, 0))):
    FH.READER_KEYWORDS["local_lines_in_window"] = kw
    for y in FH.frame_lines_for_head(g, gl, h["box"]):
        yy = int((y - Y0) * sc)
        for x in range(0, img.shape[1], 14):
            cv2.line(img, (x, yy), (x + 7, yy), col, 1)
cv2.rectangle(img, (int((x0 - X0) * sc), int((y0 - Y0) * sc)), (int((x1 - X0) * sc), int((y1 - Y0) * sc)), (0, 140, 255), 2)
cv2.imwrite(out, img)
print("wrote", out, "region", X0, Y0, X1, Y1)
