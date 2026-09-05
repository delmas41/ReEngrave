"""Print every chained stroke's gate values for the pipeline cells whose YOLO
arcs get refused — names the failing gate with its number, cell by cell.
Usage: probe_gate_values.py <pdf> <page_index> <dpi> <cell_idx> [...]"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.measure_extractor import extract_measures  # noqa: E402
from tools.omr.staff_line_removal import remove_staff_lines  # noqa: E402
from tools.omr import arc_detection as ad  # noqa: E402


def main():
    pdf, page_index, dpi = Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    idxs = [int(x) for x in sys.argv[4:]]
    page = render_page(pdf, page_index, dpi=dpi)
    pws = detect_staves(page)
    cells = extract_measures(pws)
    remove_staff_lines(cells)
    for idx in idxs:
        cell = cells[idx]
        sp = ad._staff_line_spacing(cell)
        ys = cell.staff_line_ys_canonical or []
        print(f"== cell {idx}: sp={sp:.1f} staff_ys={ys} "
              f"H={cell.image.shape[0]} W={cell.image.shape[1]}")
        src = cell.image_no_staff if cell.image_no_staff is not None else cell.image
        ink = ad._binary_ink(src)
        thin = ad._thin_run_mask(ink, max(2, int(round(ad.ARC_THIN_RUN_MAX_SPACES * sp))))
        usable, cut = ad._extract_strokes(thin, sp, ad.ARC_EDGE_MARGIN_PX)
        print(f"   cut(top/bottom-touching): {len(cut)}")
        for s in ad._chain_strokes(usable, sp):
            have = ~np.isnan(s.mid)
            if s.width < 0.8 * sp or have.sum() < 4:
                continue
            xs = np.flatnonzero(have).astype(float)
            ms = s.mid[have]
            A = np.vstack([xs ** 2, xs, np.ones_like(xs)]).T
            coef, *_ = np.linalg.lstsq(A, ms, rcond=None)
            resid = float(np.sqrt(np.mean((A @ coef - ms) ** 2)))
            chord = np.interp(xs, [xs[0], xs[-1]], [ms[0], ms[-1]])
            dev = ms - chord
            rise = float(np.max(np.abs(dev)))
            curve = float(abs(coef[0]) * s.width ** 2 / 8.0)
            pos = float(np.sum(np.clip(dev, 0, None)))
            neg = float(np.sum(np.clip(-dev, 0, None)))
            side = max(pos, neg) / max(1e-6, pos + neg)
            below = (float(np.mean(ms)) - max(ys)) / sp if len(ys) >= 2 else 0.0
            emitted = ad._gate_stroke(s, sp) is not None and below <= ad.ARC_MAX_BELOW_STAFF_SPACES
            print(f"   x0={s.x0:5d} w={s.width/sp:5.2f}sp cov={have.sum()/s.width:.2f} "
                  f"resid={resid/sp:.3f} rise={rise/sp:.3f} curve={curve/sp:.3f} "
                  f"side={side:.2f} below={below:+.2f} -> {'EMIT' if emitted else 'refused'}")


if __name__ == "__main__":
    main()
