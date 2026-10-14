"""ROADMAP 2.105 blind tiles for Sean (`out/print/2.105-review/`).
Phone-sized (12 staff spaces x 32 px = 384 px wide), big tile NUMBER, the question
*What is the bracketed mark?*, the print as printed with ONE red corner bracket on
the subject box. NOTHING of ours is on a tile; readings are in manifest.json only.

usage: tiles.py OUTDIR SPEC.json
SPEC = [{"mv": "litolff", "record": ARM_RECORD, "key": "glyph/..", "kind": "..", "base": "..", "arm": ".."}, ...]
(order is shuffled with a fixed seed so kinds are not grouped)"""
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np

from lib105 import crop, page_rgb, staff_spacing
from tools.omr.staged.readout import load_run

HDR = 56
QUESTION = "What is the bracketed mark?"
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
spec = json.loads(Path(sys.argv[2]).read_text())
random.Random(20261013).shuffle(spec)
runs = {}
tiles = []
for n, it in enumerate(spec, 1):
    run = runs.setdefault(it["record"], load_run(it["record"]))
    sps = staff_spacing(run)
    g = run.glyphs[it["key"]]
    c = crop(page_rgb(it["mv"], g.page), [(*g.box_page, (220, 30, 30))], sps[g.staff_key], half_h_sp=5.5)
    c = c[:, :384]
    h, w = c.shape[:2]
    im = np.full((h + HDR, w, 3), 255, np.uint8)
    im[HDR:] = c
    cv2.putText(im, str(n), (10, HDR - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.9, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(im, QUESTION, (70 if n < 10 else 110, HDR - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (60, 60, 60), 1, cv2.LINE_AA)
    cv2.line(im, (0, HDR - 1), (w, HDR - 1), (200, 200, 200), 1)
    f = out / f"tile_{n:02d}.png"
    cv2.imwrite(str(f), cv2.cvtColor(im, cv2.COLOR_RGB2BGR))
    tiles.append({"n": n, "file": f.name, "question": QUESTION, "hidden": {k: v for k, v in it.items() if k != "record"},
                  "page_box_600dpi": [round(v) for v in g.box_page], "dpi": 600})
(out / "manifest.json").write_text(json.dumps({"question": QUESTION, "tile_scale": "32 px per staff space", "tiles": tiles}, indent=1))
(out / "answers.template.json").write_text(json.dumps({f"tile_{t['n']:02d}": None for t in tiles}, indent=1))
print("wrote", len(tiles), "tiles to", out)
