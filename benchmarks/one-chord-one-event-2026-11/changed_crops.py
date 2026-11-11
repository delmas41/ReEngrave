"""2.300: a plain crop of EVERY note gained / value-changed by the flag (from compare.py JSONs), one montage per plate.
    PYTHONPATH=. python3 benchmarks/one-chord-one-event-2026-11/changed_crops.py CMP.json OUTDIR
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from PIL import Image, ImageDraw  # noqa: E402

from tools.omr.staged import lane_report as LR  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402

c = json.load(open(sys.argv[1]))
out = pathlib.Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
plate = c["plate"]
u = LR.PLATES[plate]["unit"]
items = [("GAINED", x["key"], x["glyph"], "%s %s" % (x["pitch"], x["type"]), x["page_box"]) for x in c["notes_present_on_absent_off"]]
items += [("VALUE", x["key"], x["glyph"], "%s -> %s" % (x["off"][1], x["on"][1]), x["page_box"]) for x in c["values_changed"]]
items += [("LOST", x["key"], x["glyph"], "%s %s" % (x["pitch"], x["type"]), x["page_box"]) for x in c["notes_present_off_absent_on"]]
pg = {}
ims = []
for kind, key, glyph, what, box in items:
    p = key[0]
    if p not in pg:
        pg.clear()
        pg[p] = Image.fromarray(render_page(str(LR.LIB / LR.PLATES[plate]["pdf"]), p, dpi=600).rgb).convert("RGB")
    im = pg[p].crop((int(box[0] - 5 * u), int(box[1] - 5 * u), int(box[2] + 5 * u), int(box[3] + 5 * u)))
    d = ImageDraw.Draw(im)
    d.rectangle([int(5 * u) - 2, int(5 * u) - 2, int(5 * u + box[2] - box[0]) + 2, int(5 * u + box[3] - box[1]) + 2], outline=(255, 140, 0), width=2)
    im = im.resize((int(im.width * 520.0 / im.width), int(im.height * 520.0 / im.width)))
    t = Image.new("RGB", (520, im.height + 20), (255, 255, 255))
    ImageDraw.Draw(t).text((2, 2), "%s %s %s" % (kind, "/".join(map(str, key)), what), fill=(0, 0, 0))
    t.paste(im, (0, 20))
    ims.append(t)
if ims:
    cols = 3
    rows = (len(ims) + cols - 1) // cols
    rh = [max(i.height for i in ims[r * cols:(r + 1) * cols]) + 6 for r in range(rows)]
    sh = Image.new("RGB", (cols * 530, sum(rh)), (255, 255, 255))
    y = 0
    for r in range(rows):
        for k in range(cols):
            if r * cols + k < len(ims):
                sh.paste(ims[r * cols + k], (k * 530, y))
        y += rh[r]
    sh.save(out / ("changed_%s.png" % plate))
print(plate, len(ims), "items")
