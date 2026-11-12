"""ROADMAP 2.304 STEP 0 probe (read only; changes no value). `gather_probe.py` (what the OCR said per candidate, and what the lexicon did with it), plus, per text
candidate, how much INK OF AN EARLIER OWNER lies inside the crop the text reader is handed (`direction_text.crop_for`'s window).

    python3 benchmarks/text-reader-owned-ink-2026-11/owned_probe.py PDF --pages ... [every `tools.omr.staged` argument]   (env PROBE_OUT=FILE.json)

Owners looked at (each the claimer's own geometry, not a new finder): `barline` = the pixels `page_strokes.carve_columns` carves from the page raster along
`barline_columns.fit_columns` (the page stroke map's own barline rule); `staff_line` = the five measured lines of every staff; `det:<category>` = the detector's
boxes (the reader already whites those OUTSIDE the candidate's own box, never inside it: `crop_for`), counted separately inside the box (`own`) and in the pad.
A pixel counts as owned ink only where the render is ink (gray < 180, what the OCR sees). `through_line` = does `direction_text.through_line_mask` (2.254 r3, the
existing geometric retry) already see a line coming into the box.
"""
import json
import os
import runpy
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
import tools.omr.direction_text as DT  # noqa: E402

DT.DIRECTION_CROP_TIMEOUT_S = 120.0
LOG = []
_cur = {"readings": []}
_orig_lookup = DT.lexicon_lookup
_cache = {}


def _lookup(text, *a, **k):
    hit = _orig_lookup(text, *a, **k)
    f = sys._getframe(1)
    i = f.f_locals.get("i", f.f_locals.get("index"))
    _cur["readings"].append(dict(candidate=i if isinstance(i, int) else None, text=text, accepted=None if hit is None else hit.text,
                                 where=f.f_code.co_name))
    return hit


def _page_masks(pws):
    """barline-owned and staff-line-owned pixels of the page (bool, full page), cached per page."""
    key = id(pws.page)
    if key in _cache:
        return _cache[key]
    import cv2
    from tools.omr.staged import barline_columns as BC
    from tools.omr.staged import page_strokes as PS
    binary = pws.page.binary
    cols = BC.fit_columns(pws)
    sp = float(np.median([s.line_spacing_px for s in pws.staves])) if pws.staves else 1.0
    canvas = binary.copy()
    PS.carve_columns(canvas, cols, sp)
    bar = (binary == 0) & (canvas != 0)
    bar = cv2.dilate(bar.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    sl = np.zeros(binary.shape, bool)
    for s in pws.staves:
        th = list(s.line_thickness_px or [])
        for k, y in enumerate(s.line_ys):
            t = th[k] if k < len(th) and th[k] else 3.0
            h = int(np.ceil(t / 2.0)) + 1
            sl[max(0, int(y) - h):int(y) + h + 1, max(0, int(s.x_start)):int(s.x_end) + 1] = True
    _cache.clear()
    _cache[key] = (bar, sl)
    return bar, sl


def _owned(pws, page_dict, cand):
    page = pws.page
    st = next((s for s in pws.staves if s.staff_index == cand.staff_index), None)
    sp = max(1.0, float(st.line_spacing_px)) if st else 20.0
    H, W = page.rgb.shape[:2]
    x0, y0, x1, y1 = cand.bbox_page
    px, py = int(round(DT.CROP_PAD_X_SPACES * sp)), int(round(DT.CROP_PAD_Y_SPACES * sp))
    cy0, cy1, cx0, cx1 = max(0, y0 - py), min(H, y1 + py), max(0, x0 - px), min(W, x1 + px)
    gray = page.rgb[cy0:cy1, cx0:cx1]
    import cv2
    if gray.ndim == 3:
        gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)
    ink = gray < 180
    own = np.zeros(ink.shape, bool)
    own[max(0, y0 - cy0):max(0, y1 - cy0), max(0, x0 - cx0):max(0, x1 - cx0)] = True
    bar, sl = _page_masks(pws)
    out = {}
    out["barline_own"] = int((ink & bar[cy0:cy1, cx0:cx1] & own).sum())
    out["barline_pad"] = int((ink & bar[cy0:cy1, cx0:cx1] & ~own).sum())
    out["staff_line_own"] = int((ink & sl[cy0:cy1, cx0:cx1] & own).sum())
    out["staff_line_pad"] = int((ink & sl[cy0:cy1, cx0:cx1] & ~own).sum())
    for system in page_dict.get("systems", []):
        for staff in system.get("staves", []):
            for m in staff.get("measures", []):
                for det in m.get("detections", []):
                    b = det.get("bbox_page")
                    if not b or len(b) != 4:
                        continue
                    dx0, dy0, dx1, dy1 = int(b[0]), int(b[1]), int(b[0] + b[2]), int(b[1] + b[3])
                    ax0, ay0, ax1, ay1 = max(dx0, cx0), max(dy0, cy0), min(dx1, cx1), min(dy1, cy1)
                    if ax1 <= ax0 or ay1 <= ay0:
                        continue
                    sub = ink[ay0 - cy0:ay1 - cy0, ax0 - cx0:ax1 - cx0]
                    o = own[ay0 - cy0:ay1 - cy0, ax0 - cx0:ax1 - cx0]
                    k = "det:" + str(det.get("category"))
                    out[k + "_own"] = out.get(k + "_own", 0) + int((sub & o).sum())
                    out[k + "_pad"] = out.get(k + "_pad", 0) + int((sub & ~o).sum())
    region = (cx0, cy0, cx1, cy1)
    try:
        tl = bool(DT.through_line_mask(page.binary, cand.bbox_page, sp, region).any())
    except Exception:
        tl = None
    return dict(sp=sp, own_px=int(own.sum()), ink_px=int(ink.sum()), owned={k: v for k, v in out.items() if v}, through_line=tl)


_orig_read = DT.read_directions


def _read(*a, **k):
    _cur["readings"] = []
    found, info = _orig_read(*a, **k)
    pws = a[0] if a else k.get("pws")
    page_dict = a[1] if len(a) > 1 else k.get("page_dict")
    cands = []
    for i, c in enumerate(info.get("candidates") or ()):
        try:
            ow = _owned(pws, page_dict, c)
        except Exception as exc:  # noqa: BLE001
            ow = dict(error=repr(exc))
        cands.append(dict(i=i, staff=int(c.staff_index), measure=int(c.measure_index), box=[float(v) for v in c.bbox_page], **ow))
    LOG.append(dict(page=int(getattr(pws.page, "page_index", -1)), candidates=cands, readings=list(_cur["readings"]),
                    found=[dict(text=d.text, staff=int(d.staff_index), measure=int(d.measure_index), reader=d.reader, box=None) for d in found],
                    rejected=list(info.get("rejected") or ())))
    return found, info


DT.lexicon_lookup = _lookup
DT.read_directions = _read
try:
    sys.argv = ["tools.omr.staged"] + sys.argv[1:]
    runpy.run_module("tools.omr.staged", run_name="__main__")
finally:
    out = os.environ.get("PROBE_OUT")
    if out:
        with open(out, "w") as fh:
            json.dump(LOG, fh)
