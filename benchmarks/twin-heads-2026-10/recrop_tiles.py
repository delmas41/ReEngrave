"""ROADMAP 2.213: re-cut lane_report's tiles taller and wider (Sean twice could not see a stem end).

    python3 benchmarks/twin-heads-2026-10/recrop_tiles.py KEY.json OUT_DIR

Window = the box grown to at least +-9 staff spaces tall and +-8 wide (more if the box is larger, +3 sp margin), ONE orange box, nothing else drawn.
Writes OUT_DIR/tiles/{tile_NN.png,sheet.png,README.md} and OUT_DIR/key.json (outside the tile folder).
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from PIL import Image, ImageDraw
from tools.omr.preprocessing import render_page
from tools.omr.staged.lane_report import LIB, PLATES, ORANGE

key = json.load(open(sys.argv[1])); out = pathlib.Path(sys.argv[2]); tdir = out / "tiles"; tdir.mkdir(parents=True, exist_ok=True)
for f in tdir.glob("*"): f.unlink()
W = 640; tiles = []; newkey = []; cache = {}
for n, it in enumerate(key, 1):
    plate, pg = it["plate"], it["page"]
    if (plate, pg) not in cache:
        cache.clear(); cache[(plate, pg)] = Image.fromarray(render_page(str(LIB / PLATES[plate]["pdf"]), pg, dpi=600).rgb).convert("RGB")
    im = cache[(plate, pg)]; u = PLATES[plate]["unit"]
    b = [it["box"][0] - 4, it["box"][1] - 4, it["box"][2] + 4, it["box"][3] + 4]
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    hw = max(8 * u, (b[2] - b[0]) / 2 + 3 * u); hh = max(9 * u, (b[3] - b[1]) / 2 + 3 * u)
    x0, y0, x1, y1 = max(0, int(cx - hw)), max(0, int(cy - hh)), min(im.width, int(cx + hw)), min(im.height, int(cy + hh))
    crop = im.crop((x0, y0, x1, y1)).copy()
    ImageDraw.Draw(crop).rectangle([round(b[0] - x0), round(b[1] - y0), round(b[2] - x0), round(b[3] - y0)], outline=ORANGE, width=max(2, int(u / 8)))
    crop = crop.resize((W, int(W * crop.height / crop.width))); crop.save(tdir / ("tile_%02d.png" % n)); tiles.append(crop)
    newkey.append(dict(it, tile=n, crop_origin=[x0, y0]))
cols = 3; rows = (len(tiles) + cols - 1) // cols; h = max(t.height for t in tiles)
sheet = Image.new("RGB", (cols * (W + 8) + 8, rows * (h + 30) + 8), (255, 255, 255)); d = ImageDraw.Draw(sheet)
for n, t in enumerate(tiles):
    x, y = 8 + (n % cols) * (W + 8), 8 + (n // cols) * (h + 30)
    d.text((x, y + 2), "%d" % (n + 1), fill=(0, 0, 0)); sheet.paste(t, (x, y + 18))
sheet.save(tdir / "sheet.png")
(tdir / "README.md").write_text("# Tiles\n\nEach picture is a piece of a scanned score page with ONE orange box on it and nothing else drawn. The orange box only says where to look.\n\n"
    "**Question, for every tile:** what is the note or rest value at the orange box (look at the whole stem and every beam on it)? Answer by tile number.\n")
(out / "key.json").write_text(json.dumps(newkey, indent=1, default=str))
