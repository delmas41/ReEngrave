"""Crops for the three right->wrong places (lane-judged-moves-1029). One staff, ONE thin orange box on the judged
subject, nothing else drawn, in out/print/judged-moves-1029/tiles/. diag/ holds the same crop with the
duplicate box in blue (for the lane report only). key.json sits OUTSIDE tiles/."""
import json
import pathlib
import sys

sys.path.insert(0, '.')
from PIL import Image, ImageDraw
from tools.omr.preprocessing import render_page

PDF = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
       "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf")
U = 15.75
OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "out/print/judged-moves-1029")
PLACES = json.loads((pathlib.Path(__file__).parent / "jm_places.json").read_text())
ORANGE, BLUE = (255, 140, 0), (30, 111, 235)
(OUT / "tiles").mkdir(parents=True, exist_ok=True)
(OUT / "diag").mkdir(parents=True, exist_ok=True)
cache = {}
for n, p in enumerate(PLACES, 1):
    pg = p["page"]
    if pg not in cache:
        cache.clear()
        cache[pg] = Image.fromarray(render_page(PDF, pg, dpi=600).rgb).convert("RGB")
    im = cache[pg]
    b = p["box"]
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    x0, y0, x1, y1 = int(cx - 7 * U), int(cy - 4.5 * U), int(cx + 7 * U), int(cy + 4.5 * U)
    for kind in ("tiles", "diag"):
        crop = im.crop((x0, y0, x1, y1)).copy()
        d = ImageDraw.Draw(crop)
        d.rectangle([b[0] - 2 - x0, b[1] - 2 - y0, b[2] + 2 - x0, b[3] + 2 - y0], outline=ORANGE, width=1)
        if kind == "diag":
            o = p["other_box"]
            d.rectangle([o[0] - 2 - x0, o[1] - 2 - y0, o[2] + 2 - x0, o[3] + 2 - y0], outline=BLUE, width=1)
        crop = crop.resize((crop.width * 4, crop.height * 4), Image.LANCZOS)
        crop.save(OUT / kind / ("place_%d.png" % n))
(OUT / "key.json").write_text(json.dumps(PLACES, indent=1))
print("wrote", len(PLACES), "places to", OUT)
