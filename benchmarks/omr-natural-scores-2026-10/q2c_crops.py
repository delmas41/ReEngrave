"""ROADMAP 2.196 Q2 look. Montage of Sean-boxed (v13-v21, by hand) NATURALS that the v7/v8 label of the SAME cell does not have, cropped from the v7/v8 cell image
that hollow-ft trained on. The crop shows the printed natural; it was background in that training cell. (Model-free: boxes are the human completion.)
usage: q2c_crops.py DATA_ROOT OUT.png [N]"""
import glob, pathlib, sys
from PIL import Image, ImageDraw
ROOT, OUT = pathlib.Path(sys.argv[1]), sys.argv[2]; N = int(sys.argv[3]) if len(sys.argv) > 3 else 24
NAT = {61, 62, 171}
src = {}
for v in ("v7-2026-09-02-hollow", "v8-2026-09-02-hollow2-5pub"):
    for f in glob.glob(str(ROOT / v / "labels" / "*.txt")):
        src[pathlib.Path(f).stem] = (ROOT / v, [l.split() for l in open(f) if len(l.split()) >= 5])
tiles = []
for v in sorted(ROOT.glob("v1[3-9]-*")) + sorted(ROOT.glob("v2[01]-*")):
    for f in sorted(glob.glob(str(v / "labels" / "*.txt"))):
        s = pathlib.Path(f).stem
        if s not in src: continue
        sd, sl = src[s]
        done = [l.split() for l in open(f) if len(l.split()) >= 5]
        n_src = sum(int(p[0]) in NAT for p in sl)
        nat = [p for p in done if int(p[0]) in NAT]
        if len(nat) <= n_src: continue
        img = next(iter((sd / "images").glob(s + ".*")), None)
        if not img: continue
        im = Image.open(img).convert("RGB"); w, h = im.size
        for p in nat:
            x, y, bw, bh = (float(t) for t in p[1:5])
            # skip boxes present in src (same centre within 2%)
            if any(int(q[0]) in NAT and abs(float(q[1]) - x) < .02 and abs(float(q[2]) - y) < .02 for q in sl): continue
            pad = 0.6
            box = [max(0, (x - bw * (.5 + pad)) * w), max(0, (y - bh * (.5 + pad)) * h), min(w, (x + bw * (.5 + pad)) * w), min(h, (y + bh * (.5 + pad)) * h)]
            c = im.crop([int(t) for t in box]).resize((130, 200))
            ImageDraw.Draw(c).text((3, 3), v.name[:3] + " " + s[-14:], fill=(255, 0, 0))
            tiles.append(c)
tiles = tiles[:N]
cols = 8; rows = (len(tiles) + cols - 1) // cols
sheet = Image.new("RGB", (cols * 134, rows * 204), "white")
for i, t in enumerate(tiles): sheet.paste(t, ((i % cols) * 134, (i // cols) * 204))
sheet.save(OUT); print(len(tiles), "tiles ->", OUT)
