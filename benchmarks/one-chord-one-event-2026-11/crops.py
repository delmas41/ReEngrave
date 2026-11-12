"""2.300 crop look: a plain crop (nothing of ours drawn) around the two events of each listed candidate pair.
    PYTHONPATH=. python3 benchmarks/one-chord-one-event-2026-11/crops.py PLATE EV.json OUTDIR page/system/staff/cell:i:j ...
EV.json from dump_events.py (event index i, j); BARS.json from capture.py (page boxes of every glyph).
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from PIL import Image  # noqa: E402

from tools.omr.staged import lane_report as LR  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402

plate, evf, out = sys.argv[1:4]
out = pathlib.Path(out)
out.mkdir(parents=True, exist_ok=True)
ev = {tuple(b["key"]): b for b in json.load(open(evf))["bars"]}
u = LR.PLATES[plate]["unit"]
pages = {}
for spec in sys.argv[4:]:
    k, i, j = spec.split(":")
    key = tuple(int(x) for x in k.split("/"))
    e = ev[key]["events"]
    gb = [h["page_box"] for n in (int(i), int(j)) for h in e[n]["heads"] if h.get("page_box")]
    x0 = min(g[0] for g in gb); y0 = min(g[1] for g in gb)
    x1 = max(g[2] for g in gb); y1 = max(g[3] for g in gb)
    p = key[0]
    if p not in pages:
        pages.clear()
        pages[p] = Image.fromarray(render_page(str(LR.LIB / LR.PLATES[plate]["pdf"]), p, dpi=600).rgb).convert("RGB")
    im = pages[p].crop((int(x0 - 4 * u), int(y0 - 6 * u), int(x1 + 4 * u), int(y1 + 6 * u)))
    sc = 640.0 / im.width if im.width < 640 else 1.0
    im = im.resize((int(im.width * sc), int(im.height * sc)))
    name = "%s_%s_%s.png" % (plate, k.replace("/", "-"), "%s%s" % (i, j))
    im.save(out / name)
    print(name, [(h["glyph"][-6:], h["pitch"], h["stem"], h["type"]) for n in (int(i), int(j)) for h in e[n]["heads"]])

# montage of everything written (3 columns, numbered) -> OUTDIR/montage.png
from PIL import ImageDraw  # noqa: E402
files = sorted(p for p in out.glob("*.png") if p.name != "montage.png")
ims = [Image.open(p) for p in files]
if ims:
    W = max(i.width for i in ims)
    cols = 2
    rows = (len(ims) + cols - 1) // cols
    rh = [max(i.height for i in ims[r * cols:(r + 1) * cols]) + 22 for r in range(rows)]
    sh = Image.new("RGB", (cols * (W + 10) + 10, sum(rh) + 10), (255, 255, 255))
    d = ImageDraw.Draw(sh)
    y = 6
    for r in range(rows):
        for c in range(cols):
            k = r * cols + c
            if k >= len(ims):
                break
            x = 10 + c * (W + 10)
            d.text((x, y), "%d %s" % (k + 1, files[k].stem[-22:]), fill=(0, 0, 0))
            sh.paste(ims[k], (x, y + 14))
        y += rh[r]
    sh.save(out / "montage.png")
    print("montage", len(ims))
