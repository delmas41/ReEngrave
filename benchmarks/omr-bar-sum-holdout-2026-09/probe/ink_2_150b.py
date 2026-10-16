"""ROADMAP 2.150b -- page-raster helpers for the rest-ink-contact probe: a staff-erased 600 dpi ink mask of a page and the
measurement of any glyph box from the cached rows (out/2.150/{doc}-rows.json). STAGED measurement only; decides nothing."""
import json
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged import rest_ink  # noqa: E402

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/"
PDFS = {"brahms": LIB + "brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
        "litolff": LIB + "beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"}
_ROWS = {}


def rows(doc):
    if doc not in _ROWS:
        _ROWS[doc] = json.load(open(f"out/2.150/{doc}-rows.json"))
    return _ROWS[doc]


_PAGE = {}


def page_gray(doc, page):
    if (doc, page) not in _PAGE:
        _PAGE[(doc, page)] = np.asarray(Image.fromarray(render_page(PDFS[doc], page, dpi=600).rgb).convert("L"))
    return _PAGE[(doc, page)]


def local_mask(doc, g):
    """A crop of the page around glyph `g`'s staff (14 spaces either side of the box) with the staff lines erased by
    the PRODUCTION routine (`staff_line_removal.remove_staff_lines_from_cell`, run on a stand-in cell): returns
    (ink bool mask, dx, dy) with crop = page[dy:, dx:]."""
    import types
    from tools.omr.preprocessing import binarize
    from tools.omr.staff_line_removal import remove_staff_lines_from_cell
    d = rows(doc)
    page = int(g.split("/")[1])
    staff = "staff/" + "/".join(g.split("/")[1:4])
    sp = float(d["staff"][staff]["space"])
    lines = [float(v) for v in d["staff"][staff]["lines"]]
    x0, y0, x1, y1 = d["boxes"][g][3]
    gray = page_gray(doc, page)
    cx0, cx1 = max(0, int(x0 - 14 * sp)), min(gray.shape[1], int(x1 + 14 * sp))
    cy0, cy1 = max(0, int(lines[0] - 6 * sp)), min(gray.shape[0], int(lines[-1] + 6 * sp))
    crop = gray[cy0:cy1, cx0:cx1]
    cell = types.SimpleNamespace(image=crop, binary=binarize(crop), image_no_staff=None,
                                 staff_line_ys_canonical=[v - cy0 for v in lines])
    out = remove_staff_lines_from_cell(cell, in_place=False)
    return out == 0, cx0, cy0


def measure_glyph(doc, g):
    d = rows(doc)
    b = d["boxes"][g]
    page = int(g.split("/")[1])
    cell = "/".join(g.split("/")[:5])
    staff = "staff/" + "/".join(g.split("/")[1:4])
    space = float(d["staff"][staff]["space"])
    heads = []
    for k, v in d["boxes"].items():
        if k == g or "/".join(k.split("/")[:5]) != cell or not str(v[0]).startswith("notehead"):
            continue
        heads.append((k, v[0], *v[3]))
    ink, dx, dy = local_mask(doc, g)
    shift = lambda t: (t[0] - dx, t[1] - dy, t[2] - dx, t[3] - dy)  # noqa: E731
    heads = [(h[0], h[1], *shift(h[2:])) for h in heads]
    return rest_ink.measure(ink, shift(b[3]), heads, space)
