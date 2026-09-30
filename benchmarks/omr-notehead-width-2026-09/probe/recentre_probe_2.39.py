"""ROADMAP 2.39 item 4 -- MEASURE ONLY, DO NOT WIRE.

Sean's convention (2026-09-29) gave GATHER a STANDARD box around the
detector's own CENTRE. The roadmap ALSO asks to "re-centre on the head's
own ink" -- this script measures that population without wiring it in
(item 4 says explicitly: do not change `gather_notehead_positions` /
`Q.NOTEHEAD_STAFF_POSITION`, which stays on the detector centre because a
re-centre changes PITCH).

For every regular notehead on one page: the ink centroid inside the
STANDARD box (`geometry.standard_head_box`), read off the staff-line-
erased raster (`cell.image_no_staff`, 0 = ink) -- compared against the
detector's own centre. Reports how many heads have
|ink centre - detector centre| > 0.25 staff space VERTICALLY, and how
many of those would change the ROUNDED staff position (half-integer
steps from the staff's own top line).

Run: PYTHONPATH=. python3 benchmarks/omr-notehead-width-2026-09/probe/recentre_probe_2.39.py <pdf> <page> --weights <path> [--dpi 600]
"""
from __future__ import annotations

import argparse
import json
import sys

import numpy as np

from tools.omr.staged import gather as G
from tools.omr.staged import geometry as GEOM
from tools.omr.staged import pipeline as P
from tools.omr.staged import record as R
from tools.omr.staged.record import Log


def _ink_centroid(img, x0, x1, y0, y1):
    """Ink-weighted centroid `(cx, cy)` inside `[x0,x1)x[y0,y1)`, or `None`
    with nothing to weigh. `img` is 0 = ink (the same convention every
    other ink reader in `gather.py` uses)."""
    if img is None or getattr(img, "ndim", 0) != 2:
        return None
    H, W = img.shape
    ix0, ix1 = max(0, int(round(x0))), min(W, int(round(x1)))
    iy0, iy1 = max(0, int(round(y0))), min(H, int(round(y1)))
    if ix1 <= ix0 or iy1 <= iy0:
        return None
    region = (img[iy0:iy1, ix0:ix1] == 0)
    if region.sum() == 0:
        return None
    ys, xs = np.nonzero(region)
    return (float(xs.mean()) + ix0, float(ys.mean()) + iy0)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("page", type=int)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--out")
    args = ap.parse_args(argv)

    from tools.omr.yolo_detector import YoloDetector
    detector = YoloDetector(args.weights)

    prepared = P.prepare_pages(args.pdf, [args.page], dpi=args.dpi)
    (pws, cells), = prepared

    log = Log()
    local = G.gather_geometry(log, pws)
    detections = G.gather_detections(log, cells, local, detector=detector,
                                     conf_threshold=args.conf)
    log.freeze()

    cell_by_local = {}
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        cell_by_local[(key[0], key[1], c.measure_index)] = c

    staff_geom = {}
    for st in pws.staves:
        key = local.get(st.staff_index)
        if key is None:
            continue
        sp = G._spacing(st)
        if sp:
            staff_geom[key] = (list(st.line_ys), float(sp))

    rows = []
    n_total = 0
    n_over_quarter_space = 0
    n_would_change_rounded_position = 0

    for cell_key, dets in detections.items():
        sub = R.Subject.from_key(cell_key)
        cell = cell_by_local.get((sub.system, sub.staff, sub.cell))
        if cell is None or getattr(cell, "image_no_staff", None) is None:
            continue
        geo = staff_geom.get((sub.system, sub.staff))
        if geo is None:
            continue
        line_ys, spacing = geo
        top = min(line_ys)
        for gi, d in enumerate(dets):
            name = str(getattr(d, "smufl_name", ""))
            if not GEOM.is_regular_notehead(name):
                continue
            n_total += 1
            cx, cy = d.x_center, d.y_center
            bx0, bx1, by0, by1 = GEOM.standard_head_box(cx, cy, spacing)
            centroid = _ink_centroid(cell.image_no_staff, bx0, bx1, by0, by1)
            if centroid is None:
                continue
            icx, icy = centroid
            dy_spaces = (icy - cy) / spacing
            det_pos = (cy - top) / (spacing / 2.0)
            ink_pos = (icy - top) / (spacing / 2.0)
            det_rounded = round(det_pos * 2.0) / 2.0
            ink_rounded = round(ink_pos * 2.0) / 2.0
            over = abs(dy_spaces) > 0.25
            changes = det_rounded != ink_rounded
            if over:
                n_over_quarter_space += 1
            if over and changes:
                n_would_change_rounded_position += 1
            rows.append({
                "cell": cell_key, "glyph": gi, "class": name,
                "detector_centre": [round(cx, 2), round(cy, 2)],
                "ink_centroid": [round(icx, 2), round(icy, 2)],
                "dy_spaces": round(dy_spaces, 4),
                "over_quarter_space": over,
                "detector_rounded_position": det_rounded,
                "ink_rounded_position": ink_rounded,
                "would_change_rounded_position": bool(over and changes),
            })

    summary = {
        "pdf": args.pdf, "page": args.page,
        "n_regular_noteheads": n_total,
        "n_with_ink_centroid": len(rows),
        "n_over_0.25_space_vertically": n_over_quarter_space,
        "n_would_change_rounded_staff_position": n_would_change_rounded_position,
    }
    print(json.dumps(summary, indent=2))
    if args.out:
        with open(args.out, "w") as f:
            json.dump({"summary": summary, "rows": rows}, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
