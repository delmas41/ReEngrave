"""8 crops of GATED kept boxes: python3 gate_crops.py RESDIR OUTDIR   (4 per plate: 2 covering a real cut item, 2 covering none = the false ones). One thin red box each."""
import json
import os
import random
import sys

import cv2

ROOT = "/Users/seanjohnson/Desktop/ReEngrave/"
WT = ROOT + ".claude/worktrees/agent-aca2654680d85413f"
sys.path.insert(0, WT)
sys.path.insert(0, WT + "/benchmarks/omr-arc-binding-2026-10/barline-crop-trial-2026-11")
os.chdir(WT)
import analyze as AN  # noqa: E402
from crops import PDF  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402

resdir, outdir = sys.argv[1], sys.argv[2]
os.makedirs(outdir, exist_ok=True)
rng = random.Random(5)
for plate in ("litolff", "brahms"):
    g = json.load(open("%s/gate.%s.json" % (resdir, plate)))
    items, _, _ = AN.build_items(plate)
    good, bad = [], []
    for k in g["kept"]:
        hit = any(it["page"] == k["page"] and AN.far_cover(it, [k["cls"], k["conf"]] + k["box"])[0] for it in items)
        (good if hit else bad).append(k)
    picks = [("covers", x) for x in rng.sample(good, 2)] + [("nocover", x) for x in rng.sample(bad, 2)]
    for n, (tag, k) in enumerate(picks):
        rgb = render_page(PDF[plate], k["page"], dpi=600).rgb
        b = k["box"]
        sp = 16.0
        X0, Y0 = max(0, int(b[0] - 2 * sp)), max(0, int(b[1] - 3 * sp))
        X1, Y1 = min(rgb.shape[1], int(b[2] + 2 * sp)), min(rgb.shape[0], int(b[3] + 3 * sp))
        im = cv2.resize(rgb[Y0:Y1, X0:X1].copy(), None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
        cv2.rectangle(im, (int((b[0] - X0) * 4), int((b[1] - Y0) * 4)), (int((b[2] - X0) * 4), int((b[3] - Y0) * 4)), (0, 0, 255), 1)
        cv2.imwrite("%s/%s_p%d_%s_%d.png" % (outdir, plate, k["page"], tag, n), im)
        print(plate, k["page"], tag, n)
