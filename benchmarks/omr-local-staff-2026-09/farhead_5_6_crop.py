"""lane-farhead-5-6: raw crop of a head with pixel-row ruler, for reading the page by eye. Read only.
  python3 farhead_5_6_crop.py <extract> <subject> <out.png> [pad_sp]"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2, numpy as np
import farhead_5_6_diag as D
import overnight_1004_report as R

src, s, out = sys.argv[1:4]
pad = float(sys.argv[4]) if len(sys.argv) > 4 else 5.0
data, rep = D.load(src)
g, r, cap, gl, ctx = D.read_one(rep, data, s)
gray = rep.gray_of(R.page_of(s))
x0, y0, x1, y1 = g["box"]
sp = cap["sp"]
X0, X1 = int(x0 - pad * sp), int(x1 + pad * sp)
Y0, Y1 = int(y0 - pad * sp), int(y1 + pad * sp)
crop = cv2.cvtColor(gray[Y0:Y1, X0:X1], cv2.COLOR_GRAY2BGR)
SC = 4
crop = cv2.resize(crop, None, fx=SC, fy=SC, interpolation=cv2.INTER_NEAREST)
cv2.rectangle(crop, (int((x0 - X0) * SC), int((y0 - Y0) * SC)), (int((x1 - X0) * SC), int((y1 - Y0) * SC)), (255, 0, 255), 1)
for y in gl:
    cv2.line(crop, (0, int((y - Y0) * SC)), (40, int((y - Y0) * SC)), (255, 150, 0), 1)
for y in cap.get("rungs", []):
    cv2.line(crop, (crop.shape[1] - 40, int((y - Y0) * SC)), (crop.shape[1], int((y - Y0) * SC)), (0, 0, 255), 1)
nf = (r.get("detail") or {}).get("note_first") or {}
if nf.get("line_y"):
    cv2.line(crop, (60, int((nf["line_y"] - Y0) * SC)), (100, int((nf["line_y"] - Y0) * SC)), (0, 170, 0), 1)
for y in range((Y0 // 10 + 1) * 10, Y1, 10):
    cv2.putText(crop, str(y), (crop.shape[1] // 2, int((y - Y0) * SC)), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 120, 0), 1)
cv2.imwrite(out, crop)
print("wrote", out, crop.shape, "origin", X0, Y0)
