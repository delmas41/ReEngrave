"""Measure the Litolff rise population behind ARC_RELAXED_MIN_RISE_SPACES.

Round 8 diagnosed the publisher-transfer gap from a handful of refused cells
(rise 0.062-0.116 sp under the 0.12 gate). This probe reads the WHOLE page:
every chained stroke on Litolff Beethoven 5 p1 that passes every gate EXCEPT
the rise gate — the population the relaxed floor exists to admit — plus, as
the control, the strokes that pass outright.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.measure_extractor import extract_measures  # noqa: E402
from tools.omr.staff_line_removal import remove_staff_lines  # noqa: E402
from tools.omr import arc_detection as ad  # noqa: E402

PDF = Path("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/"
           "symphony-5-op67/beethoven--symphony-5-op67--"
           "henry-litolff-s-verlag-1870--imslp984073.pdf")


def main():
    page = render_page(PDF, 1, dpi=600)
    pws = detect_staves(page)
    cells = extract_measures(pws)
    remove_staff_lines(cells)
    passed, rise_only = [], []
    for cell in cells:
        sp = ad._staff_line_spacing(cell)
        if sp <= 1.0:
            continue
        src = cell.image_no_staff if cell.image_no_staff is not None else cell.image
        if src is None:
            continue
        ink = ad._binary_ink(src)
        thin = ad._thin_run_mask(
            ink, max(2, int(round(ad.ARC_THIN_RUN_MAX_SPACES * sp))))
        usable, _cut = ad._extract_strokes(thin, sp, ad.ARC_EDGE_MARGIN_PX)
        ys = cell.staff_line_ys_canonical or []
        bottom = max(ys) if len(ys) >= 2 else None
        for s in ad._chain_strokes(usable, sp):
            std = ad._gate_stroke(s, sp)
            relaxed = ad._gate_stroke(s, sp, ad.ARC_RELAXED_MIN_RISE_SPACES)
            for cand, bucket in ((std, passed),
                                 (relaxed if std is None else None, rise_only)):
                if cand is None:
                    continue
                if (bottom is not None and
                        cand["mid_mean"] - bottom > ad.ARC_MAX_BELOW_STAFF_SPACES * sp):
                    continue
                bucket.append(cand["rise"] / sp)
    for name, v in (("passed standard gate", passed),
                    ("admitted ONLY by the relaxed floor", rise_only)):
        a = np.array(v)
        if a.size:
            print(f"{name}: n={a.size} p5={np.percentile(a,5):.3f} "
                  f"p50={np.percentile(a,50):.3f} p95={np.percentile(a,95):.3f} "
                  f"min={a.min():.3f} max={a.max():.3f}")
        else:
            print(f"{name}: n=0")


if __name__ == "__main__":
    main()
