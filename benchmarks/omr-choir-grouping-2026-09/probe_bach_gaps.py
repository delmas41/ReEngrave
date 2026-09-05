"""Phase 1 diagnosis: WHY does the Bach Brandenburg 3 page shatter into choirs?

Renders the page exactly as the pipeline does (600 dpi), detects staves, then
answers, per adjacent-staff gap:

  1. what `gap_bridging_counts` computed (the wide-window rule that decides
     `existing_break`), with the window it actually used;
  2. what a FULL-WIDTH scan of the same band finds — every x whose column
     crosses the gap at >= BRIDGE_INK_FRACTION after the same closing — so we
     can say where the crossing ink physically is (bracket? left barline?
     interior barlines?) and whether the engraving draws barlines through the
     choir gaps at all;
  3. what `left_edge_barline_counts` computed and whether cue A's gate passed.

Run from the worktree root:
    python3 -m benchmarks.omr-choir-grouping-2026-09.probe_bach_gaps   # (won't import: dashes)
    PYTHONPATH=. python3 benchmarks/omr-choir-grouping-2026-09/probe_bach_gaps.py
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves
from tools.omr import system_grouping as sg

PDF = Path(
    "/Users/seanjohnson/Desktop/ReEngrave/library/editions/bach/"
    "brandenburg-concerto-3-in-g-major-bwv1048/"
    "bach--brandenburg-concerto-3-in-g-major-bwv1048--edition-peters-nr-4412--imslp468678.pdf"
)


def crossing_profile(binary, upper, lower, x0, x1):
    """All x in [x0,x1) whose column crosses the gap band at >= BRIDGE_INK_FRACTION,
    using the exact closing gap_bridging_counts uses."""
    height, width = binary.shape
    top = max(0, upper.bottom_y + 2)
    bot = min(height, lower.top_y - 2)
    x0 = max(0, x0)
    x1 = min(width, x1)
    if bot <= top or x1 <= x0:
        return [], (top, bot)
    band = (binary[top:bot, x0:x1] < 128).astype(np.uint8)
    spacing = max(upper.line_spacing_px, lower.line_spacing_px)
    k = max(3, int(round(spacing * sg.BRIDGE_GAP_TOLERANCE_SPACINGS)) * 2 + 1)
    closed = cv2.morphologyEx(band, cv2.MORPH_CLOSE, np.ones((k, 1), np.uint8))
    cov = closed.mean(axis=0)
    xs = [int(x0 + i) for i in np.flatnonzero(cov > sg.BRIDGE_INK_FRACTION)]
    return xs, (top, bot)


def runs(xs):
    """Compress a sorted x list into (start, end, n) runs."""
    if not xs:
        return []
    out = []
    s = p = xs[0]
    for x in xs[1:]:
        if x - p > 3:
            out.append((s, p, p - s + 1))
            s = x
        p = x
    out.append((s, p, p - s + 1))
    return out


def main():
    page = render_page(PDF, 0, dpi=600)
    binary = page.binary
    pws = detect_staves(page)
    staves = sorted(pws.staves, key=lambda s: s.top_y)
    print(f"page {binary.shape[1]}x{binary.shape[0]} @600dpi; {len(staves)} staves")
    n_systems = 1 + max(s.system_index for s in staves)
    sizes = {}
    for s in staves:
        sizes.setdefault(s.system_index, 0)
        sizes[s.system_index] += 1
    print(f"as-shipped grouping: {n_systems} systems, sizes {[sizes[k] for k in sorted(sizes)]}")

    spacing_pg = statistics.median([s.line_spacing_px for s in staves])
    x_start_med = int(statistics.median([s.x_start for s in staves]))
    x_end_med = int(statistics.median([s.x_end for s in staves]))
    wx0, wx1 = sg._robust_x_window(staves)
    print(f"\npage spacing median {spacing_pg:.2f}px")
    print(f"x_start median {x_start_med}, x_end median {x_end_med}")
    print(f"wide window: [{wx0}, {wx1}]  (margin {sg.WINDOW_MARGIN_SPACINGS} spacings)")
    lx0 = max(0, int(x_start_med - sg.LEFT_BAND_LEFT_SPACINGS * spacing_pg))
    lx1 = int(x_start_med + sg.LEFT_BAND_RIGHT_SPACINGS * spacing_pg)
    print(f"cue-A left band: [{lx0}, {lx1}]")
    print(f"x_starts: {[s.x_start for s in staves]}")

    bridging = sg.gap_bridging_counts(binary, staves)
    left_counts = sg.left_edge_barline_counts(binary, staves)

    print("\nPer gap: [i] upper->lower  gap_px  wide_count  left_count  "
          "| full-width crossing runs (x_start-x_end, width)")
    results = []
    for i, (u, l) in enumerate(zip(staves, staves[1:])):
        gap = l.top_y - u.bottom_y
        xs_full, (top, bot) = crossing_profile(binary, u, l, 0, binary.shape[1])
        r = runs(xs_full)
        in_window = [x for x in xs_full if wx0 <= x < wx1]
        print(f"[{i:2d}] s{u.staff_index:2d}->s{l.staff_index:2d}  gap {gap:3d}px "
              f"({gap/spacing_pg:4.1f}sp)  wide={bridging[i]:4d}  left={left_counts[i]:3d}  "
              f"in_win={len(in_window):4d}  full={len(xs_full):4d}  runs={r[:8]}")
        results.append({
            "gap_index": i,
            "upper": u.staff_index, "lower": l.staff_index,
            "gap_px": gap,
            "wide_count": bridging[i], "left_count": left_counts[i],
            "n_crossing_full_width": len(xs_full),
            "crossing_runs": r,
            "band_y": [top, bot],
        })

    # cue A gate replication
    existing_break = [
        (sg._x_overlap_frac(u, l) <= sg.MIN_X_OVERLAP_FRAC) or (bridging[i] == 0)
        for i, (u, l) in enumerate(zip(staves, staves[1:]))
    ]
    interior = [i for i in range(len(existing_break))
                if not existing_break[i] and 0 <= left_counts[i]]
    crossed = sum(1 for i in interior if left_counts[i] >= sg.LEFT_BAND_MIN_CROSS)
    print(f"\nexisting_break (wide rule): {[i for i, b in enumerate(existing_break) if b]}")
    print(f"cue A: interior gaps {len(interior)}, left-crossed {crossed} "
          f"-> gate {'PASS' if interior and crossed/len(interior) >= sg.LEFT_BAND_GATE_FRAC else 'FAIL (cue A inert)'}")

    out = {
        "n_staves": len(staves),
        "grouping_sizes": [sizes[k] for k in sorted(sizes)],
        "spacing_median": spacing_pg,
        "x_start_median": x_start_med,
        "wide_window": [wx0, wx1],
        "left_band": [lx0, lx1],
        "x_starts": [s.x_start for s in staves],
        "x_ends": [s.x_end for s in staves],
        "staff_tops": [s.top_y for s in staves],
        "staff_bottoms": [s.bottom_y for s in staves],
        "gaps": results,
        "existing_break_gaps": [i for i, b in enumerate(existing_break) if b],
        "cue_a_gate_passed": bool(interior and crossed / len(interior) >= sg.LEFT_BAND_GATE_FRAC),
    }
    out_path = Path(__file__).parent / "probe_bach_gaps.json"
    out_path.write_text(json.dumps(out, indent=1))
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
