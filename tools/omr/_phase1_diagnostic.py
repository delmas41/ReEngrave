"""Phase 1 barline-detection diagnostic. Captures per-cluster data
(vote count, inter-staff connectivity score) on a single PDF page so we
can analyze the distributions before deciding on tuning thresholds.

Not part of the production pipeline — drop into the tools/omr/ package
just so it has easy access to the private helpers.

Usage (inside the backend container, with weights mounted):

    python3 -m tools.omr._phase1_diagnostic <pdf> <page> > clusters.csv

Output columns:
    pdf, page, sys_idx, n_staves, cluster_x, n_votes,
    vote_fraction, connectivity, current_accept, n_inter_gaps

`current_accept` is what the existing tiered vote rule (no connectivity)
would decide. Useful for cross-referencing against connectivity scores
to see where the two signals agree / disagree.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from .preprocessing import render_page
from .staff_detector import detect_staves
from .measure_extractor import _detect_barlines_per_staff


def _connectivity(bin_img: np.ndarray, staves, x_col: int,
                  x_tolerance: int = 5) -> tuple[float, int]:
    """Returns (connectivity_fraction, n_inter_gaps). See the docstring on
    measure_extractor._intersystem_connectivity (which this mirrors)."""
    if len(staves) < 2:
        return 1.0, 0
    ordered = sorted(staves, key=lambda s: s.top_y)
    n_gaps = len(ordered) - 1
    n_connected = 0
    h, w = bin_img.shape
    for i in range(n_gaps):
        gap_top = ordered[i].bottom_y + 1
        gap_bot = ordered[i + 1].top_y
        if gap_bot <= gap_top:
            n_connected += 1
            continue
        x0 = max(0, x_col - x_tolerance)
        x1 = min(w, x_col + x_tolerance + 1)
        gt = max(0, gap_top); gb = min(h, gap_bot)
        if gt >= gb or x0 >= x1:
            continue
        strip = bin_img[gt:gb, x0:x1]
        if strip.size == 0:
            continue
        col_ink_fraction = (strip < 128).mean(axis=0)
        if col_ink_fraction.max() > 0.5:
            n_connected += 1
    return n_connected / max(n_gaps, 1), n_gaps


def _current_min_votes(n_staves: int) -> int:
    """Mirror of the existing tiered rule in measure_extractor.detect_barlines."""
    if n_staves <= 2:
        return n_staves
    elif n_staves <= 4:
        return n_staves - 1
    elif n_staves <= 8:
        return max(n_staves - 1, int(round(0.80 * n_staves)))
    elif n_staves <= 12:
        return int(round(0.65 * n_staves))
    else:
        return max(5, int(round(0.50 * n_staves)))


def diagnose(pdf_path: Path, page_idx: int, dpi: int = 300) -> list[dict]:
    """Run Phase 1 (staves + barline scanning) on one page, return
    per-cluster diagnostic rows (does NOT make any acceptance decisions
    beyond the current tiered rule — `current_accept` reflects that
    rule). No YOLO involved → fast (~30s for a dense page).
    """
    pi = render_page(pdf_path, page_idx, dpi=dpi)
    pws = detect_staves(pi)
    bin_img = pws.page.binary

    systems: dict[int, list] = {}
    for s in pws.staves:
        systems.setdefault(s.system_index, []).append(s)

    x_tolerance = 12
    rows: list[dict] = []
    for sys_idx, staves in systems.items():
        all_xs: list[int] = []
        for staff in staves:
            all_xs.extend(_detect_barlines_per_staff(bin_img, staff))
        if not all_xs:
            continue
        all_xs.sort()
        clusters: list[list[int]] = []
        for x in all_xs:
            if clusters and x - clusters[-1][-1] <= x_tolerance:
                clusters[-1].append(x)
            else:
                clusters.append([x])

        n_staves = len(staves)
        min_votes = _current_min_votes(n_staves)
        for cluster in clusters:
            x_mean = int(round(sum(cluster) / len(cluster)))
            n_votes = len(cluster)
            connectivity, n_inter_gaps = _connectivity(bin_img, staves, x_mean)
            rows.append({
                "pdf": pdf_path.name,
                "page": page_idx,
                "sys_idx": sys_idx,
                "n_staves": n_staves,
                "cluster_x": x_mean,
                "n_votes": n_votes,
                "vote_fraction": round(n_votes / max(n_staves, 1), 3),
                "connectivity": round(connectivity, 3),
                "current_accept": n_votes >= min_votes,
                "n_inter_gaps": n_inter_gaps,
            })
    return rows


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: python3 -m tools.omr._phase1_diagnostic <pdf> <page>",
              file=sys.stderr)
        return 2
    pdf = Path(sys.argv[1])
    page = int(sys.argv[2])
    rows = diagnose(pdf, page)
    if not rows:
        print("(no clusters found)", file=sys.stderr)
        return 1
    cols = list(rows[0].keys())
    print(",".join(cols))
    for r in rows:
        print(",".join(str(r[c]) for c in cols))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
