"""2.247: which synthetic natural stub does the stroke map split into a stem + a piece (as the real stubs do)? usage: stub_probe.py"""
import os
import sys

sys.path.insert(0, ".")
import numpy as np  # noqa: E402

from tools.omr.staged import accidental_family as AF  # noqa: E402
from tools.omr.staged import stroke_map as SM  # noqa: E402
from tools.omr.tests.test_accidental_family_2_201 import LINES, SP, _bar, _cell, _stem  # noqa: E402

os.environ[AF.KIND_ENV] = "0"
for y0, y1, bx, by, t in ((120, 260, 0, 245, 22), (100, 250, 0, 230, 22), (100, 250, 10, 230, 30), (110, 250, 0, 200, 40), (100, 240, 0, 210, 50)):
    img, raw = _cell()
    _stem(img, 400, 400 + y0, 400 + y1)
    _bar(img, (400 + bx, 400 + by), (460, 400 + by - 30), t)
    res = SM.map_strokes(img, SP, LINES, raw)
    ys, xs = np.nonzero(img == 0)
    box = (float(xs.min()), float(ys.min()), float(xs.max() + 1), float(ys.max() + 1))
    f = AF.family_row("accidentalFlat", box, res.strokes, SM.strokes_in_box(res, box), float(SP))
    print((y0, y1, bx, by, t), f["type"], f["why"], f["features"])
