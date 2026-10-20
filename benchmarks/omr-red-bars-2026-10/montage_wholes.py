"""usage: montage_wholes.py CROP_DIR TAG OUT.png [REMAINING.json] -- contact sheet of the print crops crop_wholes.py wrote for TAG, numbered;
a tile whose glyph is in REMAINING.json (the whole notes still written with the flag ON) gets a red frame."""
import glob
import json
import sys

from PIL import Image, ImageDraw

d, tag, out = sys.argv[1], sys.argv[2], sys.argv[3]
rem = set(g["glyph"] for g in json.load(open(sys.argv[4]))) if len(sys.argv) > 4 else set()
files = sorted(glob.glob("%s/whole-%s-*.png" % (d, tag)))
T, cols = 230, 6
rows = (len(files) + cols - 1) // cols
sheet = Image.new("RGB", (cols * T, rows * (T + 14)), "white")
dr = ImageDraw.Draw(sheet)
for i, f in enumerate(files):
    im = Image.open(f).convert("RGB")
    im.thumbnail((T - 4, T - 4))
    x, y = (i % cols) * T, (i // cols) * (T + 14)
    sheet.paste(im, (x + 2, y + 14))
    g = f.split("-")[-1][:-4].replace("_", "/")
    dr.text((x + 3, y + 1), "%d %s" % (i + 1, "REMAINS" if g in rem else ""), fill=(200, 0, 0) if g in rem else (0, 0, 0))
    if g in rem:
        dr.rectangle([x, y + 12, x + T - 1, y + T + 13], outline=(220, 0, 0), width=3)
sheet.save(out)
print(len(files), "tiles")
