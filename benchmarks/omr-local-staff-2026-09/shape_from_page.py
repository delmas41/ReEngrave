#!/usr/bin/env python3
"""lane-ledger-template-fix round 3 (2026-10-04): the head SHAPE (width,
height, tilt) measured from many CLEAN, ISOLATED, IN-STAFF heads on the page,
plus the same blob extraction the review sheet's control tiles use.

Why a new measurement: `measure_head_tilt.measure_head`'s per-head tilt had an
IQR of -2..43 degrees. Cause found here (see `diagnose_old_fit`): it fitted a
cv2 ellipse to ink in a window only ~1.65 sp tall with the stem MASKED BY
WHOLE COLUMNS (which eats the head's own edge, because the stem column's run
includes the head) and the protect-columns rule leaving staff-line stubs
attached to the oval's top and bottom for heads in a space; and at ~16 px per
space a 1.3 : 1 oval is only ~20 x 16 pixels, where fitEllipse's angle is
quantisation noise for a near-round blob. The fit here: staff-line rows are
masked only OUTSIDE a nominal oval, stems and line remnants are removed by a
morphological OPENING (a disc wider than a stem or a line, narrower than a
head), the head's blob is the component through the box centre, holes are
filled for the outer outline, and the angle comes from SECOND MOMENTS (an
area statistic, not a contour fit), reported only where the blob is
eccentric enough for an angle to exist.

Nothing here scores a reader. Run:
    python3 benchmarks/omr-local-staff-2026-09/shape_from_page.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import cv2  # noqa: E402

import truth_set_2_44c as ts  # noqa: E402
import score_truth_set_rungs as score  # noqa: E402
import score_head_template as sht  # noqa: E402
import measure_head_tilt as mht  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.annotate import head_template as ht  # noqa: E402

OPEN_DIAMETER_SPACES = 0.42   # wider than a stem / staff line, narrower than a head
WIN_HALF_SPACES = 1.25
NOMINAL_HALF_W_SPACES = 0.68  # nominal oval used ONLY to decide where line rows may be cut
NOMINAL_HALF_H_SPACES = 0.55
ISOLATION_GAP_SPACES = 1.0
ISOLATION_CLASSES = ("notehead", "accidental", "rest")
# quality gate (area / shape sanity of a head blob)
AREA_SP2 = (0.7, 1.45)        # ellipse 1.3 x 1.0 sp is 1.02 sp^2
LONG_AXIS_SP = (1.0, 1.8)
SOLIDITY_MIN = 0.90
LEMON_SOLIDITY_MIN = 0.88     # the shape gate for a lemon: no oval test, same area/size/solidity
ELLIPSE_IOU_MIN = 0.85        # blob must BE an oval: IoU with its own moments-ellipse
ECC_MIN_FOR_ANGLE = 1.12     # below this a blob is round: its angle is undefined


def moments_shape(mask: np.ndarray) -> Optional[Dict[str, float]]:
    """(long axis, short axis, angle) of a binary blob from second central
    moments. `tilt_up_right_deg` is the major axis's angle from horizontal,
    positive = RIGHT end higher (image y is down)."""
    m = cv2.moments(mask.astype(np.uint8), binaryImage=True)
    if m["m00"] < 5:
        return None
    mu20, mu02, mu11 = m["mu20"] / m["m00"], m["mu02"] / m["m00"], m["mu11"] / m["m00"]
    tr, det = mu20 + mu02, mu20 * mu02 - mu11 ** 2
    disc = max(0.0, tr * tr / 4.0 - det)
    l1, l2 = tr / 2.0 + disc ** 0.5, max(1e-9, tr / 2.0 - disc ** 0.5)
    theta_img = 0.5 * np.arctan2(2 * mu11, mu20 - mu02)   # clockwise from +x, y down
    return dict(long_px=4.0 * l1 ** 0.5, short_px=4.0 * l2 ** 0.5,
                ecc=(l1 / l2) ** 0.5, tilt_up_right_deg=float(-np.degrees(theta_img)),
                cx=m["m10"] / m["m00"], cy=m["m01"] / m["m00"], area=m["m00"])


def head_blob(gray: np.ndarray, box, lines: List[float], spacing: float,
              thickness_px: float) -> Dict[str, Any]:
    """The head's own blob. Returns dict(ok, reason, blob, outer, hole, org)
    in WINDOW coordinates with `org=(x0, y0)` the window's page origin."""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    hw = int(round(WIN_HALF_SPACES * spacing))
    wx0, wy0 = int(round(cx)) - hw, int(round(cy)) - hw
    wx1, wy1 = wx0 + 2 * hw + 1, wy0 + 2 * hw + 1
    H, W = gray.shape
    if wx0 < 0 or wy0 < 0 or wx1 > W or wy1 > H:
        return dict(ok=False, reason="window_off_page")
    win = gray[wy0:wy1, wx0:wx1]
    ink = win <= ht._otsu_threshold(win)
    cxl, cyl = cx - wx0, cy - wy0
    yy, xx = np.mgrid[0:win.shape[0], 0:win.shape[1]]
    nominal = (((xx - cxl) / (NOMINAL_HALF_W_SPACES * spacing)) ** 2
               + ((yy - cyl) / (NOMINAL_HALF_H_SPACES * spacing)) ** 2) <= 1.0
    half = int(round(thickness_px / 2.0)) + 1
    for ly in lines:
        r0, r1 = int(round(ly - wy0)) - half, int(round(ly - wy0)) + half + 1
        r0, r1 = max(0, r0), min(win.shape[0], r1)
        if r1 > r0:
            ink[r0:r1, :] &= nominal[r0:r1, :]
    d = max(3, int(round(OPEN_DIAMETER_SPACES * spacing)) | 1)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d, d))
    op = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_OPEN, k)
    num, labels = cv2.connectedComponents(op)
    if num <= 1:
        return dict(ok=False, reason="no_blob_after_opening")
    lab = int(labels[int(round(cyl)), int(round(cxl))])
    if lab == 0:
        ov = [(int(((labels == i) & nominal).sum()), i) for i in range(1, num)]
        n_ov, lab = max(ov)
        if n_ov == 0:
            return dict(ok=False, reason="no_blob_at_box_centre")
    blob = labels == lab
    border = np.zeros_like(blob)
    border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
    if (blob & border).any():
        return dict(ok=False, reason="blob_touches_window_edge", blob=blob)
    cnts, _ = cv2.findContours(blob.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    outer = np.zeros(blob.shape, np.uint8)
    cv2.drawContours(outer, cnts, -1, 1, -1)
    outer = outer.astype(bool)
    holes = outer & ~blob
    nh, hl = cv2.connectedComponents(holes.astype(np.uint8))
    hole = None
    if nh > 1:
        sizes = [(int((hl == i).sum()), i) for i in range(1, nh)]
        hole = hl == max(sizes)[1]
    hull = cv2.convexHull(max(cnts, key=cv2.contourArea))
    solidity = float(outer.sum() / max(1.0, cv2.contourArea(hull)))
    return dict(ok=True, reason="", blob=blob, outer=outer, hole=hole,
                org=(wx0, wy0), solidity=solidity)


def measure_clean_head(gray, box, lines, spacing, thickness_px) -> Dict[str, Any]:
    """Blob + gate + moments in staff spaces. `pass` True only when the blob
    is a plausible head; `reason` names the first failure."""
    b = head_blob(gray, box, lines, spacing, thickness_px)
    out = dict(ok=False, reason=b.get("reason", ""), **{})
    if not b["ok"]:
        return out
    ms = moments_shape(b["outer"])
    if ms is None:
        return dict(ok=False, reason="empty")
    area_sp2 = ms["area"] / spacing ** 2
    long_sp, short_sp = ms["long_px"] / spacing, ms["short_px"] / spacing
    reason = ""
    ell = np.zeros(b["outer"].shape, np.uint8)
    cv2.ellipse(ell, (int(round(ms["cx"])), int(round(ms["cy"]))),
                (max(1, int(round(ms["long_px"] / 2))), max(1, int(round(ms["short_px"] / 2)))),
                -ms["tilt_up_right_deg"], 0, 360, 1, -1)
    ell = ell.astype(bool)
    ell_iou = float((ell & b["outer"]).sum() / max(1, (ell | b["outer"]).sum()))
    if ell_iou < ELLIPSE_IOU_MIN:
        reason = f"not_oval iou {ell_iou:.2f} < {ELLIPSE_IOU_MIN}"
    elif not (AREA_SP2[0] <= area_sp2 <= AREA_SP2[1]):
        reason = f"area {area_sp2:.2f} sp2 outside {AREA_SP2}"
    elif not (LONG_AXIS_SP[0] <= long_sp <= LONG_AXIS_SP[1]):
        reason = f"long axis {long_sp:.2f} sp outside {LONG_AXIS_SP}"
    elif b["solidity"] < SOLIDITY_MIN:
        reason = f"solidity {b['solidity']:.2f} < {SOLIDITY_MIN}"
    ok_lemon = (AREA_SP2[0] <= area_sp2 <= AREA_SP2[1]
                and LONG_AXIS_SP[0] <= long_sp <= LONG_AXIS_SP[1]
                and b["solidity"] >= LEMON_SOLIDITY_MIN)
    res = dict(ok=(reason == ""), ok_lemon=bool(ok_lemon), reason=reason, ell_iou=ell_iou, long_sp=long_sp, short_sp=short_sp,
               ecc=ms["ecc"], tilt=ms["tilt_up_right_deg"],
               angle_defined=ms["ecc"] >= ECC_MIN_FOR_ANGLE, area_sp2=area_sp2,
               blob=b)
    if b.get("hole") is not None:
        hs = moments_shape(b["hole"])
        if hs:
            res["slit"] = dict(long_sp=hs["long_px"] / spacing, short_sp=hs["short_px"] / spacing,
                               ecc=hs["ecc"], tilt=hs["tilt_up_right_deg"],
                               area_sp2=hs["area"] / spacing ** 2)
    return res


# --------------------------------------------------------------------------
# population
# --------------------------------------------------------------------------

def _kind(cls: str) -> Optional[str]:
    if "Black" in cls:
        return "filled"
    if "Half" in cls or "Whole" in cls:
        return "hollow"
    return None


def in_staff_heads(doc_id: str, loaded, pages) -> List[Dict[str, Any]]:
    """Every in-staff notehead (position 0..8 on OUR staff-position read),
    with its local lines, isolation flag and measured blob. `position` is
    only used to say on-line vs in-space and to keep the head in the staff;
    the SHAPE never depends on it."""
    rec = loaded["rec"]
    boxes_by_page = sht._page_glyph_boxes(rec)
    out = []
    for o in rec.observations:
        if o["quantity"] != Q.NOTEHEAD_STAFF_POSITION:
            continue
        pos = int(round(float(o["value"])))
        if not 0 <= pos <= 8:
            continue
        sub = o["subject"]
        page = int(sub.split("/")[1])
        box_obs = rec.obs(Q.GLYPH_BOX, sub)
        if not box_obs:
            continue
        box = (box_obs[-1].get("detail") or {}).get("bbox_page_px")
        if not box:
            continue
        staff_key = "staff/" + "/".join(sub.split("/")[1:4])
        lr = rec.obs(Q.STAFF_LINES, staff_key)
        if not lr:
            continue
        pb = boxes_by_page.get(page, [])
        entry = {s: (c, b) for (s, c, b) in pb}
        cls = entry.get(sub, (None, None))[0]
        kind = _kind(cls or "")
        if kind is None:
            continue
        out.append(dict(subject=sub, page=page, box=tuple(float(v) for v in box), pos=pos,
                        kind=kind, cls=cls, staff_key=staff_key,
                        global_lines=[float(y) for y in lr[-1]["value"]]))
    return out


# ---- round 5: "is this box really a notehead?" (Sean: two Brahms controls were
# "not noteheads, part of another symbol"). The CONVENTION used, stated once:
#   (1) the detector's own confidence for the notehead box is >= 0.5;
#   (2) no rest / flag / clef / dynamic / accidental / fermata / ornament / ottava /
#       time / key box overlaps more than 20% of the head's box (a notehead box
#       sitting inside another symbol is a piece of that symbol);
#   (3) a FILLED head carries a STEM on the print: a vertical ink run 2.0-6.5 sp
#       long touching the head's left or right edge and reaching >= 1 sp past the
#       head (every filled head has a stem, chord heads included; a barline is
#       longer than 6.5 sp, a tie or beam is horizontal). Hollow/whole class heads
#       are not asked for one (a whole note has none).
# None of these keys on a subject id.
MIN_DETECTOR_SCORE = 0.5
# NOT "flag": a flag is attached to the stem OF a real head, and the detector's
# flag box overlaps the head's box on every flagged stem-down note (the first
# version of this rule removed 15 real Brahms heads that way -- contact sheet).
NON_HEAD_CLASS_WORDS = ("rest", "clef", "dynamic", "accidental", "fermata",
                        "ornament", "ottava", "time", "key")
OVERLAP_FRACTION_MAX = 0.20
STEM_RUN_SPACES = (2.0, 6.5)
STEM_REACH_PAST_HEAD_SPACES = 1.0


def symbol_gate(gray, h, page_boxes, rec) -> Dict[str, Any]:
    x0, y0, x1, y1 = h["box"]
    sp = h["spacing"]
    reasons = []
    obs = rec.obs(Q.GLYPH_BOX, h["subject"])
    score_ = obs[-1].get("score") if obs else None
    if score_ is None or score_ < MIN_DETECTOR_SCORE:
        reasons.append(f"detector score {score_}")
    area = max(1.0, (x1 - x0) * (y1 - y0))
    for (sub, cls, b) in page_boxes:
        if sub == h["subject"] or not any(w in cls.lower() for w in NON_HEAD_CLASS_WORDS):
            continue
        ox, oy = min(x1, b[2]) - max(x0, b[0]), min(y1, b[3]) - max(y0, b[1])
        if ox > 0 and oy > 0 and ox * oy / area > OVERLAP_FRACTION_MAX:
            reasons.append(f"overlaps {cls}")
            break
    stem = None
    if "Black" in (h.get("cls") or ""):
        H, W = gray.shape
        ry0, ry1 = max(0, int(y0 - 7 * sp)), min(H, int(y1 + 7 * sp))
        rx0, rx1 = max(0, int(x0 - 0.5 * sp)), min(W, int(x1 + 0.5 * sp))
        win = gray[ry0:ry1, rx0:rx1]
        ink = win <= ht._otsu_threshold(win)
        hy0, hy1 = int(y0) - ry0, int(y1) - ry0
        bands = [(int(x0 - 0.2 * sp) - rx0, int(x0 + 0.35 * sp) - rx0),
                 (int(x1 - 0.35 * sp) - rx0, int(x1 + 0.2 * sp) - rx0)]
        best = 0.0
        for c0, c1 in bands:
            for c in range(max(0, c0), min(ink.shape[1], c1 + 1)):
                col = ink[:, c]
                # the run that contains the head's own rows
                r = (hy0 + hy1) // 2
                if not col[min(max(r, 0), len(col) - 1)]:
                    continue
                a = r
                while a - 1 >= 0 and col[a - 1]:
                    a -= 1
                b_ = r
                while b_ + 1 < len(col) and col[b_ + 1]:
                    b_ += 1
                ext_up, ext_dn = (hy0 - a) / sp, (b_ - hy1) / sp
                run = (b_ - a + 1) / sp
                if STEM_RUN_SPACES[0] <= run <= STEM_RUN_SPACES[1] and max(ext_up, ext_dn) >= STEM_REACH_PAST_HEAD_SPACES:
                    best = max(best, run)
        stem = best
        if best == 0.0:
            reasons.append("no stem on the print")
    return dict(ok=not reasons, reasons=reasons, detector_score=score_, stem_run_sp=stem)


def annotate_heads(doc_id, loaded, pages, heads) -> None:
    """Fill `lines`, `spacing`, `isolated`, `meas` on each head dict."""
    rec = loaded["rec"]
    boxes_by_page = sht._page_glyph_boxes(rec)
    for h in heads:
        gray = pages.get(h["page"])
        h["lines"] = score.frame_lines_for_head(gray, h["global_lines"], h["box"])
        h["spacing"] = (max(h["lines"]) - min(h["lines"])) / 4.0
        pb = boxes_by_page.get(h["page"], [])
        gap = ISOLATION_GAP_SPACES * h["spacing"]
        x0, y0, x1, y1 = h["box"]
        iso = True
        for (s, c, b) in pb:
            if s == h["subject"] or not any(k in c.lower() for k in ISOLATION_CLASSES):
                continue
            if (b[0] < x1 + gap and b[2] > x0 - gap and b[1] < y1 + gap and b[3] > y0 - gap):
                iso = False
                break
        h["isolated_boxes"] = iso
        h["symbol"] = symbol_gate(gray, h, pb, rec)
        h["isolated"] = iso and h["symbol"]["ok"]
        thick = mht._page_line_thickness_px(doc_id, h["page"], gray, rec, pb)
        h["thickness"] = thick
        h["meas"] = measure_clean_head(gray, h["box"], h["lines"], h["spacing"], thick)


def summarize(doc_id: str, heads) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for kind in ("filled", "hollow"):
        ks = [h for h in heads if h["kind"] == kind]
        iso = [h for h in ks if h["isolated"]]
        ok = [h for h in iso if h["meas"]["ok"]]
        ang = [h for h in ok if h["meas"]["angle_defined"]]
        def q(v):
            v = np.array(v)
            return [round(float(x), 3) for x in np.percentile(v, [25, 50, 75])] if v.size else None
        e = dict(n_in_staff=len(ks), n_isolated=len(iso), n_pass=len(ok), n_angle_defined=len(ang))
        fails: Dict[str, int] = {}
        for h in iso:
            if not h["meas"]["ok"]:
                r = h["meas"]["reason"].split(" ")[0]
                fails[r] = fails.get(r, 0) + 1
        e["fail_reasons_among_isolated"] = fails
        if ok:
            e["long_sp_q25_50_75"] = q([h["meas"]["long_sp"] for h in ok])
            e["short_sp_q25_50_75"] = q([h["meas"]["short_sp"] for h in ok])
        if ang:
            e["tilt_deg_q25_50_75"] = q([h["meas"]["tilt"] for h in ang])
        for par, nm in ((0, "on_line"), (1, "in_space")):
            sub = [h for h in ok if h["pos"] % 2 == par]
            sa = [h for h in sub if h["meas"]["angle_defined"]]
            e[nm] = dict(n=len(sub),
                         long_sp=q([h["meas"]["long_sp"] for h in sub]),
                         short_sp=q([h["meas"]["short_sp"] for h in sub]),
                         tilt_deg=q([h["meas"]["tilt"] for h in sa]))
        sl = [h["meas"]["slit"] for h in ok if "slit" in h["meas"] and h["meas"]["slit"]["ecc"] >= ECC_MIN_FOR_ANGLE]
        if sl:
            e["slit_tilt_q25_50_75"] = q([s["tilt"] for s in sl])
            e["slit_long_sp_q"] = q([s["long_sp"] for s in sl])
            e["slit_short_sp_q"] = q([s["short_sp"] for s in sl])
            e["n_slit"] = len(sl)
        out[kind] = e
    return out


def diagnose_old_fit(doc_id: str, loaded, pages, heads) -> Dict[str, Any]:
    """Why was the old per-head tilt noisy? Re-run the OLD `measure_head`
    on the same clean in-staff heads and split its angle spread by candidate
    causes. Also reports the old fit's long-vs-short axis and the new
    moments tilt on the SAME heads."""
    rows = []
    for h in heads:
        if h["kind"] != "filled" or not h["isolated"] or not h["meas"]["ok"]:
            continue
        gray = pages.get(h["page"])
        m = mht.measure_head(gray, h["box"], h["spacing"], h["lines"], h["thickness"])
        if m["outer"] is None:
            continue
        win = m["window_ink"]
        edge = bool(win[0, :].any() or win[-1, :].any() or win[:, 0].any() or win[:, -1].any())
        ys, xs = np.nonzero(win)
        ecc = None
        ax = m.get("outer_axes")
        if ax:
            ecc = ax[0] / max(1e-6, ax[1])
        rows.append(dict(old=m["outer"], new=h["meas"]["tilt"], new_defined=h["meas"]["angle_defined"],
                         in_space=h["pos"] % 2 == 1, edge=edge, ecc=ecc))
    def iqr(v):
        v = [x for x in v]
        if len(v) < 4:
            return None
        a = np.percentile(v, [25, 50, 75])
        return dict(n=len(v), q25=round(float(a[0]), 1), q50=round(float(a[1]), 1), q75=round(float(a[2]), 1))
    out = dict(n=len(rows), old_all=iqr([r["old"] for r in rows]),
               new_all_defined=iqr([r["new"] for r in rows if r["new_defined"]]),
               old_on_line=iqr([r["old"] for r in rows if not r["in_space"]]),
               old_in_space=iqr([r["old"] for r in rows if r["in_space"]]),
               old_window_ink_touches_edge=iqr([r["old"] for r in rows if r["edge"]]),
               old_window_clear=iqr([r["old"] for r in rows if not r["edge"]]),
               old_ecc_lt_1p15=iqr([r["old"] for r in rows if r["ecc"] is not None and r["ecc"] < 1.15]),
               old_ecc_ge_1p15=iqr([r["old"] for r in rows if r["ecc"] is not None and r["ecc"] >= 1.15]))
    return out


def main() -> int:
    import json
    result = {}
    for doc_id in ts.DOCS:
        print(f"=== {doc_id} ===")
        loaded = ts.load_doc(doc_id)
        pages = score.PageCache(loaded["cfg"])
        heads = in_staff_heads(doc_id, loaded, pages)
        annotate_heads(doc_id, loaded, pages, heads)
        s = summarize(doc_id, heads)
        d = diagnose_old_fit(doc_id, loaded, pages, heads)
        result[doc_id] = dict(summary=s, old_fit_diagnosis=d)
        print(json.dumps(result[doc_id], indent=1))
    out = REPO / "out" / "print" / "ledgers" / "shape_from_page.json"
    out.write_text(json.dumps(result, indent=1))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# --------------------------------------------------------------------------
# round 4: a mean head shape (for plates whose heads are not ovals)
# --------------------------------------------------------------------------

def mean_shape(heads, pages, kind="filled", on_line_only=True):
    """Average of the clean heads' OUTER blobs, each resampled to the canonical
    grid (30 px per space) and aligned on its own measured centroid (second
    moments) -- the tilt stays IN the shape. Returns (prob, n) with prob in 0..1
    on the `head_template` canonical grid, head centre at the grid centre."""
    use = [h for h in heads if h["kind"] == kind and h["isolated"] and h["meas"].get("ok_lemon")
           and (not on_line_only or h["pos"] % 2 == 0)]
    acc = np.zeros((ht.CANONICAL_H, ht.CANONICAL_W), np.float64)
    for h in use:
        b = h["meas"]["blob"]
        ms = moments_shape(b["outer"])
        s_ = ht.CANONICAL_PX_PER_SPACE / h["spacing"]
        M = np.array([[s_, 0, ht.CANONICAL_W / 2.0 - s_ * ms["cx"]],
                      [0, s_, ht.CANONICAL_H / 2.0 - s_ * ms["cy"]]], np.float64)
        w = cv2.warpAffine(b["outer"].astype(np.float32), M, (ht.CANONICAL_W, ht.CANONICAL_H),
                           flags=cv2.INTER_LINEAR)
        acc += w
    return (acc / max(1, len(use))), len(use)
