"""2.306 r14, MY look: crops of the flag/beam rows `r14_flag_tally.py` wrote (filter by kind/what), Sean's head blue, the beam box the exporter
grouped the note under red. One PNG, 3 per row. Usage: r14_look_beams.py PAGE.png TALLY.json OUT.png KIND WHAT"""
import json
import sys

from PIL import Image, ImageDraw

sys.path[:0] = [".", "benchmarks/note-loss-funnel-2026-11"]
import judge as J  # noqa: E402

page_png, tally_p, out_p, kind, what = sys.argv[1:6]
rows = [r for r in json.load(open(tally_p)) if r["kind"] == kind and r["what"] == what]
page, truth, u, in_scope, swept = J.load_truth(J.TRUTH)
tid = {t.id: t for t in truth}
img = Image.open(page_png).convert("RGB")
tiles = []
seen = set()
for r in rows:
    if r["id"] in seen:
        continue
    seen.add(r["id"])
    t = tid[r["id"]]
    im = img.copy()
    d = ImageDraw.Draw(im)
    d.rectangle([t.rect[0] - 3, t.rect[1] - 3, t.rect[2] + 3, t.rect[3] + 3], outline=(0, 0, 255), width=3)
    p = r.get("pick")
    if isinstance(p, dict):
        b = p["box"]
        d.rectangle([b[0], b[1], b[0] + b[2], b[1] + b[3]], outline=(255, 0, 0), width=3)
    cx, cy = (t.rect[0] + t.rect[2]) / 2, (t.rect[1] + t.rect[3]) / 2
    c = im.crop((int(cx - 10 * u), int(cy - 6 * u), int(cx + 10 * u), int(cy + 6 * u)))
    ImageDraw.Draw(c).text((4, 4), "%s %s %s" % (r["id"], r["rg"], "" if isinstance(p, dict) else p), fill=(200, 0, 0))
    tiles.append(c.resize((c.width // 2, c.height // 2)))
cols = 3
W, H = tiles[0].width, tiles[0].height
out = Image.new("RGB", (W * cols, H * ((len(tiles) + cols - 1) // cols)), "white")
for i, c in enumerate(tiles):
    out.paste(c, ((i % cols) * W, (i // cols) * H))
out.save(out_p)
print(len(tiles))
