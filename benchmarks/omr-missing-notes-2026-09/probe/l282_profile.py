#!/usr/bin/env python3
"""l282_profile: the per-column thickness PROFILE of every `Q.BEAM_STROKE` stroke, read off the page
raster (the gather's own, `preprocessing.render_page` at 600 dpi), so statistics other than the median
can be priced on the whole movement without a re-gather. ROADMAP 2.82. A reading probe: it decides
nothing and changes no product code.

THE CONTROL (can fail): the profile's MEDIAN, in canonical px, must reproduce the record's own
`thickness_px` (`gather.beam_stroke_ink`, off the canonical cell raster) on the strokes the record
read. It is reported per record (`median |difference|`, and the share within 2 canonical px); a
frame, a threshold or a column-window error shows here. `--shift` reads the SAME profile with the box
moved a whole beam off its stroke and must fail that agreement.

Per stroke the profile gives, besides the median (`med`):
  * `win[W]`  -- the THICKEST SUSTAINED SPAN: the largest median thickness over any window of W staff
    spaces of consecutive inked columns (W = 1.0, 1.5, 2.0 spaces);
  * `run2`    -- the longest stretch (staff spaces) of consecutive columns whose run is >= 2.0 staff
    lines thick, `run2_5` the same at 2.5 lines;
all as RATIOS to the stroke's own recorded staff-line thickness (`line_px`, the reader's local line),
so the unit is the one `BEAM_THICKNESS_RATIO_MIN` is in.

    python3 l282_profile.py --ext ext.json --pdf brahms|litolff --out prof.json [--pages 0,1]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from l281_tiles import PDFS  # noqa: E402

THRESH = 180          # gather.BEAM_INK_THRESHOLD
WINDOWS = (1.0, 1.5, 2.0, 2.5, 3.0)


def runs(col):
    d = np.diff(np.concatenate([[0], col.astype(np.int8), [0]]))
    return list(zip(np.where(d == 1)[0].tolist(), np.where(d == -1)[0].tolist()))


def profile(gray, box, space_px, shift_y=0.0):
    """Per-column run thickness (page px) of the ink run most overlapping the box, as `beam_stroke_ink`."""
    ink = gray < THRESH
    H, W = ink.shape
    x0, y0, x1, y1 = box
    y0 += shift_y
    y1 += shift_y
    xi0, xi1 = max(0, int(round(x0))), min(W, int(round(x1)))
    pad = int(round(0.5 * space_px))
    ya, yb = max(0, int(round(y0)) - pad), min(H, int(round(y1)) + pad)
    xs, th = [], []
    if yb <= ya or xi1 - xi0 < 4:
        return None
    for cx in range(xi0, xi1):
        best, bov = None, 0.0
        for s, e in runs(ink[ya:yb, cx]):
            ov = min(e + ya, y1) - max(s + ya, y0)
            if ov > bov:
                best, bov = (s, e), ov
        if best is None:
            continue
        xs.append(cx)
        th.append(best[1] - best[0])
    if len(xs) < 0.5 * (xi1 - xi0):
        return None
    return np.array(xs), np.array(th, float), xi1 - xi0


def sustained(th, win_cols, q=50):
    """The largest `q`-th percentile of thickness over any `win_cols` consecutive profile entries (the
    profile may skip columns that held no ink; a window is `win_cols` entries). q=50 is the sliding
    median; q=20 is a PLATEAU: 80% of the window's columns are at least this thick."""
    n = len(th)
    if n == 0:
        return None
    if n <= win_cols:
        return float(np.percentile(th, q))
    from numpy.lib.stride_tricks import sliding_window_view
    w = sliding_window_view(th, win_cols)
    return float(np.percentile(w, q, axis=1).max())


def longest_run(th, xs, cut):
    """Longest stretch, in columns, of consecutive columns (xs contiguous) with th >= cut."""
    best = cur = 0
    prev = None
    for x, t in zip(xs, th):
        if t >= cut:
            cur = cur + 1 if (prev is not None and x == prev + 1 and cur > 0) else 1
        else:
            cur = 0
        prev = x
        best = max(best, cur)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ext", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pages", default=None)
    ap.add_argument("--shift", action="store_true", help="the control: read each stroke a beam's height off")
    a = ap.parse_args()
    ext = json.load(open(a.ext))
    pages = sorted({int(ck.split("/")[1]) for ck in ext["strokes"]})
    if a.pages:
        pages = [int(x) for x in a.pages.split(",")]
    from tools.omr.preprocessing import render_page
    out = {}
    diffs = []
    for p in pages:
        gray = None
        n_p = 0
        for ck, ss in ext["strokes"].items():
            pp = ck.split("/")
            if int(pp[1]) != p:
                continue
            calib = ext["calib"].get(ck)
            if not calib:
                continue
            x0, y0, up = calib[:3]
            space_px = 100.0 / up
            for sid, s in ss.items():
                ink = ext["ink"].get(sid)
                if not ink or not ink.get("line_px"):
                    continue
                if gray is None:
                    import cv2
                    rgb = render_page(PDFS[a.pdf], p, dpi=600).rgb
                    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY) if rgb.ndim == 3 else rgb
                bx, by, bw, bh = s["box"][:4]
                box = (x0 + bx / up, y0 + by / up, x0 + (bx + bw) / up, y0 + (by + bh) / up)
                shift = (bh / up + 1.2 * space_px) if a.shift else 0.0
                pr = profile(gray, box, space_px, shift_y=shift)
                if pr is None:
                    continue
                xs, th, ncols = pr
                line_page = ink["line_px"] / up
                med_c = float(np.median(th)) * up
                rec = {"med_ratio": round(float(np.median(th)) / line_page, 3),
                       "rec_ratio": ink["thickness_ratio"], "med_canon": round(med_c, 1),
                       "rec_canon": ink["thickness_px"], "line_page": round(line_page, 2),
                       "space_page": round(space_px, 2), "w_sp": round(ncols / space_px, 2),
                       "reader": s["reader"]}
                for W in WINDOWS:
                    wc = max(3, int(round(W * space_px)))
                    rec[f"win{W:g}"] = round(sustained(th, wc) / line_page, 3)
                    rec[f"pl{W:g}"] = round(sustained(th, wc, 20) / line_page, 3)
                rec["run2"] = round(longest_run(th, xs, 2.0 * line_page) / space_px, 2)
                rec["run2_5"] = round(longest_run(th, xs, 2.5 * line_page) / space_px, 2)
                out[sid] = rec
                diffs.append(abs(med_c - ink["thickness_px"]))
                n_p += 1
        print(f"page {p}: {n_p} strokes", flush=True)
    d = np.array(diffs)
    print(f"CONTROL median(profile) vs record thickness_px: n={len(d)} median |diff| {np.median(d):.2f} canonical px; "
          f"within 2 px: {(d <= 2).mean():.3f}; within 5 px: {(d <= 5).mean():.3f}" +
          ("   (SHIFTED: must be BAD)" if a.shift else ""))
    Path(a.out).write_text(json.dumps(out, separators=(",", ":")))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
