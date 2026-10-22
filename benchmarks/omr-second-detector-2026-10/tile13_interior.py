"""2.114 round 2 item 2: why Sean's tile 13 (Litolff glyph/1/0/9/11/1, a real half) read filled. Raw-raster centre/ring (the 2.88 windows,
`gather.notehead_ink_under`'s own 30% shrink) for the production box and for a standard head box (1.4 x 1.1 sp) centred where the head's ink is.
usage: tile13_interior.py RASTER.npy(crop of page rows 2650: cols 1990:, 0 = ink) OUT.png"""
import sys
import numpy as np, cv2
sys.path.insert(0, ".")
from tools.omr.staged.gather import NOTEHEAD_INK_CENTER_SHRINK as SHR
a = np.load(sys.argv[1]); OX, OY = 1990, 2650
ink = a == 0
SP = 15.75
def win(box):
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    reg = ink[y0-OY:y1-OY, x0-OX:x1-OX]
    dx, dy = int(round(SHR*(x1-x0))), int(round(SHR*(y1-y0)))
    core = ink[y0+dy-OY:y1-dy-OY, x0+dx-OX:x1-dx-OX]
    c = core.mean()
    ring = (reg.sum() - core.sum()) / (reg.size - core.size)
    return round(float(c), 2), round(float(ring), 2), (x0+dx, y0+dy, x1-dx, y1-dy)
prod = (2050.8675, 2725.7425, 2069.1375, 2739.76)
cx, cy = 2063.5, 2737.0          # the head's own ink: spans x 2050-2077, y 2726-2749, the top staff line (y 2735-2738) through its middle
std = (cx - 0.7*SP, cy - 0.55*SP, cx + 0.7*SP, cy + 0.55*SP)
for name, b in (("production box", prod), ("standard head box centred on the head", std)):
    c, r, core = win(b)
    print(f"{name}: box {[round(v,1) for v in b]}  centre {c}  ring {r}  gap {round(r-c,2)}")
Z = 14
x0, y0, x1, y1 = 2036, 2716, 2086, 2760
crop = cv2.cvtColor(np.where(ink, 0, 255).astype(np.uint8)[y0-OY:y1-OY, x0-OX:x1-OX], cv2.COLOR_GRAY2BGR)
crop = cv2.resize(crop, None, fx=Z, fy=Z, interpolation=cv2.INTER_NEAREST)
T = lambda x, y: (int((x - x0) * Z), int((y - y0) * Z))
def rect(b, col, th=2): cv2.rectangle(crop, T(b[0], b[1]), T(b[2], b[3]), col, th)
rect(prod, (0, 140, 255)); rect(win(prod)[2], (255, 160, 0))          # orange box, light-blue centre window
rect(std, (0, 170, 0)); rect(win(std)[2], (200, 0, 200))              # green box, magenta centre window
cv2.imwrite(sys.argv[2], crop)
