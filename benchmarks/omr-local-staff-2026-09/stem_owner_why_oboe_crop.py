import sys
sys.path.insert(0, 'benchmarks/omr-local-staff-2026-09'); sys.path.insert(0, '.')
from frame import render_page_matching_gather
from tools.library.score_library import library_root
import numpy as np
from PIL import Image, ImageDraw
LIB = library_root()
pdf = LIB / "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
pi = render_page_matching_gather(pdf, 4, 600)
a = np.asarray(pi.rgb)
cx, cy, hw, hh = 1111, 2415, 60, 55
c = a[cy - hh:cy + hh, cx - hw:cx + hw]
S = 8
im = Image.fromarray(c).resize((c.shape[1] * S, c.shape[0] * S), Image.NEAREST).convert("RGB")
d = ImageDraw.Draw(im)
for y, col, lab in ((2393.75, (255, 0, 0), "rung 1 window y=2393.75"), (2409.5, (0, 150, 0), "rung 2 window y=2409.5"), (2425.25, (0, 0, 255), "rung 3 y=2425.25")):
    yy = (y - (cy - hh)) * S
    d.line([(0, yy), (im.width, yy)], fill=col, width=2)
    d.text((4, yy - 14), lab, fill=col)
bx = [1100.2125, 2411.8625, 1121.79, 2435.8025]
d.rectangle([(bx[0] - (cx - hw)) * S, (bx[1] - (cy - hh)) * S, (bx[2] - (cx - hw)) * S, (bx[3] - (cy - hh)) * S], outline=(255, 110, 0), width=3)
im.save('/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-notation-tile-fixes-2837c5/61ecbfe3-efe1-4b05-b3a2-0c894d475fc0/scratchpad/c7b.png')
