"""MY look (ours, not evidence) at certified strokes beyond the hand-truth page: a seeded sample, one sheet.
usage: python3 probe/2.278-micro/look_certified.py brahms|litolff N OUT.png [seed]"""
import sys, pickle, random, json
from pathlib import Path
import cv2, numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import render as RN, groups as G
ROOT = Path(__file__).resolve().parents[2]
plate, N, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
seed = int(sys.argv[4]) if len(sys.argv) > 4 else 5278
LIT_PDF = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
D = pickle.load(open(ROOT / f"out/2.278-micro/{plate}.pkl", "rb"))
pdf = RN.PDFS["brahms"] if plate == "brahms" else LIT_PDF
allc = []
for p in sorted(D["pages"]):
    if plate == "brahms" and p == 0:
        continue
    P = D["pages"][p]; r = G.read_page(P)
    for o in r["certified"]:
        allc.append((p, o))
print(plate, "certified strokes off-p0:", len(allc))
rng = random.Random(seed); rng.shuffle(allc)
sel = allc[:N]
ims = []; meta = []
for i, (p, o) in enumerate(sel, 1):
    P = D["pages"][p]; r = G.read_page(P); k = P["strokes"][o]; sp = k["sp"]
    st = sorted({t[0] for run in r["certified"][o] for t in run}, key=lambda s: r["SG"][s]["x"])
    xs = [k["bbox"][0], k["bbox"][2]] + [r["SG"][s]["x"] for s in st]
    ys = [k["bbox"][1], k["bbox"][3]] + [v for s in st for v in (r["SG"][s]["top"], r["SG"][s]["bot"])]
    img = RN.page_image(pdf, p)
    b = k["bbox"]
    c = RN.crop(img, min(xs) - 4 * sp, min(ys) - 3 * sp, max(xs) + 4 * sp, max(ys) + 3 * sp, [dict(rect=[b[0] - 2, b[1] - 2, b[2] + 2, b[3] + 2])], scale=(0.6 if sp > 25 else 1.2), thick=1)
    s = 300.0 / max(c.shape[:2]); c = cv2.resize(c, (int(c.shape[1] * s), int(c.shape[0] * s)), interpolation=cv2.INTER_AREA)
    cv2.putText(c, str(i), (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 128, 0), 1)
    ims.append(c); meta.append((i, p, o, len(st), round(k["thick"], 2)))
H = max(i.shape[0] for i in ims); W = max(i.shape[1] for i in ims); cols = 6
rows = []
for i in range(0, len(ims), cols):
    row = [cv2.copyMakeBorder(t, 0, H - t.shape[0], 0, W - t.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in ims[i:i + cols]]
    while len(row) < cols: row.append(np.full((H, W, 3), 255, np.uint8))
    rows.append(np.hstack(row))
cv2.imwrite(out, np.vstack(rows)); print(np.vstack(rows).shape); print(meta)
json.dump(meta, open(out.replace(".png", ".json"), "w"))
