"""python3 raw.py X0 Y0 X1 Y1 NAME [scale]: plain crop of page 0 (no overlays)"""
import sys
import cv2
import page as PG

x0, y0, x1, y1 = [int(v) for v in sys.argv[1:5]]
name = sys.argv[5]
s = float(sys.argv[6]) if len(sys.argv) > 6 else 0.6
im, _ = PG.crop(PG.page(), [x0, y0, x1, y1], pad=0)
im = cv2.resize(im, None, fx=s, fy=s)
cv2.imwrite("look/%s.png" % name, im)
print(im.shape)
