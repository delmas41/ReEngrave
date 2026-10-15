"""2.120 round 2 -- descriptors.py (round 1, unchanged) plus ONE new fact: where the mark stands across the
system's left edge (needed because the first bar's cell begins AT the brace, so a brace never read as MARGIN).
xs = (mark centre x - system's first cell x0) / local sp. left_edge = the Sean-ruled place for braces/brackets."""
import descriptors as D1
from descriptors import page_gray, StaffModel  # noqa: F401

LEFT_EDGE_LO_SP = -3.0   # CUT: measured braces on Brahms p0 sit at -0.67 .. +1.03 sp; margin ~2 sp each side
LEFT_EDGE_HI_SP = 2.0


def describe(rect, gray, model):
    d = D1.describe(rect, gray, model)
    cx = (rect[0] + rect[2]) / 2
    c = model.nearest(cx, (rect[1] + rect[3]) / 2)
    d["xs"] = (cx - model.sys_x0[c["system"]]) / c["sp"]
    d["left_edge"] = LEFT_EDGE_LO_SP <= d["xs"] <= LEFT_EDGE_HI_SP
    return d
