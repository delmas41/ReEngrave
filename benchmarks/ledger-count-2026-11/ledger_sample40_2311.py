"""ROADMAP 2.311 small test: seeded 40 far heads per plate (seed 2311311) -> our own look sheets (rule 7), 20 per sheet.

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/note-loss-funnel-2026-11/ledger_sample40.py INK.json OUTDIR

Each cell: crop of the page around the head, one thin orange box on the head; caption = number, R = ledger lines the record owes,
I = our stroke count, L = ledger count decided it / G = geometry extrapolation (ledger read refused).
"""
import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from checksheet import page_image
from ledger_heights import owed

o = json.load(open(sys.argv[1]))
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
picked = {}
for plate, hs in o.items():
    far = [h for h in hs if owed(h["final"]) > 0]
    far.sort(key=lambda h: h["key"])
    s = random.Random(2311311).sample(far, 40)
    picked[plate] = s
    for part in (0, 1):
        tiles = []
        for n, h in enumerate(s[part * 20:(part + 1) * 20]):
            sp = (h["lines"][4] - h["lines"][0]) / 4.0
            b = h["box"]
            cx = (b[0] + b[2]) / 2
            cy = (b[1] + b[3]) / 2
            top = min(h["lines"][0], cy) - 1.5 * sp
            bot = max(h["lines"][4], cy) + 1.5 * sp
            im = page_image(plate, h["page"]).crop((int(cx - 3.5 * sp), int(top), int(cx + 3.5 * sp), int(bot))).convert("RGB")
            d = ImageDraw.Draw(im)
            d.rectangle([b[0] - (cx - 3.5 * sp), b[1] - top, b[2] - (cx - 3.5 * sp), b[3] - top], outline=(255, 140, 0), width=2)
            k = 230 / im.width
            tiles.append((im.resize((230, int(im.height * k))),
                          "%d R%d I%d %s" % (part * 20 + n + 1, owed(h["final"]), h["ink_count"], "L" if h["ledger"] is not None else "G")))
        H = max(t.height for t, _ in tiles) + 16
        sh = Image.new("RGB", (5 * 236, 4 * H), "white")
        d = ImageDraw.Draw(sh)
        for i, (t, c) in enumerate(tiles):
            x, y = (i % 5) * 236, (i // 5) * H
            sh.paste(t, (x, y + 14))
            d.text((x + 2, y + 1), c, fill=(0, 0, 0))
        sh.save(out / ("%s_%d.png" % (plate, part + 1)))
json.dump({p: [h["key"] for h in s] for p, s in picked.items()}, open(out / "sample40_keys.json", "w"))
