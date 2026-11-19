"""ROADMAP 2.326 small test: blind tiles for Sean (one staff, nothing of ours drawn but a thin box sized to the head).
    PYTHONPATH=. python3 benchmarks/notehead-fill-by-page-2026-11/blind.py
"""
import json
import pathlib
import sys

import cv2

from tools.omr.preprocessing import render_page

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from measure import PDF  # noqa: E402

W = pathlib.Path(__file__).parent / "work"
SL = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261117-night/%s/observations.jsonl"
OUT = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/project-mgmt-pipeline-review-e6581e/out/print/2.326-fill/blind")
TILES = [("litolff", "glyph/2/0/7/4/5")]


def staff_rows(doc, page, y):
    best = None
    for line in open(SL % doc):
        if '"staff_lines"' not in line:
            continue
        o = json.loads(line)
        if o.get("quantity") != "staff_lines" or not str(o["subject"]).startswith("staff/%d/" % page):
            continue
        ys = o["value"]
        d = 0 if min(ys) <= y <= max(ys) else min(abs(y - min(ys)), abs(y - max(ys)))
        if best is None or d < best[0]:
            best = (d, min(ys), max(ys))
    return best


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    key = {}
    for i, (doc, sub) in enumerate(TILES, 1):
        m = json.load(open(W / ("measures-%s.json" % doc)))[sub]
        x0, y0, x1, y1 = m["box"]
        p = int(sub.split("/")[1])
        _, s0, s1 = staff_rows(doc, p, (y0 + y1) / 2)
        sp = (s1 - s0) / 4.0
        top, bot = min(s0, y0) - 2.5 * sp, max(s1, y1) + 2.5 * sp
        img = render_page(str(PDF[doc]), p, dpi=600)
        a, b = int(max(0, (x0 + x1) / 2 - 9 * sp)), int(max(0, top))
        crop = img.rgb[b:int(bot), a:int((x0 + x1) / 2 + 9 * sp)].copy()
        k = 3
        crop = cv2.resize(crop, None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC)
        cv2.rectangle(crop, (int((x0 - a) * k) - 3, int((y0 - b) * k) - 3), (int((x1 - a) * k) + 3, int((y1 - b) * k) + 3),
                      (31, 111, 235), 1)
        fn = "tile_%02d.png" % i
        cv2.imwrite(str(OUT / fn), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
        key[fn] = {"doc": doc, "subject": sub, "page_box": m["box"],
                   "written_today": "half, blue (2.220 head_ink_hollow_over_black)",
                   "question": "Is the boxed notehead hollow (a half) or filled (a quarter), or not a notehead?"}
    json.dump(key, open(OUT.parent / "blind-key.json", "w"), indent=1)
    print(key)


main()
