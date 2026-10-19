"""2.170: 2x2 montages of a sheet directory (sNN.png -> mNN.png). usage: montage_2_170.py DIR"""
import glob
import sys

from PIL import Image

S = sys.argv[1].rstrip("/") + "/"
fs = sorted(glob.glob(S + "s*.png"))
for j in range(0, len(fs), 4):
    ims = [Image.open(f) for f in fs[j:j + 4]]
    W = max(i.width for i in ims)
    H = max(i.height for i in ims)
    m = Image.new("RGB", (2 * W, 2 * H), "white")
    for q, i in enumerate(ims):
        m.paste(i, ((q % 2) * W, (q // 2) * H))
    m.thumbnail((1600, 1600))
    m.save(S + "m%02d.png" % (j // 4))
print(len(fs), "tiles")
