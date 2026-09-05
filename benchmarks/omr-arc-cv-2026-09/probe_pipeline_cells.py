"""Does the CV arc reader see anything in PIPELINE cells (pad 4, sp 100,
possibly low-res upscale), as opposed to the gauntlet's pad-5 crops?

Builds the page's cells exactly as transcribe does (render -> detect_staves ->
extract_measures -> remove_staff_lines), no model, then runs detect_arcs per
cell and reports: arcs found, and — with gates instrumented — how many
candidate strokes were refused by which gate. CPU-only, cheap.

Usage: probe_pipeline_cells.py <pdf> <page_index> [dpi]
"""
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.measure_extractor import extract_measures  # noqa: E402
from tools.omr.staff_line_removal import remove_staff_lines  # noqa: E402
from tools.omr import arc_detection as ad  # noqa: E402


def main():
    pdf = Path(sys.argv[1])
    page_index = int(sys.argv[2])
    dpi = int(sys.argv[3]) if len(sys.argv) > 3 else 600
    page = render_page(pdf, page_index, dpi=dpi)
    pws = detect_staves(page)
    cells = extract_measures(pws)
    remove_staff_lines(cells)
    print(f"{len(cells)} cells")
    n_arcs = 0
    gate_fail = Counter()
    stroke_stats = []
    for cell in cells:
        sp = ad._staff_line_spacing(cell)
        arcs = ad.detect_arcs(cell)
        n_arcs += len(arcs)
        # instrument: ungated stroke population
        src = cell.image_no_staff if cell.image_no_staff is not None else cell.image
        if src is None:
            continue
        ink = ad._binary_ink(src)
        thin = ad._thin_run_mask(ink, max(2, int(round(ad.ARC_THIN_RUN_MAX_SPACES * sp))))
        usable, cut = ad._extract_strokes(thin, sp, ad.ARC_EDGE_MARGIN_PX)
        gate_fail["cut_edge"] += len(cut)
        for s in ad._chain_strokes(usable, sp):
            if s.width < ad.ARC_MIN_WIDTH_SPACES * sp:
                gate_fail["width"] += 1
                continue
            have = ~np.isnan(s.mid)
            cand = ad._gate_stroke(s, sp)
            if cand is None:
                # name the failing gate crudely
                xs = np.flatnonzero(have).astype(float)
                ms = s.mid[have]
                if have.sum() < 4 or have.sum() / s.width < (
                        ad.ARC_MIN_COVERAGE_JOINED if s.joined else ad.ARC_MIN_COVERAGE):
                    gate_fail["coverage"] += 1
                    continue
                A = np.vstack([xs ** 2, xs, np.ones_like(xs)]).T
                coef, *_ = np.linalg.lstsq(A, ms, rcond=None)
                resid = float(np.sqrt(np.mean((A @ coef - ms) ** 2)))
                if resid > ad.ARC_MAX_FIT_RESID_SPACES * sp:
                    gate_fail["resid"] += 1
                    continue
                chord = np.interp(xs, [xs[0], xs[-1]], [ms[0], ms[-1]])
                dev = ms - chord
                rise = float(np.max(np.abs(dev)))
                curve = float(abs(coef[0]) * s.width ** 2 / 8.0)
                if max(rise, curve) < ad.ARC_MIN_RISE_SPACES * sp:
                    gate_fail["rise"] += 1
                    continue
                gate_fail["side"] += 1
            else:
                counts = s.cnt[have]
                stroke_stats.append((s.width / sp, float(np.median(counts)) / sp))
    print("arcs found:", n_arcs)
    print("gate refusals:", dict(gate_fail))
    if stroke_stats:
        w = sorted(x[0] for x in stroke_stats)
        t = sorted(x[1] for x in stroke_stats)
        print(f"passing strokes n={len(stroke_stats)} w_sp p50={w[len(w)//2]:.2f} t_med p50={t[len(t)//2]:.2f}")
    # thin-mask sanity: overall ink and thin fractions on one middling cell
    c = cells[len(cells) // 2]
    src = c.image_no_staff if c.image_no_staff is not None else c.image
    ink = ad._binary_ink(src)
    sp = ad._staff_line_spacing(c)
    thin = ad._thin_run_mask(ink, max(2, int(round(ad.ARC_THIN_RUN_MAX_SPACES * sp))))
    print(f"sample cell: sp={sp:.1f} ink_frac={ink.mean()/255:.4f} thin_frac_of_ink={(thin.sum()/max(1,(ink>0).sum())):.3f}")


if __name__ == "__main__":
    main()
