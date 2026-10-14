"""2.120 crops: truth marks the table wrongly eliminates. Page raster only + small red corner bracket."""
import json, sys
sys.path.insert(0, ".")
from PIL import Image, ImageDraw
import descriptors as D
REPO = "/Users/seanjohnson/Desktop/ReEngrave"
p = json.load(open(REPO + "/data/hand-truth/pages/imslp317803/0.json"))
g = D.page_gray(REPO + "/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf", 0)
R = {r["id"]: r for r in json.load(open("measure/truth.json"))}
B = {b["id"]: b for b in p["boxes"]}
PXSP = 40
for i, q in enumerate(["q751", "q880", "q399", "q871", "q648", "b2967"], 1):
    r = B[q]["rect"]; sp = R[q]["d"]["sp_px"]; cx, cy = (r[0]+r[2])/2, (r[1]+r[3])/2
    hw = max(7.5*sp, (r[2]-r[0])/2 + 2*sp); hh = max(6*sp, (r[3]-r[1])/2 + 2*sp)
    H, W = g.shape
    x0, y0, x1, y1 = [int(round(v)) for v in (max(0, cx-hw), max(0, cy-hh), min(W, cx+hw), min(H, cy+hh))]
    im = Image.fromarray(g[y0:y1, x0:x1]).convert("RGB"); k = PXSP/sp
    im = im.resize((max(1, int(im.width*k)), max(1, int(im.height*k))), Image.LANCZOS); d = ImageDraw.Draw(im)
    bx0, by0, bx1, by1 = [(v-o)*k for v, o in zip(r, (x0, y0, x0, y0))]; pad = 0.18*PXSP
    bx0, by0, bx1, by1 = bx0-pad, by0-pad, bx1+pad, by1+pad
    L = max(8, 0.45*min(bx1-bx0, by1-by0)); red = (230, 0, 0)
    for (x, y, sx, sy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1), (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
        d.line([(x, y), (x+sx*L, y)], fill=red, width=4); d.line([(x, y), (x, y+sy*L)], fill=red, width=4)
    im.save("crops/C%d_%s.png" % (i, q)); print("crops/C%d_%s.png" % (i, q), B[q]["cls"], B[q]["cell_id"])
