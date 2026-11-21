"""Cut numbered tiles (one staff, ONE thin red box on the mark, nothing else drawn) from the page at 600 dpi; a sheet PNG + key json.
specs json: [{plate, page, box:[x0,y0,x1,y1] page px, half_w_sp?, half_h_sp?, key:{...what the file writes...}}]"""
import sys, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))
from PIL import Image, ImageDraw, ImageFont
from tools.omr.preprocessing import render_page
LIB = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library")
PDF = {"litolff": "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
UNIT = {"litolff": 15.75, "brahms": 32.0}
specs = json.load(open(sys.argv[1]))
out_png, out_key, tdir = sys.argv[2], sys.argv[3], pathlib.Path(sys.argv[4])
tdir.mkdir(parents=True, exist_ok=True)
W = 560
try:
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 34)
except Exception:
    font = ImageFont.load_default()
cache = {}
tiles, key = [], []
for n, s in enumerate(specs, 1):
    k = (s["plate"], s["page"])
    if k not in cache:
        cache.clear()
        cache[k] = Image.fromarray(render_page(str(LIB / PDF[s["plate"]]), s["page"], dpi=600).rgb).convert("RGB")
    im = cache[k]
    u = UNIT[s["plate"]]
    b = [float(v) for v in s["box"]]
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    hw = max(s.get("half_w_sp", 7) * u, (b[2] - b[0]) / 2 + 3 * u)
    hh = max(s.get("half_h_sp", 6) * u, (b[3] - b[1]) / 2 + 2 * u)
    x0, y0 = max(0, int(cx - hw)), max(0, int(cy - hh))
    x1, y1 = min(im.width, int(cx + hw)), min(im.height, int(cy + hh))
    crop = im.crop((x0, y0, x1, y1)).copy()
    ImageDraw.Draw(crop).rectangle([round(b[0] - 3 - x0), round(b[1] - 3 - y0), round(b[2] + 3 - x0), round(b[3] + 3 - y0)],
                                   outline=(220, 0, 0), width=max(2, int(u / 10)))
    scale = W / crop.width
    crop = crop.resize((W, max(1, int(crop.height * scale))))
    t = Image.new("RGB", (W, crop.height + 44), (255, 255, 255))
    ImageDraw.Draw(t).text((6, 4), str(n), fill=(0, 0, 0), font=font)
    t.paste(crop, (0, 44))
    t.save(tdir / ("tile_%02d.png" % n))
    tiles.append(t)
    key.append({**s.get("key", {}), **dict(tile=n, plate=s["plate"], page=s["page"], box=b, crop_origin=[x0, y0])})
cols = 3
rows = (len(tiles) + cols - 1) // cols
h = max((t.height for t in tiles), default=10)
sheet = Image.new("RGB", (cols * (W + 10) + 10, max(1, rows) * (h + 10) + 10), (235, 235, 235))
for i, t in enumerate(tiles):
    sheet.paste(t, (10 + (i % cols) * (W + 10), 10 + (i // cols) * (h + 10)))
sheet.save(out_png)
json.dump(key, open(out_key, "w"), indent=1, default=str)
print("tiles", len(tiles), "->", out_png)
