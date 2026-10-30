"""Crop a system around a column x for the 10-minute look: barline_crop.py PDF page system x OUT.png [half_width_px]."""
import sys
import cv2
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves

pdf, page, sysi, x, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
hw = int(sys.argv[6]) if len(sys.argv) > 6 else 170
pws = detect_staves(render_page(pdf, page, dpi=600))
st = [s for s in pws.staves if s.system_index == sysi]
y0, y1 = min(s.top_y for s in st) - 40, max(s.bottom_y for s in st) + 40
img = pws.page.binary[max(0, y0):y1, max(0, x - hw):x + hw]
img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR) if img.ndim == 2 else img
cv2.line(img, (min(hw, x), 0), (min(hw, x), 12), (0, 0, 255), 3)
cv2.line(img, (min(hw, x), img.shape[0] - 12), (min(hw, x), img.shape[0]), (0, 0, 255), 3)
cv2.imwrite(out, img)
print(img.shape)
