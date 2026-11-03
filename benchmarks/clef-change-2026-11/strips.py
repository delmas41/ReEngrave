"""2.251 carry: one staff of several systems, print only (crops.strip), downscaled for a look.

python3 work-2.251/strips.py PLATE STAFF_LOCAL OUTDIR PG:SYS [PG:SYS ...]
"""
import os, sys
from PIL import Image
sys.path.insert(0, os.path.join(os.getcwd(), "work-2.251"))
import crops  # noqa: E402

plate, st, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
os.makedirs(out, exist_ok=True)
for a in sys.argv[4:]:
    pg, s = (int(v) for v in a.split(":"))
    im = crops.strip(plate, pg, s, st, 0, 99)
    im = im.resize((im.width // 3, im.height // 3), Image.LANCZOS)
    im.save(os.path.join(out, "%s-p%d-s%d-st%d.png" % (plate, pg, s, st)))
