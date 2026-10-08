"""Show the page ink, the detection-blanked mask and the letter components around a point.
python3 probe_region.py tag x y   (page pixels, centre)  -> /private/tmp/dtmiss/probe.png"""
import pickle, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]; sys.path.insert(0, str(ROOT))
import cv2, numpy as np
from tools.omr import direction_text as DT
tag, cx, cy = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
pws, pd = pickle.load(open(f"/private/tmp/dtmiss/{tag}.pkl", "rb"))
sp = float(np.median([DT._spacing(s) for s in pws.staves]))
raw = DT._page_ink(pws.page); cfg = DT.DEFAULT_BAND_CONFIG
bl = DT._blank_detections(raw, pd, sp, cfg)
w, h = int(8 * sp), int(4 * sp)
sl = (slice(max(0, cy - h), cy + h), slice(max(0, cx - w), cx + w))
a = cv2.cvtColor(255 - raw[sl], cv2.COLOR_GRAY2BGR); b = cv2.cvtColor(255 - bl[sl], cv2.COLOR_GRAY2BGR)
comps = DT._letter_components(bl[sl], sp, cfg)
for (x, y, ww, hh, ar) in comps: cv2.rectangle(b, (x, y), (x + ww, y + hh), (0, 0, 255), 1)
for s_ in range(len(pd["systems"])):
    for st in pd["systems"][s_]["staves"]:
        for m in st["measures"]:
            for d in m.get("detections", []):
                bx = d.get("bbox_page")
                if bx and cx - w < bx[0] < cx + w and cy - h < bx[1] < cy + h:
                    cv2.rectangle(a, (int(bx[0]) - (cx - w), int(bx[1]) - (cy - h)), (int(bx[0] + bx[2]) - (cx - w), int(bx[1] + bx[3]) - (cy - h)), (255, 0, 0), 1)
                    cv2.putText(a, str(d.get("category"))[:8], (int(bx[0]) - (cx - w), int(bx[1]) - (cy - h) - 2), 0, 0.4, (255, 0, 0), 1)
out = np.vstack([a, np.full((4, a.shape[1], 3), 128, np.uint8), b])
cv2.imwrite("/private/tmp/dtmiss/probe.png", cv2.resize(out, None, fx=1.5, fy=1.5))
print("sp", sp, "comps", len(comps))
