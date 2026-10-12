#!/usr/bin/env python3
"""l283_cells: cut a page's measure cells the way the staged gather does (`pipeline.prepare_pages`: staff-detect, cut,
erase staff lines) and run the gather's own CV stem reader on each (`line_detection.detect_lines`, the exact call
`gather.gather_cv_lines` makes), then cache the erased rasters, stems and beams, so a flag-at-the-tip reader can be
iterated on the REAL cell raster in seconds instead of a ten-minute re-gather. ROADMAP 2.83 probe, no product code.

    python3 l283_cells.py --pdf PDF --page 0 --out cells_p0.pkl

Cached per cell: key (system_index, staff_index, measure_index), `bbox_page_px`, `upscale_factor`, the staff lines in
canonical px, the erased raster (uint8 0/255), the CV stems and beams as (x, y, w, h) in canonical px.

The notehead gate (`OMR_STEM_NOTEHEAD_GATE`) is OFF by default, so `detect_lines` is called with no heads, as
`gather_cv_lines` effectively does; a cell whose stems differ from a real gather's is caught by `l283_truth_score.py`'s
stem control (it matches the cached stems to Sean's stem boxes).
"""
import argparse
import gzip
import pickle
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    from tools.omr.staged.pipeline import prepare_pages
    from tools.omr.line_detection import detect_lines
    (pws, cells), = prepare_pages(a.pdf, [a.page], dpi=600)
    out = {}
    for c in cells:
        try:
            found = detect_lines(c, candidates_out=None, noteheads=None, rescue_tall_beams=True)
        except Exception as exc:  # noqa: BLE001
            print("detect_lines failed", c.system_index, c.staff_index, c.measure_index, type(exc).__name__)
            continue
        img = getattr(c, "image_no_staff", None)
        if img is None:
            continue

        def boxes(rows):
            return [(float(d.x_canonical), float(d.y_canonical), float(d.width_canonical),
                     float(d.height_canonical)) for d in (rows or [])]
        out[(c.system_index, c.staff_index, c.measure_index)] = {
            "bbox_page_px": tuple(c.bbox_page_px), "scale": float(c.upscale_factor),
            "lines": list(c.staff_line_ys_canonical), "img": (np.asarray(img) == 0),
            "stems": boxes(found.get("stems")), "beams": boxes(found.get("beams")),
            "staff_index": c.staff_index,
        }
    with gzip.open(a.out, 'wb', compresslevel=3) as fh:
        pickle.dump(out, fh, protocol=4)
    print("cells", len(out), "stems", sum(len(v["stems"]) for v in out.values()),
          "beams", sum(len(v["beams"]) for v in out.values()), "->", a.out)


if __name__ == "__main__":
    main()
