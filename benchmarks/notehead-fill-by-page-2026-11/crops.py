"""ROADMAP 2.326 small test (read-only, scratch): crops of named heads, cut from the page raster (600 dpi, the pipeline's
own render), 4x, a thin box on the head (green = Q.HEAD_INK's trimmed head, grey = the detector's box).
    python3 benchmarks/notehead-fill-by-page-2026-11/crops.py litolff name=glyph/... [name=glyph/...]
"""
import json
import pathlib
import sys

import cv2
import numpy as np

from tools.omr.preprocessing import render_page

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from measure import PDF  # noqa: E402

W = pathlib.Path(__file__).parent / "work"
OUT = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/project-mgmt-pipeline-review-e6581e/out/print/2.326-fill")


def main(doc, items):
    H = {h["subject"]: h for h in json.load(open(W / ("heads-%s.json" % doc)))["heads"]}
    P = {h["subject"]: h for h in json.load(open(W / ("pages-%s.json" % doc)))["heads"]}
    M = json.load(open(W / ("measures-%s.json" % doc)))
    by_page = {}
    for name, sub in items:
        by_page.setdefault(int(sub.split("/")[1]), []).append((name, sub))
    OUT.mkdir(parents=True, exist_ok=True)
    for p, its in sorted(by_page.items()):
        img = render_page(str(PDF[doc]), p, dpi=600)
        g = img.rgb if img.rgb.ndim == 3 else cv2.cvtColor(img.rgb, cv2.COLOR_GRAY2RGB)
        for name, sub in its:
            m = M.get(sub) or {}
            det = (P.get(sub) or {}).get("bbox_page_px")
            if det is None and sub in H:
                det = None
            box = m.get("box") or det
            if box is None:
                print("no box", sub)
                continue
            x0, y0, x1, y1 = box
            w = max(x1 - x0, 10)
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            r = int(3.0 * w)
            a, b = int(max(0, cx - r)), int(max(0, cy - r))
            crop = g[b:int(cy + r), a:int(cx + r)].copy()
            k = 4
            crop = cv2.resize(crop, None, fx=k, fy=k, interpolation=cv2.INTER_NEAREST)
            if det and m.get("box_from") == "trimmed":
                cv2.rectangle(crop, (int((det[0] - a) * k), int((det[1] - b) * k)), (int((det[2] - a) * k), int((det[3] - b) * k)),
                              (150, 150, 150), 1)
            col = (0, 170, 0) if m.get("box_from") == "trimmed" else (150, 150, 150)
            cv2.rectangle(crop, (int((x0 - a) * k) - 2, int((y0 - b) * k) - 2), (int((x1 - a) * k) + 2, int((y1 - b) * k) + 2), col, 1)
            fn = OUT / ("%s-%s-%s.png" % (doc, name, sub.replace("/", "_")))
            cv2.imwrite(str(fn), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
            print(fn.name)
        del img


if __name__ == "__main__":
    main(sys.argv[1], [tuple(x.split("=", 1)) for x in sys.argv[2:]])
