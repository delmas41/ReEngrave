import sys, pickle, cv2
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import render as RN, groups as G, heads as H
ROOT = Path(__file__).resolve().parents[2]
plate, sub, out = sys.argv[1], sys.argv[2], sys.argv[3]
LIT_PDF = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
D = pickle.load(open(ROOT / f"out/2.278-micro/{plate}.pkl", "rb"))
h = D["heads"][sub]; P = D["pages"][h["page"]]; r = G.read_page(P)
st, L, why, det = H.decide(P, r, h, window="B2")
print(st, L, why, det, h["value"], h.get("cands"), h.get("stem_ref"))
sp = 15.4 if plate == "litolff" else 32.0
hb = h["bbox"]
boxes = [dict(rect=[hb[0] - 2, hb[1] - 2, hb[2] + 2, hb[3] + 2], color=(0, 160, 0))]
xs = [hb[0], hb[2]]; ys = [hb[1], hb[3]]
for o in det.get("strokes") or []:
    b = P["strokes"][o]["bbox"]; boxes.append(dict(rect=b, color=(0, 0, 255))); xs += [b[0], b[2]]; ys += [b[1], b[3]]
img = RN.page_image(RN.PDFS["brahms"] if plate == "brahms" else LIT_PDF, h["page"])
c = RN.crop(img, min(xs) - 6 * sp, min(ys) - 5 * sp, max(xs) + 6 * sp, max(ys) + 5 * sp, boxes, scale=1.5 if plate == "litolff" else 0.8, thick=1)
cv2.imwrite(out, c)
