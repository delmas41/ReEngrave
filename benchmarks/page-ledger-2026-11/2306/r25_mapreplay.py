"""Replay the page stroke map from pickled `map_strokes` inputs (gather_dump.py / approx_map.py). `run(D)` -> CellStrokes."""
import types
import numpy as np
from tools.omr.staged import stroke_map as SM
from tools.omr.staged import page_strokes as PG


def staff_of(D):
    scale = float(D["scale"])
    sp_small = SM.TARGET_SP_PX if scale < 1.0 else float(D["sp"])
    staves = [types.SimpleNamespace(**s) for s in D["staves"]]
    return PG.PageStaff(SM._reduce_float(D["raw"], scale), staves, scale, sp_small)


def run(D, staff=None):
    staff = staff or staff_of(D)
    return SM.map_strokes(D["erased"], D["sp"], [], D["raw"], keep_whole=D["keep_whole"], touch_boxes=D["touch_boxes"], staff_override=staff), staff


def near(res, box, pad=0):
    x0, y0, x1, y1 = box
    out = []
    for i, st in enumerate(res.strokes):
        x, y, w, h = st.box
        if x + w >= x0 - pad and x <= x1 + pad and y + h >= y0 - pad and y <= y1 + pad:
            out.append((i, st))
    return out
