import sys, cv2
from tools.omr.preprocessing import render_page
from tools.omr.staged import lane_report as LR
plate, page = sys.argv[1], int(sys.argv[2])
x0, y0, x1, y1 = map(int, sys.argv[3:7])
out = sys.argv[7]
pdf = str(LR.LIB / LR.PLATES[plate]["pdf"])
pi = render_page(pdf, page, dpi=600)
im = cv2.cvtColor(pi.rgb, cv2.COLOR_RGB2BGR)[y0:y1, x0:x1]
im = cv2.resize(im, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
cv2.imwrite(out, im)
