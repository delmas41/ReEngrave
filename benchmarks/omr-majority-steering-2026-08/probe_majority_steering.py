"""Where does majority-steered re-segmentation actually fire?

Phase 1 only (no detection), over the same 12-page real-scan corpus
`phase1_layout_eval` uses. For each page it reports, per system:

  * the bar count the system's staves agree on, or that they do not agree
  * how many staves deviate from it
  * what the conservative re-segmentation pass produces
  * what the majority-steered pass produces

The question this answers is not "is the pipeline better" — it is the prior
question of whether real scans contain the disagreement the feature exists to
act on, and whether steering fabricates bars when they do.

    python3 benchmarks/omr-majority-steering-2026-08/probe_majority_steering.py
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.measure_extractor import (  # noqa: E402
    detect_barlines, extract_measures, majority_bars_by_system,
    resegment_fused_measures,
)
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.training.phase1_layout_eval import CORPUS  # noqa: E402


def counts_by_system(cells) -> dict[int, list[int]]:
    per_staff: Counter = Counter()
    for c in cells:
        per_staff[(c.system_index, c.staff_index)] += 1
    out: dict[int, list[int]] = {}
    for (sys_idx, _st), n in per_staff.items():
        out.setdefault(sys_idx, []).append(n)
    return out


def main() -> None:
    tot_systems = tot_disagree = tot_steered_cells = tot_changed_systems = 0
    print(f"{'page':<15} {'sys':>4} {'staff bar counts':<28} "
          f"{'majority':>9} {'conserv':>8} {'steered':>8}")
    print("-" * 82)

    for key, pdf, page_index, dpi in CORPUS:
        if not pdf.exists():
            print(f"{key:<15} (pdf not on this machine)")
            continue
        page = render_page(pdf, page_index, dpi=dpi)
        pws = detect_barlines(detect_staves(page))
        cells = extract_measures(pws)

        conservative = resegment_fused_measures(pws, cells)
        majority = majority_bars_by_system(cells)
        steered = resegment_fused_measures(
            pws, cells, expected_bars_by_system=majority)

        c_counts, s_counts = counts_by_system(conservative), counts_by_system(steered)
        if not counts_by_system(cells):
            # Reported rather than skipped: a page that yields no staves must
            # not silently shrink the denominator of the summary below.
            print(f"{key:<15} {'—':>4} (no staves detected on this page)")
            continue
        for sys_idx in sorted(counts_by_system(cells)):
            tot_systems += 1
            raw = sorted(counts_by_system(cells)[sys_idx])
            maj = majority.get(sys_idx)
            deviating = sum(1 for n in raw if maj is not None and n != maj)
            if deviating:
                tot_disagree += 1
            c_n = max(c_counts.get(sys_idx, [0]))
            s_n = max(s_counts.get(sys_idx, [0]))
            if s_n != c_n:
                tot_changed_systems += 1
                tot_steered_cells += s_n - c_n
            shown = str(raw if len(raw) <= 8 else raw[:8] + ["..."])
            flag = "  <-- steered" if s_n != c_n else ("  (disagree)" if deviating else "")
            print(f"{key:<15} {sys_idx:>4} {shown:<28} "
                  f"{str(maj):>9} {c_n:>8} {s_n:>8}{flag}")

    print("-" * 82)
    print(f"systems: {tot_systems}   with a staff disagreeing from the majority: "
          f"{tot_disagree}   systems steering changed: {tot_changed_systems}   "
          f"bars added: {tot_steered_cells}")


if __name__ == "__main__":
    main()
