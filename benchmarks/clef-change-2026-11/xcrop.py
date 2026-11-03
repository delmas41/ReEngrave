"""2.251 carry: crops of the print (nothing drawn) around page x on one staff, side by side, labelled above.

python3 work-2.251/xcrop.py PLATE OUT.png PG:SYS:STAFF:X ...
"""
import os, sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.join(os.getcwd(), "work-2.251"))
import crops  # noqa: E402
import scan_claims as SC  # noqa: E402

plate, out = sys.argv[1], sys.argv[2]
ims = []
for a in sys.argv[3:]:
    pg, s, li, x = (int(float(v)) for v in a.split(":"))
    for ss, l2, t, cells in SC.staves_of(plate, pg):
        if (ss, l2) == (s, li):
            ly = t["line_ys"]
            sp = (ly[4] - ly[0]) / 4.0
            im = crops.page_img(plate, pg).crop((int(x - 5 * sp), int(ly[0] - 3 * sp), int(x + 4 * sp), int(ly[4] + 3 * sp)))
            im = im.resize((360, int(360 * im.height / im.width)))
            band = Image.new("RGB", (360, 20), "white")
            ImageDraw.Draw(band).text((4, 4), a, fill="black")
            c = Image.new("RGB", (360, im.height + 20), "white")
            c.paste(band, (0, 0)); c.paste(im, (0, 20))
            ims.append(c)
W = sum(i.width for i in ims) + 10 * len(ims)
H = max(i.height for i in ims)
sheet = Image.new("RGB", (W, H), "white")
x = 0
for i in ims:
    sheet.paste(i, (x, 0)); x += i.width + 10
sheet.save(out)
