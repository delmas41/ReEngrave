#!/usr/bin/env python3
"""System grouping: connectivity vs the gap-size heuristic, against ground
truth established by LOOKING at the pages.

Ground truth is the number of systems on each page, read off a rendered
thumbnail by eye. That matters: an earlier evaluation used "how tightly does
staves-per-system cluster across pages?" as a ground-truth-free proxy, on the
argument that true instrumentation is constant. It is a BAD proxy — it rewards
merging every page into one big system, and it reported success for a variant
that was merging two systems into one on 6 of 12 pages.

Usage: python3 benchmarks/omr-system-grouping-2026-08/eval_grouping.py
"""
from __future__ import annotations

import collections
import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import _assign_systems, detect_staves
from tools.omr.system_grouping import assign_systems

B9 = ("/Users/seanjohnson/Desktop/ReEngrave/tools/omr/training/data/imslp/"
      "beethoven-symphony-9/pdfs/imslp-516488/score.pdf")
_B5 = glob.glob("/Users/seanjohnson/Documents/Gradus-Assets/Scores/"
                "Scores For Gradus/IMSLP984073*")

# (pdf, page, dpi, true number of systems).
#
# Ground truth is the number of LEFT BRACKETS on the page, read off a crop of
# the left margin. Counting systems from a whole-page thumbnail does not work
# and produced a wrong label set on the first attempt: at thumbnail scale the
# brass-to-strings bracket-GROUP gap looks exactly like a system break, so
# pages 30-50 (single 13-staff systems) were all mislabelled as 2.
CASES = [(B9, page, 300, truth) for page, truth in (
    (20, 2), (25, 2), (30, 1), (35, 1), (40, 1), (45, 1),
    (50, 1), (55, 2), (60, 2), (65, 2), (70, 2), (75, 2),
)]
if _B5:
    CASES += [(_B5[0], 10, 300, 2), (_B5[0], 10, 600, 2),
              # Adjudicated 2026-08-31 from the left margin: three brackets,
              # measure numbers 229/243/256, instrument labels restarting at
              # each. The set's first MERGE case — LEGATO's cross-check found it.
              (_B5[0], 40, 300, 3)]

# Beethoven is not a corpus. A rule fitted to B9+B5 scored 14/14 here and then
# over-split TWELVE pages on everything else, because orchestral engraving
# breaks barlines between instrument families and those two editions happen not
# to — see RULE_FIX_ATTEMPT_2026-08-31.md. These eight pages were hand-read the
# same way (left-margin crop, count the brackets) to widen the set past one
# publisher. All eight currently pass; they exist to stop the NEXT idea.
_SCORES = "/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus/PDF Scores"
_WIDER = [
    ("Mahler_5_.pdf", 2, 1),    # 15 staves, one bracket Fag.->Bässe, m.9
    ("Mahler_5_.pdf", 10, 1),   # 18 staves, Hoboen->Bässe, m.78
    ("Mahler_5_.pdf", 20, 1),   # 16 staves, Flöten->Bässe, m.171
    ("IMSLP15420-Debussy_-_La_Mer_(orch._score).pdf", 2, 2),
    ("IMSLP15420-Debussy_-_La_Mer_(orch._score).pdf", 20, 1),   # 16 staves, one system
    ("IMSLP421137-PMLP03667-Ravel_Bolero.pdf", 2, 4),   # m. 14/21/27/33
    # 32 staves, m.153 and m.159. LEGATO says 3 here and is WRONG — it returns
    # three overlapping boxes on this page. Second recorded miner error, after B9 p25.
    ("IMSLP421137-PMLP03667-Ravel_Bolero.pdf", 10, 2),
    ("IMSLP421137-PMLP03667-Ravel_Bolero.pdf", 20, 1),  # 19 staves, m.219
]
for _name, _page, _truth in _WIDER:
    _path = f"{_SCORES}/{_name}"
    if glob.glob(_path):
        CASES.append((_path, _page, 300, _truth))


def main() -> int:
    rows = []
    for pdf, page, dpi, truth in CASES:
        pi = render_page(pdf, page, dpi=dpi)
        staves = sorted(detect_staves(pi).staves, key=lambda s: s.top_y)

        # Connectivity is what detect_staves already applied.
        conn = 1 + max(s.system_index for s in staves)
        conn_sizes = sorted(collections.Counter(
            s.system_index for s in staves).values(), reverse=True)

        # Re-run the old gap heuristic on the same staves for comparison.
        for s in staves:
            s.system_index = 0
        gap_staves = _assign_systems(list(staves))
        gap = 1 + max(s.system_index for s in gap_staves)
        gap_sizes = sorted(collections.Counter(
            s.system_index for s in gap_staves).values(), reverse=True)

        # Restore.
        assign_systems(pi.binary, staves)
        rows.append((page, dpi, len(staves), truth, gap, gap_sizes, conn, conn_sizes))

    hdr = f"{'page':>6} {'dpi':>4} {'staves':>6} {'true':>4} | {'gap':>3} {'sizes':<22} | {'conn':>4} {'sizes':<22}"
    print(hdr)
    print("-" * len(hdr))
    gap_ok = conn_ok = 0
    for page, dpi, n, truth, gap, gs, conn, cs in rows:
        gap_ok += gap == truth
        conn_ok += conn == truth
        print(f"{page:>6} {dpi:>4} {n:>6} {truth:>4} | {gap:>3}{'✓' if gap==truth else '✗'} "
              f"{str(gs):<21} | {conn:>4}{'✓' if conn==truth else '✗'} {str(cs):<21}")
    total = len(rows)
    print("-" * len(hdr))
    print(f"system-count correct — gap heuristic: {gap_ok}/{total} ({gap_ok/total:.0%})   "
          f"connectivity: {conn_ok}/{total} ({conn_ok/total:.0%})")
    gap_singles = sum(r[5].count(1) for r in rows)
    conn_singles = sum(r[7].count(1) for r in rows)
    print(f"spurious single-staff systems — gap: {gap_singles}   connectivity: {conn_singles}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
