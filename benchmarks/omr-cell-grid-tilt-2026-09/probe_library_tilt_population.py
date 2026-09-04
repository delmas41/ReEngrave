"""How common is a displaced cell grid across SCANNED pages generally?

The scan e2e benchmark reads page 1 of five works, and page 1 of a bound book
is where the paper is flattest — measured, only 7 of its 1143 cells sit past
the quarter-space parity-flip line, which is why an A/B on it moves 4 edits of
7894 and says nothing about the defect. This asks the population question
instead: over many pages of many scanned editions, what share of cells carry a
grid displaced far enough to name the wrong half-step slot?

Phase 1 only — no YOLO, no export, no scoring. The pages the labeling campaign
flagged by hand are included as a POSITIVE CONTROL: a survey that cannot
reproduce a known-bad page is measuring something else.

    python3 benchmarks/omr-cell-grid-tilt-2026-09/probe_library_tilt_population.py
    python3 ... --pages-per-edition 4 --dpi 600
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))

from tools.library.score_library import library_root  # noqa: E402
from tools.omr import measure_extractor as _me  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402

FLIP_SPACES = 0.25

#: The pages the campaign audit flagged by hand (FINDINGS.md §1), as a control.
#: A survey of scanned pages that does not reproduce these is not measuring
#: the thing they were flagged for.
CONTROL_PAGES = [
    ("editions/dvorak/symphony-9-op95/"
     "dvorak--symphony-9-op95--simrock-1894--imslp405834.pdf", 7),
    ("editions/mahler/symphony-1-gmw-11/"
     "mahler--symphony-1-gmw-11--edition-1906--imslp17070.pdf", 2),
    ("editions/mahler/symphony-1-gmw-11/"
     "mahler--symphony-1-gmw-11--edition-1906--imslp17070.pdf", 3),
    ("editions/brahms/symphony-1-op68/"
     "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf", 1),
    ("editions/rimsky-korsakov/scheherazade-op35/"
     "rimsky-korsakov--scheherazade-op35--eulenburg--imslp1010338.pdf", 3),
    ("editions/beethoven/symphony-5-op67/"
     "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp575951.pdf",
     47),
]

#: Pages sampled from deeper in each edition than the benchmark's page 1 — the
#: interesting region, since a bound scan's warp grows away from the flattest
#: opening. Chosen by position, not by looking at the answer first.
SURVEY_PAGES = (5, 17, 31, 48)


def measure_page(pdf: Path, page0: int, dpi: int) -> dict | None:
    try:
        img = render_page(pdf, page0, dpi=dpi)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}
    pws = detect_staves(img)
    if not pws.staves:
        return {"error": "no staves detected"}
    _me.detect_barlines(pws)
    cells = _me.extract_measures(pws)
    by_staff = {s.staff_index: s for s in pws.staves}

    offs, widths, wander = [], [], []
    for cell in cells:
        staff = by_staff.get(cell.staff_index)
        if staff is None or len(staff.line_ys) < 5:
            continue
        x0, _, x1, _ = cell.bbox_page_px
        got = _me._cell_line_offset(pws, staff, x0, x1)
        offs.append(abs(got[1]["offset_spaces"]) if got else 0.0)
        widths.append((x1 - x0) / max(1.0, float(staff.line_spacing_px)))
        if staff.line_wander_px is not None:
            wander.append(staff.line_wander_px / max(1.0, float(staff.line_spacing_px)))
    if not offs:
        return {"error": "no five-line cells"}
    o = np.array(offs)
    return {
        "n_staves": len(pws.staves),
        "n_cells": int(o.size),
        "n_past_flip": int((o >= FLIP_SPACES).sum()),
        "share_past_flip": round(float((o >= FLIP_SPACES).mean()), 4),
        "median": round(float(np.median(o)), 3),
        "p90": round(float(np.percentile(o, 90)), 3),
        "max": round(float(o.max()), 3),
        "median_cell_width_spaces": round(float(np.median(widths)), 2),
        "median_wander_spaces": (round(float(np.median(wander)), 3)
                                 if wander else None),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--pages-per-edition", type=int, default=len(SURVEY_PAGES))
    ap.add_argument("--max-editions", type=int, default=8)
    args = ap.parse_args(argv)

    lib = library_root()
    # Every edition the control pages come from, plus whatever else the store
    # holds, so the survey is not confined to the works already implicated.
    editions = sorted({rel for rel, _ in CONTROL_PAGES})
    others = sorted(
        str(p.relative_to(lib)) for p in (lib / "editions").rglob("*.pdf")
    )
    for rel in others:
        if rel not in editions and len(editions) < args.max_editions:
            editions.append(rel)

    rows = []
    print("CONTROL — pages the campaign flagged by hand")
    for rel, page0 in CONTROL_PAGES:
        pdf = lib / rel
        if not pdf.is_file():
            print(f"  {rel} p{page0}: MISSING", file=sys.stderr)
            continue
        m = measure_page(pdf, page0, args.dpi)
        rows.append({"role": "control", "edition": rel, "page": page0, **(m or {})})
        if m and "error" not in m:
            print(f"  {Path(rel).stem[:44]:44s} p{page0:<4d} "
                  f"cells {m['n_cells']:>4d} past-flip {m['n_past_flip']:>4d} "
                  f"({100 * m['share_past_flip']:>5.1f}%)  "
                  f"p90 {m['p90']:.3f} max {m['max']:.3f}", flush=True)
        else:
            print(f"  {Path(rel).stem[:44]:44s} p{page0:<4d} "
                  f"{(m or {}).get('error')}", flush=True)

    print("\nSURVEY — pages sampled deeper into each edition")
    for rel in editions:
        pdf = lib / rel
        if not pdf.is_file():
            continue
        for page0 in SURVEY_PAGES[:args.pages_per_edition]:
            m = measure_page(pdf, page0, args.dpi)
            rows.append({"role": "survey", "edition": rel, "page": page0,
                         **(m or {})})
            if m and "error" not in m:
                print(f"  {Path(rel).stem[:44]:44s} p{page0:<4d} "
                      f"cells {m['n_cells']:>4d} past-flip {m['n_past_flip']:>4d} "
                      f"({100 * m['share_past_flip']:>5.1f}%)  "
                      f"p90 {m['p90']:.3f} max {m['max']:.3f}", flush=True)
            else:
                print(f"  {Path(rel).stem[:44]:44s} p{page0:<4d} "
                      f"{(m or {}).get('error')}", flush=True)

    for role in ("control", "survey"):
        sel = [r for r in rows if r.get("role") == role and "n_cells" in r]
        if not sel:
            continue
        cells = sum(r["n_cells"] for r in sel)
        flip = sum(r["n_past_flip"] for r in sel)
        print(f"\n{role}: {len(sel)} pages, {cells} cells, {flip} past the "
              f"{FLIP_SPACES}-space flip line ({100.0 * flip / max(1, cells):.2f}%)")

    out = BENCH / "probe_library_tilt_population.json"
    out.write_text(json.dumps({"dpi": args.dpi, "rows": rows}, indent=1) + "\n")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
