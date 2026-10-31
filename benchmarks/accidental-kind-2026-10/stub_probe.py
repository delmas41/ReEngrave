"""2.247: which synthetic flat-with-a-square-bowl does the stroke map read as TWO stems (as Sean's r1 tile 8 did)? usage: stub_probe.py"""
import os
import sys

sys.path.insert(0, ".")
import numpy as np  # noqa: E402

from tools.omr.staged import accidental_family as AF  # noqa: E402
from tools.omr.staged import stroke_map as SM  # noqa: E402
from tools.omr.tests.test_accidental_family_2_201 import LINES, SP, _bar, _cell, _stem  # noqa: E402

os.environ[AF.KIND_ENV] = "0"
for rtop, rw, t1, t2, gap in ((140, 20, 14, 10, 60), (130, 22, 8, 8, 60), (130, 22, 24, 22, 60), (120, 20, 20, 20, 55), (130, 20, 22, 22, 60)):
    img, raw = _cell()
    x, top = 400, 400
    _stem(img, x, top, top + 240)
    _stem(img, x + gap, top + rtop, top + 240, w=rw)
    _bar(img, (x, top + rtop + 10), (x + gap, top + rtop), t1)
    _bar(img, (x, top + 232), (x + gap, top + 232), t2)
    res = SM.map_strokes(img, SP, LINES, raw)
    ys, xs = np.nonzero(img == 0)
    box = (float(xs.min()), float(ys.min()), float(xs.max() + 1), float(ys.max() + 1))
    f = AF.family_row("accidentalFlat", box, res.strokes, SM.strokes_in_box(res, box), float(SP))
    print((rtop, rw, t1, t2, gap), f["type"], f["why"], f["features"])
