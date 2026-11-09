import sys, glob
from PIL import Image
d, out, cols = sys.argv[1], sys.argv[2], int(sys.argv[3])
fs = sorted(glob.glob(d + "/tile_*.png"))
ims = [Image.open(f) for f in fs]
w = 760
ims = [i.resize((w, int(i.height * w / i.width))) for i in ims]
h = max(i.height for i in ims)
rows = (len(ims) + cols - 1) // cols
S = Image.new("RGB", (cols * (w + 6) + 6, rows * (h + 6) + 6), (255, 255, 255))
for k, im in enumerate(ims):
    S.paste(im, (6 + (k % cols) * (w + 6), 6 + (k // cols) * (h + 6)))
S.save(out)
