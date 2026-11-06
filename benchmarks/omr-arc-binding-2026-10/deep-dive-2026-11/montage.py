"""Stack crops into contact sheets for MY look (control): python3 montage.py DIR OUT_PREFIX [N_PER_SHEET]. Numbers are drawn on the sheet only."""
import pathlib
import sys

from PIL import Image, ImageDraw

d = pathlib.Path(sys.argv[1])
pre = sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 4
files = sorted(p for p in d.glob("*.png"))
for i in range(0, len(files), n):
    chunk = files[i:i + n]
    ims = [Image.open(f) for f in chunk]
    W = max(im.width for im in ims)
    H = sum(im.height + 22 for im in ims)
    sheet = Image.new("RGB", (W, H), (255, 255, 255))
    y = 0
    dr = ImageDraw.Draw(sheet)
    for f, im in zip(chunk, ims):
        dr.text((4, y + 4), f.stem, fill=(0, 0, 255))
        sheet.paste(im, (0, y + 22))
        y += im.height + 22
    sheet.save("%s_%02d.png" % (pre, i // n + 1))
    print("sheet", i // n + 1, [f.stem for f in chunk], sheet.size)
