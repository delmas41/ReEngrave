"""2.247: the type reader on synthetic marks of KNOWN shape (the 2.201 test cell): a natural whose right upright's lower part is faint
(kept 0..1 sp below the lower bar) vs a flat, with OMR_ACCIDENTAL_KIND off and on. usage: synthetic_probe.py"""
import os
import sys

sys.path.insert(0, ".")
import numpy as np  # noqa: E402

from tools.omr.staged import accidental_family as AF  # noqa: E402
from tools.omr.staged import stroke_map as SM  # noqa: E402
from tools.omr.tests.test_accidental_family_2_201 import LINES, SP, _bar, _cell, _flat, _stem  # noqa: E402


def nat_faint(img, x=400, top=400, keep=0):
    _stem(img, x, top, top + 240)
    _stem(img, x + 60, top + 140, top + 215 + keep)
    _bar(img, (x, top + 170), (x + 60, top + 140), 22)
    _bar(img, (x, top + 245), (x + 60, top + 215), 22)


def row(fn, **kw):
    img, raw = _cell()
    fn(img, **kw)
    res = SM.map_strokes(img, SP, LINES, raw)
    ys, xs = np.nonzero(img == 0)
    box = (float(xs.min()), float(ys.min()), float(xs.max() + 1), float(ys.max() + 1))
    return AF.family_row("accidentalFlat", box, res.strokes, SM.strokes_in_box(res, box), float(SP))


if __name__ == "__main__":
    for flag in ("0", "1"):
        os.environ[AF.KIND_ENV] = flag
        for name, fn, kw in (("natural, lower stroke kept 1.0 sp", nat_faint, {"keep": 100}), ("natural, kept 0.6 sp", nat_faint, {"keep": 60}),
                             ("natural, kept 0.3 sp", nat_faint, {"keep": 30}), ("natural, lower stroke lost", nat_faint, {"keep": 0}),
                             ("flat", _flat, {})):
            f = row(fn, **kw)
            print("KIND=%s %-36s -> %-8s %-30s shoulder=%s guess=%s" % (flag, name, f["type"], f["why"], f["features"].get("shoulder_sp"),
                                                                        [c["value"] for c in (AF.guess_of(f) or {}).get("candidates", [])]))
