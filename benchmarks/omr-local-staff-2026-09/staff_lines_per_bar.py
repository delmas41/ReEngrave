"""(a) raw staff-wide lines vs ink, (b) the PER-BAR grid in-staff positions use vs ink
(lane-staff-lines-off-ink, 2026-10-06; coordinator request).

(b) = the cell's own stored grid: `measure_extractor._cell_line_offset`'s rigid integer shift
(`cell.line_grid_localized['offset_px']`, 0 when the cell is not localized) added to
`staff.line_ys`.  Samples are the clean columns of staff_lines_off_ink.sample_column, assigned to the
cell whose `bbox_page_px` x-range holds them.  (c) -- the far-head path -- reads `st.line_ys`
(staged/gather.py on lane-local-staff-lines: `staff_lines[...] = st.line_ys`, then `global_lines=lines`),
which IS (a); it never sees the cell shift.

    python3 benchmarks/omr-local-staff-2026-09/staff_lines_per_bar.py litolff --pages 16 --out x.json
"""
from __future__ import annotations

import argparse, json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
from frame import render_page_matching_gather  # noqa: E402
import staff_lines_off_ink as M  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("doc", choices=list(M.DOCS)); ap.add_argument("--pages", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    from tools.omr.staff_detector import detect_staves
    from tools.omr.measure_extractor import extract_measures
    pdf, dpi, rec = M.recorded_staves(a.doc)
    pages = sorted({p for p, _, _ in rec})
    if a.pages:
        want = {int(v) for v in a.pages.split(",")}; pages = [p for p in pages if p in want]
    res = []
    for p in pages:
        pi = render_page_matching_gather(pdf, p, dpi=dpi)
        pws = detect_staves(pi)
        cells = extract_measures(pws)
        gray = pi.rgb.mean(axis=2)
        by_staff = {}
        for c in cells:
            by_staff.setdefault(c.staff_index, []).append(c)
        for (pp, s, k), lines in sorted(rec.items()):
            if pp != p:
                continue
            st = next((t for t in pws.staves if [float(v) for v in t.line_ys] == lines), None)
            if st is None:
                continue
            sp = (lines[-1] - lines[0]) / 4.0
            samples = []
            for x in range(int(st.x_start) + 8, int(st.x_end) - 8, M.STEP):
                r = M.sample_column(pi.binary, gray, x, lines[0], lines[-1], lines, sp)
                if r is not None:
                    samples.append((x, (r[0] - np.array(lines)).tolist()))
            cs = []
            for c in by_staff.get(st.staff_index, []):
                x0, _, x1, _ = c.bbox_page_px
                prov = c.__dict__.get("line_grid_localized")
                shift = prov["offset_px"] if prov else 0
                inx = [(x, o) for x, o in samples if x0 <= x < x1]
                if not inx:
                    cs.append(dict(x0=x0, x1=x1, shift=shift, n=0)); continue
                xs = np.array([x for x, _ in inx], float)
                oa = np.array([o for _, o in inx])           # raw offsets (n,5)
                ob = oa - shift                               # offsets of the per-bar grid
                mean_b = ob.mean(axis=1)
                if len(xs) >= 3 and np.ptp(xs) > 3 * sp:
                    sl = np.polyfit(xs, mean_b, 1)[0]; tilt = float(sl * (x1 - x0))
                else:
                    tilt = 0.0
                cs.append(dict(x0=x0, x1=x1, shift=shift, n=len(xs),
                               a_med=float(np.median(oa)), a_max=float(np.abs(oa).max()),
                               b_med=float(np.median(ob)), b_max=float(np.abs(ob).max()),
                               b_tilt_px=tilt, a_tilt_px=None))
            res.append(dict(doc=a.doc, page=p, staff=f"{p}/{s}/{k}", sp=sp, cells=cs))
        print(a.doc, "page", p, "done", flush=True)
    Path(a.out).write_text(json.dumps(res))


if __name__ == "__main__":
    main()
