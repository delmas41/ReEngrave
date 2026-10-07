"""lane-farhead-per-bar-grid (2026-10-06): the per-bar grid the GATHER hands the far-head reader, rebuilt from a page
WITHOUT a gather (staff detection + measure cells only, no detector), for the benchmark scripts. Read-only.

`bar_grids(rec, page, pi)` -> (grid_of, staves, raw)
    grid_of[(system, staff, cell)] -> five page-pixel lines = `far_head_reader.cell_grid_page_lines(cell)`
        (the rows `gather_notehead_positions` takes its position from)
    staves   -> `far_head_owner` staff dicts (key, raw lines, x0, x1, grid=[(x0, x1, lines)...])
    raw[staff key] -> the recorded staff-wide lines
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
from tools.omr.annotate import far_head_reader as FH  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402


def bar_grids(rec, page, pi):
    from tools.omr.staff_detector import detect_staves
    from tools.omr.measure_extractor import extract_measures
    pws = detect_staves(pi)
    cells = extract_measures(pws)
    recorded = {}
    for o in rec.observations:
        if o["quantity"] == Q.STAFF_LINES and o["subject"].startswith(f"staff/{page}/"):
            recorded[o["subject"]] = [float(v) for v in o["value"]]
    by_staff = {}
    for c in cells:
        by_staff.setdefault(c.staff_index, []).append(c)
    grid_of, staves, raw, unmatched = {}, [], {}, []
    for key, lines in sorted(recorded.items()):
        st = next((t for t in pws.staves if [float(v) for v in t.line_ys] == lines), None)
        if st is None:
            unmatched.append(key)
            continue
        _, p, s, k = key.split("/")
        segs = []
        for c in by_staff.get(st.staff_index, []):
            gl = FH.cell_grid_page_lines(c)
            if gl is None:
                continue
            grid_of[(int(s), int(k), c.measure_index)] = gl
            segs.append((float(c.bbox_page_px[0]), float(c.bbox_page_px[2]), gl))
        staves.append(dict(key=key, lines=lines, x0=float(st.x_start), x1=float(st.x_end), grid=segs))
        raw[key] = lines
    return grid_of, staves, raw, unmatched, pws, cells


def head_cell(subject):
    """(system, staff, cell) of a glyph subject `glyph/page/system/staff/cell/glyph`."""
    p = subject.split("/")
    return int(p[2]), int(p[3]), int(p[4])
