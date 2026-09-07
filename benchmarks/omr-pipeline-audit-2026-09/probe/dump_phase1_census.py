#!/usr/bin/env python3
"""What Phase 1 threw away on one page, and what evidence admitted its barlines.

Phase 1 only — `detect_staves` -> `detect_barlines` -> `extract_measures` — so
it runs in seconds with no YOLO weights and no venv beyond the repo's own.

Two tables:

* `PageWithStaves.deletion_counts`, the per-reason census of everything
  `staff_detector` and `measure_extractor` discarded. Before 2026-09-06 most of
  these sites recorded nothing at all, so a page that came back a staff short
  or a bar short gave no way to ask which gate ate it.
* `Barline.accept_prong` / `n_votes` / `connectivity` / `span_ink`, the
  evidence each accepted column cleared its acceptance rule on — computed by
  `detect_barlines` since forever and destroyed at the constructor until the
  same day.

⚠️ Read a count as a REASON, not a defect. `n_barline_components_dropped_*` is
large and healthy on any real page (most vertical ink is stems). The counts
worth staring at are the ones that should be near zero:
`n_staves_dropped_as_body_text` on a music-only page,
`n_measure_cells_dropped_too_narrow`, and
`n_barlines_dropped_at_system_edge` above two per system.

    python3 benchmarks/omr-pipeline-audit-2026-09/probe/dump_phase1_census.py \
        <pdf> --page 0 [--dpi 600]
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.measure_extractor import detect_barlines, extract_measures
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--dpi", type=int, default=600)
    args = ap.parse_args()

    page = render_page(args.pdf, args.page, dpi=args.dpi)
    pws = detect_staves(page)
    n_after_staves = dict(pws.deletion_counts)
    pws = detect_barlines(pws)
    cells = extract_measures(pws)

    n_sys = 1 + max((s.system_index for s in pws.staves), default=-1)
    print(f"{Path(args.pdf).name} p{args.page} @ {args.dpi}dpi: "
          f"{len(pws.staves)} staves / {n_sys} systems / "
          f"{len(pws.barlines)} barlines / {len(cells)} cells")

    print("\n── deletion census ──")
    for k, v in sorted(pws.deletion_counts.items()):
        stage = "staff_detector" if k in n_after_staves else "measure_extractor"
        print(f"  {v:7d}  {k}   [{stage}]")
    if not pws.deletion_counts:
        print("  (nothing recorded — every gate abstained)")

    print("\n── barline acceptance evidence ──")
    prongs = Counter(b.accept_prong for b in pws.barlines)
    for prong, n in prongs.most_common():
        print(f"  {n:7d}  {prong}")
    regimes = Counter((b.barlines_cross_gaps, b.choir_cue_c_override)
                      for b in pws.barlines)
    for (crosses, cue_c), n in regimes.most_common():
        print(f"  {n:7d}  barlines_cross_gaps={crosses} "
              f"choir_cue_c_override={cue_c}")
    if pws.barlines:
        votes = [b.n_votes for b in pws.barlines if b.n_votes is not None]
        conns = [b.connectivity for b in pws.barlines
                 if b.connectivity is not None]
        spans = [b.span_ink for b in pws.barlines if b.span_ink is not None]
        if votes:
            print(f"  votes      min {min(votes)} max {max(votes)} "
                  f"(of {pws.barlines[0].n_staves_in_system} staves, "
                  f"threshold {pws.barlines[0].min_votes})")
        print(f"  connectivity measured on {len(conns)}/{len(pws.barlines)}"
              + (f", range {min(conns):.3f}-{max(conns):.3f}" if conns else ""))
        print(f"  span_ink     measured on {len(spans)}/{len(pws.barlines)}"
              + (f", range {min(spans):.3f}-{max(spans):.3f}" if spans else ""))
        # ⚠️ The standing warning: connectivity is ANTI-CORRELATED with
        # correctness across families. An open score bars per staff, so its
        # real barlines carry no inter-staff gap ink and score 0.0 — measured,
        # a naive `>= 0.4` filter culls 7 of 8 UNANIMOUS barlines on the
        # engraved Brahms fixture and 0 of 17 on the Beethoven scan. Never
        # compare this number across pages without reading
        # `barlines_cross_gaps` first.
        culled = [b for b in pws.barlines if (b.connectivity or 0.0) < 0.4]
        unanimous = [b for b in culled
                     if b.n_votes is not None
                     and b.n_votes == b.n_staves_in_system]
        print(f"  a naive connectivity>=0.4 filter would cull "
              f"{len(culled)}/{len(pws.barlines)} "
              f"({len(unanimous)} of them UNANIMOUSLY voted)")


if __name__ == "__main__":
    main()
