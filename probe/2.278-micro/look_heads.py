"""MY look (ours, not evidence) at narrowed beam-family heads by what the prototype said. A seeded sample, one sheet; the head box is green, the owning stroke red.
usage: python3 probe/2.278-micro/look_heads.py brahms|litolff STATUS(beam|plain|undecided[:why]) N OUT.png [window]"""
import sys, pickle, random, json
from pathlib import Path
import cv2, numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import render as RN, groups as G, heads as H
ROOT = Path(__file__).resolve().parents[2]
plate, want, N, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
win = sys.argv[5] if len(sys.argv) > 5 else "B2"
LIT_PDF = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
D = pickle.load(open(ROOT / f"out/2.278-micro/{plate}.pkl", "rb"))
pdf = RN.PDFS["brahms"] if plate == "brahms" else LIT_PDF
res = H.run(D, sorted(D["pages"]), window=win)
st, _, why = want.partition(":")
sel = [r for r in res if (st == "all" or r["status"] == st) and (not why or r["why"] == why)]
rng = random.Random(278); rng.shuffle(sel); sel = sel[:N]
print(len(res), "narrowed;", want, "n=", len([r for r in res if r["status"] == st and (not why or r["why"] == why)]))
ims = []
for i, r in enumerate(sel, 1):
    P = D["pages"][r["page"]]; hb = r["bbox"]; sp = (P["strokes"][next(iter(P["strokes"]))]["sp"] or 32)
    boxes = [dict(rect=[hb[0] - 2, hb[1] - 2, hb[2] + 2, hb[3] + 2], color=(0, 160, 0))]
    xs = [hb[0], hb[2]]; ys = [hb[1], hb[3]]
    s = r["det"].get("stem")
    if s is not None:
        sb = P["strokes"][s]["bbox"]; xs += [sb[0], sb[2]]; ys += [sb[1], sb[3]]
    for o in r["det"].get("strokes") or []:
        b = P["strokes"][o]["bbox"]; boxes.append(dict(rect=[b[0] - 2, b[1] - 2, b[2] + 2, b[3] + 2], color=(0, 0, 255))); xs += [b[0], b[2]]; ys += [b[1], b[3]]
    img = RN.page_image(pdf, r["page"])
    c = RN.crop(img, min(xs) - 5 * sp, min(ys) - 3 * sp, max(xs) + 5 * sp, max(ys) + 3 * sp, boxes, scale=(0.6 if sp > 25 else 1.2), thick=1)
    k = 300.0 / max(c.shape[:2]); c = cv2.resize(c, (int(c.shape[1] * k), int(c.shape[0] * k)), interpolation=cv2.INTER_AREA)
    cv2.putText(c, f"{i} {r['status'][:5]} L={r['levels']} {r['why'] or ''}"[:30], (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 100, 0), 1)
    ims.append(c)
Hh = max(i.shape[0] for i in ims); W = max(i.shape[1] for i in ims); cols = 5
rows = []
for i in range(0, len(ims), cols):
    row = [cv2.copyMakeBorder(t, 0, Hh - t.shape[0], 0, W - t.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in ims[i:i + cols]]
    while len(row) < cols: row.append(np.full((Hh, W, 3), 255, np.uint8))
    rows.append(np.hstack(row))
cv2.imwrite(out, np.vstack(rows)); print(np.vstack(rows).shape)
