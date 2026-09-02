#!/usr/bin/env python3
"""How far left of the staves does an edition actually PRINT its labels?

`staff_labels_vision.MARGIN_SPACINGS` is the one number that decides whether an
instrument name arrives whole or with its first letters cut off, and 2026-08-31
moved it 14 -> 20 on twelve systems of Beethoven 5 and 6
(`benchmarks/omr-margin-labels-2026-08/SURYA_BAKEOFF_2026-08-31.md`). The scan
benchmark then found the same failure shape on other publishers — `ken in C u. G`
for Pauken, `larinetten in B` for 2 Klarinetten in B — so the question is whether
20 is still too narrow, and by how much, rather than what a bigger number does.

This measures the printing, not the reader. For each staff it walks LEFT from
the crop's own reference column and reports the leftmost ink in that staff's
band, in staff spacings — which is the unit `MARGIN_SPACINGS` is expressed in
and the only unit that transfers between a 2897-px scan and a 5409-px one.

    python3 benchmarks/omr-scan-e2e-2026-09/probe_margin_reach.py
    python3 benchmarks/omr-scan-e2e-2026-09/probe_margin_reach.py --rows brahms-sym1-mvt1-317803-p1

⚠️ A LEFTMOST INK COLUMN IS NOT A LABEL. The margin also holds the bracket, the
system's initial rule, page furniture and, on a scan, the shadow of the binding
and the page edge. So the probe reports the ink RUN it finds — its width, its
gap to the staff — and prints the per-staff numbers rather than a single verdict.
Read the columns, do not trust a summary statistic over them.
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
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.staff_labels_vision import (  # noqa: E402
    MARGIN_SPACINGS,
    OVERLAP_SPACINGS,
    _spacing,
)

#: How far left to LOOK, well past any plausible label, so the measurement is
#: not bounded by the constant it is measuring.
SEARCH_SPACINGS = 45.0

#: A column counts as inked when this fraction of the band's rows are dark.
#: Deliberately low — a capital letter occupies a few rows of a staff-high band.
INK_ROW_FRACTION = 0.02


def _runs(inked: np.ndarray, min_gap: int) -> list[tuple[int, int]]:
    """Contiguous inked column ranges, merging gaps narrower than `min_gap`.

    The gap merge is what makes a WORD one run instead of one run per letter.
    """
    out: list[tuple[int, int]] = []
    for x in np.flatnonzero(inked):
        if out and x - out[-1][1] <= min_gap:
            out[-1] = (out[-1][0], int(x))
        else:
            out.append((int(x), int(x)))
    return out


def probe_row(row: dict, dpi: int) -> dict:
    lib = library_root()
    pdf = lib / row["edition"]["catalog_path"]
    page_index = row["page"]["pdf_page_index"]
    page = render_page(pdf, page_index, dpi=dpi)
    pws = detect_staves(page)
    staves = pws.staves
    if not staves:
        return {"row_id": row["row_id"], "error": "no staves"}

    # The crop's own frame of reference, copied from `margin_strip` so the
    # numbers are directly comparable to MARGIN_SPACINGS.
    spacing = _spacing(staves)
    x_starts = sorted(s.x_start for s in staves)
    x_ref = x_starts[len(x_starts) // 2]
    x_lo = max(0, int(x_ref - SEARCH_SPACINGS * spacing))
    x_hi = min(page.binary.shape[1], int(x_ref + OVERLAP_SPACINGS * spacing))

    # A word's letters are separated by less than a staff space; a label is
    # separated from the bracket by much more.
    min_gap = max(2, int(0.8 * spacing))

    per_staff = []
    for s in staves:
        top = max(0, s.top_y - int(0.5 * spacing))
        bot = min(page.binary.shape[0], s.bottom_y + int(0.5 * spacing))
        band = page.binary[top:bot, x_lo:x_hi]
        if band.size == 0:
            continue
        inked = (band == 0).mean(axis=0) >= INK_ROW_FRACTION
        runs = [(a, b) for a, b in _runs(inked, min_gap)]
        # Express every edge as spacings LEFT of x_ref — the same axis as the
        # constant. Positive = left of the reference.
        def sp(x_local: float) -> float:
            return round((x_ref - (x_lo + x_local)) / spacing, 2)

        per_staff.append({
            "staff": s.staff_index,
            "runs": [{"left_sp": sp(a), "right_sp": sp(b),
                      "width_sp": round((b - a) / spacing, 2)}
                     for a, b in runs],
        })
    return {
        "row_id": row["row_id"],
        "dpi": dpi,
        "spacing_px": round(spacing, 2),
        "x_ref": int(x_ref),
        "page_px": [int(page.binary.shape[1]), int(page.binary.shape[0])],
        "n_staves": len(staves),
        "per_staff": per_staff,
    }


def report(res: dict, cutoff: float) -> None:
    print(f"\n=== {res['row_id']}   spacing {res['spacing_px']}px  "
          f"x_ref {res['x_ref']}  page {res['page_px'][0]}x{res['page_px'][1]}")
    if "error" in res:
        print("   ", res["error"])
        return
    print(f"    {'staff':>5s}  runs left of x_ref, in staff spacings "
          f"(| = the {cutoff} crop edge)")
    clipped = 0
    for st in res["per_staff"]:
        # Only runs that START left of the staff are margin content.
        margin = [r for r in st["runs"] if r["left_sp"] > 0.5]
        # A run the crop CUTS: it begins outside and ends inside.
        cut = [r for r in margin if r["left_sp"] > cutoff > r["right_sp"]]
        clipped += bool(cut)
        cells = " ".join(
            f"{'>' if r['left_sp'] > cutoff else ' '}"
            f"[{r['left_sp']:5.1f}..{r['right_sp']:5.1f}]"
            for r in margin) or "(nothing)"
        print(f"    {st['staff']:>5d}  {cells}")
    print(f"    -> {clipped} of {len(res['per_staff'])} staves have a margin ink "
          f"run that the {cutoff}-spacing crop cuts through")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rows", nargs="+", default=None)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--cutoff", type=float, default=MARGIN_SPACINGS)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    doc = json.loads((BENCH / "works.json").read_text())
    rows = [r for r in doc["rows"]
            if args.rows is None or r["row_id"] in args.rows]
    results = []
    for row in rows:
        if row["window"].get("last_ref_measure") is None and args.rows is None:
            continue
        res = probe_row(row, args.dpi)
        results.append(res)
        report(res, args.cutoff)
    if args.out:
        args.out.write_text(json.dumps(results, indent=1) + "\n")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
