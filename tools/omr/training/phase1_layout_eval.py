"""Phase 1 layout probe — staff / system / measure counts across a fixed corpus.

Phase 1 (staff detection → barline detection → measure extraction) had no
regression baseline, which is why two of its bugs survived so long: the
`test_pipeline.py` assertions were written from an eyeballed layout that was
never checked, and one of them (18 staves on Beethoven 5 p.10) was satisfied by
a PHANTOM staff standing in for five real ones.

This probe reports the counts for a fixed page list so any Phase-1 change can be
diffed before/after. Pages with hand-verified ground truth (see
`benchmarks/omr-phase1-baseline/ground-truth.json`) are scored; the rest are
reported as bare numbers, where the point is that they should not MOVE
unnoticed.

    python3 -m tools.omr.training.phase1_layout_eval --out before.json
    python3 -m tools.omr.training.phase1_layout_eval --out after.json --compare before.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves
from tools.omr.measure_extractor import detect_barlines, extract_measures


SCORE_DIR = Path(
    "/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus"
)
PDF_DIR = SCORE_DIR / "PDF Scores"

# (key, pdf, page_index, dpi). Chosen to span the engraving styles the pipeline
# actually meets: modern keyboard typesetting, a pocket orchestral score, dense
# late-romantic orchestration, and a small-format 19th-century method book.
CORPUS: list[tuple[str, Path, int, int]] = [
    ("wtc-p5",        PDF_DIR / "IMSLP932182-PMLP5948-well-tempered-clavier-I-book.pdf", 5, 600),
    ("wtc-p8",        PDF_DIR / "IMSLP932182-PMLP5948-well-tempered-clavier-I-book.pdf", 8, 600),
    ("beet5-p10",     SCORE_DIR / "IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf", 10, 600),
    ("beet5-p2",      SCORE_DIR / "IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf", 2, 600),
    ("beet5-p8",      SCORE_DIR / "IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf", 8, 600),
    ("bolero-p31",    PDF_DIR / "IMSLP421137-PMLP03667-Ravel_Bolero.pdf", 31, 300),
    ("bolero-p5",     PDF_DIR / "IMSLP421137-PMLP03667-Ravel_Bolero.pdf", 5, 300),
    ("lamer-p25",     PDF_DIR / "IMSLP15420-Debussy_-_La_Mer_(orch._score).pdf", 25, 300),
    ("mahler5-p11",   PDF_DIR / "Mahler_5_.pdf", 11, 300),
    ("handel-red-p1", PDF_DIR / "Haendel_Messiah_reduction.pdf", 1, 600),
    ("handel-lead-p1", PDF_DIR / "Haendel_Messiah_lead-sheet.pdf", 1, 600),
    ("kirchhoff-p10", SCORE_DIR / "Kirchhoff_L'ABC-Musical.pdf", 10, 600),
]

GROUND_TRUTH_PATH = Path("benchmarks/omr-phase1-baseline/ground-truth.json")


def probe_page(pdf: Path, page_index: int, dpi: int) -> dict[str, Any]:
    page = render_page(pdf, page_index, dpi=dpi)
    pws = detect_staves(page)
    pws = detect_barlines(pws)
    cells = extract_measures(pws)

    by_sys: dict[int, list] = {}
    for s in pws.staves:
        by_sys.setdefault(s.system_index, []).append(s)
    measures: dict[int, set] = {}
    for c in cells:
        measures.setdefault(c.system_index, set()).add(c.measure_index)

    spacings = [float(s.line_spacing_px) for s in pws.staves]
    median_spacing = float(np.median(spacings)) if spacings else 0.0
    # A staff whose line spacing is far off the page median is the phantom
    # signature: five lines from five DIFFERENT staves grouped into one.
    outliers = [
        {"staff_index": s.staff_index, "spacing": round(float(s.line_spacing_px), 1)}
        for s in pws.staves
        if median_spacing > 0 and abs(float(s.line_spacing_px) - median_spacing) / median_spacing > 0.30
    ]

    return {
        "page_px": [page.width, page.height],
        "n_staves": len(pws.staves),
        # One-line percussion staves, reported separately because they are the
        # one kind of staff whose absence is INVISIBLE in the total: a page
        # that misses one still looks like a page of n staves.
        "n_single_line_staves": sum(1 for s in pws.staves if len(s.line_ys) == 1),
        "n_systems": len(by_sys),
        "staves_per_system": [len(by_sys[i]) for i in sorted(by_sys)],
        "measures_per_system": [len(measures[i]) for i in sorted(measures)],
        "n_cells": len(cells),
        "median_line_spacing": round(median_spacing, 1),
        "spacing_outlier_staves": outliers,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--compare", type=Path, help="prior run to diff against")
    ap.add_argument("--only", nargs="*", help="subset of corpus keys")
    args = ap.parse_args()

    gt = {}
    if GROUND_TRUTH_PATH.exists():
        gt = json.loads(GROUND_TRUTH_PATH.read_text())["pages"]

    results: dict[str, Any] = {}
    for key, pdf, page_index, dpi in CORPUS:
        if args.only and key not in args.only:
            continue
        if not pdf.exists():
            print(f"{key:15s} SKIP (missing {pdf.name})")
            continue
        r = probe_page(pdf, page_index, dpi)
        results[key] = r
        line = (
            f"{key:15s} staves={r['n_staves']:3d} systems={r['n_systems']:2d} "
            f"per_sys={r['staves_per_system']} measures={r['measures_per_system']} "
            f"cells={r['n_cells']:4d}"
        )
        if r["n_single_line_staves"]:
            line += f"  1-line={r['n_single_line_staves']}"
        if r["spacing_outlier_staves"]:
            line += f"  PHANTOM?{r['spacing_outlier_staves']}"
        if key in gt:
            g = gt[key]
            ok_s = r["staves_per_system"] == g["staves_per_system"]
            line += f"  GT staves:{'OK' if ok_s else 'FAIL ' + str(g['staves_per_system'])}"
            # A page may be recorded for its staff layout alone; a null here
            # means "not hand-counted", which must not read as a failure.
            if g.get("measures_per_system") is not None:
                ok_m = r["measures_per_system"] == g["measures_per_system"]
                line += f" bars:{'OK' if ok_m else 'FAIL ' + str(g['measures_per_system'])}"
        print(line)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2) + "\n")
    print(f"\nwrote {args.out}")

    if args.compare and args.compare.exists():
        prior = json.loads(args.compare.read_text())
        print(f"\n=== changes vs {args.compare} ===")
        moved = False
        for key, r in results.items():
            p = prior.get(key)
            if not p:
                continue
            for field in ("n_staves", "n_single_line_staves", "n_systems",
                          "staves_per_system", "measures_per_system", "n_cells"):
                if p.get(field) != r[field]:
                    moved = True
                    print(f"  {key:15s} {field}: {p.get(field)} -> {r[field]}")
        if not moved:
            print("  (no change)")


if __name__ == "__main__":
    main()
