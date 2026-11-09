import sys, pickle, cv2, numpy as np
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
import render as RN, groups as G
D = pickle.load(open("out/2.278-micro/brahms.pkl", "rb")); P = D["pages"][0]
img = RN.page_image(RN.PDFS["brahms"], 0)
r = G.read_page(P)
tiles = []
for o in (1206, 1434, 1443, 1474, 1524, 1531, 2721, 2435):
    k = P["strokes"][o]; x0, y0, x1, y1 = k["bbox"]
    runs = r["certified"].get(o)
    st = [t[0] for run in runs for t in run] if runs else []
    boxes = [dict(rect=[x0 - 3, y0 - 3, x1 + 3, y1 + 3], color=(0, 0, 255))]
    for s in st:
        sb = P["strokes"][s]["bbox"]; boxes.append(dict(rect=sb, color=(255, 0, 0)))
    xs = [x0, x1] + [P["strokes"][s]["bbox"][i] for s in st for i in (0, 2)]
    ys = [y0, y1] + [P["strokes"][s]["bbox"][i] for s in st for i in (1, 3)]
    c = RN.crop(img, min(xs) - 120, min(ys) - 160, max(xs) + 120, max(ys) + 160, boxes, scale=0.45)
    cv2.putText(c, str(o), (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 128, 0), 1)
    tiles.append(c)
H = max(t.shape[0] for t in tiles); W = max(t.shape[1] for t in tiles)
rows = []
for i in range(0, len(tiles), 4):
    row = [cv2.copyMakeBorder(t, 0, H - t.shape[0], 0, W - t.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in tiles[i:i + 4]]
    while len(row) < 4: row.append(np.full((H, W, 3), 255, np.uint8))
    rows.append(np.hstack(row))
cv2.imwrite("out/2.278-micro/look_errs.png", np.vstack(rows))
print(np.vstack(rows).shape)
