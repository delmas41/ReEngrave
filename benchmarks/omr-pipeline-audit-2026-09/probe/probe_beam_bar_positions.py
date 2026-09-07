#!/usr/bin/env python3
"""Agent I, round 2 — N4: does the FABRICATED beam-bar position diverge from the
MEASURED one on real pages?

THE FINDING UNDER TEST (round 1, §5.2 N4).

  * `line_detection._stacked_bar_count` counts how many bars are stacked in a
    beam component by finding, per sampled column, the rows where ink STARTS
    (`cols & ~above`, `:374-376`). Those rows ARE the bars' positions. It
    reduces them to `median(count)` and throws the positions away.
  * `detect_beams:544-551` then SYNTHESISES the positions: it splits the
    component's bounding box into `n_bars` equal slices,
    `y_canonical = y + k*(h/n_bars)`, `height = h // n_bars`.
  * `rhythm._beams_attached_to_stem` clusters beam y-CENTRES at a tolerance of
    `BEAM_Y_CLUSTER_FACTOR (0.35) x staff spacing` to decide how many levels a
    stem carries — hence the note's duration.

So whenever `n_bars > 1`, the duration is decided by clustering coordinates
nobody measured. The module's own docstring says a sloped beam fills only
43-46% of its box against 95% for a level one, which is exactly the case where
even division is wrong.

THE NUMBER THIS PROBE PRODUCES: over accepted multi-bar components on real
pages, how far is the fabricated bar centre from the measured one, in staff
spaces, and how often does that exceed the 0.35-space clustering tolerance?
A divergence under the tolerance changes no level and is a null result.

It also reports N5b: the box FILL RATIO (`area/(w*h)`), which
`connectedComponentsWithStats` already computes and `detect_beams:527` uses
only as a floor.

⚠️ This RENDERS PAGES and runs phase 1. It runs no detector, needs no weights,
and is not one of the embargoed benchmarks. ~1 minute a page.

    python3 .../probe_beam_bar_positions.py --pages 2   # default rows
"""
from __future__ import annotations
import argparse, json, statistics as st, sys
from pathlib import Path
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from fixture_root import env_path, must_glob, must_exist  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import cv2, numpy as np  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.measure_extractor import detect_barlines, extract_measures  # noqa: E402
from tools.omr.staff_line_removal import remove_staff_lines  # noqa: E402
from tools.omr import line_detection as ld  # noqa: E402

#: gitignored (6.4 GB score store). Overridable; default unchanged.
LIB = env_path("OMR_LIBRARY_ROOT", "/Users/seanjohnson/Desktop/ReEngrave/library")
ROWS = ROOT / "benchmarks/omr-scan-e2e-2026-09/works.json"
#: distinct publishers, so a finding is not one edition's engraving
DEFAULT_ROWS = ["beethoven-sym5-mvt1-984073-p1", "brahms-sym1-mvt1-317803-p1"]
#: ENGRAVED fixtures, page 0. `mozart-sym41-mvt1` and `brahms-sym1-mvt1` are
#: the two pages the `_stacked_bar_count` / `_beams_attached_to_stem`
#: docstrings use as their worked examples, so they are where the fabrication
#: is most likely to matter. Build products of `orchestral_eval.excerpt()`;
#: this probe only READS them and runs no benchmark.
FIXTURES = env_path("OMR_ENGRAVED_FIXTURES",
                    "/Users/seanjohnson/Desktop/ReEngrave/benchmarks/omr-orchestral-e2e/fixtures")
DEFAULT_ENGRAVED = ["mozart-sym41-mvt1", "brahms-sym1-mvt1", "tchaikovsky-sym6-mvt2"]


def measured_bar_rows(labels, label, x, y, w, h, max_samples=48):
    """The bars' MEASURED centre rows — what `_stacked_bar_count` computes and
    discards. Mirrors its sampling exactly, then keeps the run positions.

    Returns `(n_bars_median, [centre_row_per_bar])`, or `(n, None)` where the
    columns do not agree on how many runs there are (nothing to average).
    """
    roi = labels[y:y + h, x:x + w] == label
    if roi.size == 0:
        return 1, None
    step = max(1, roi.shape[1] // max_samples)
    cols = roi[:, ::step]
    above = np.vstack([np.zeros((1, cols.shape[1]), dtype=bool), cols[:-1]])
    starts = cols & ~above
    counts = starts.sum(axis=0)
    nz = counts[counts > 0]
    if nz.size == 0:
        return 1, None
    n = max(1, int(np.median(nz)))
    # keep only columns that agree with the median, then average the k-th run
    good = [c for c in range(cols.shape[1]) if counts[c] == n]
    if not good:
        return n, None
    per_bar = [[] for _ in range(n)]
    for c in good:
        rows = np.flatnonzero(starts[:, c])
        ends = np.flatnonzero(cols[:, c] & ~np.vstack(
            [cols[1:, c:c + 1], np.zeros((1, 1), dtype=bool)]).ravel())
        for k, r0 in enumerate(rows[:n]):
            # centre of run k = start + half its own length
            nxt = rows[k + 1] if k + 1 < len(rows) else cols.shape[0]
            run = cols[r0:nxt, c]
            run_len = int(np.argmin(run)) if (~run).any() else int(nxt - r0)
            per_bar[k].append(y + r0 + run_len / 2.0)
    return n, [float(np.mean(v)) for v in per_bar if v] or None


def census_cell(cell):
    """Accepted beam components in one cell, with fabricated vs measured."""
    src = cell.image_no_staff if cell.image_no_staff is not None else cell.image
    if src is None or src.size == 0:
        return []
    spacing = ld._staff_line_spacing(cell)
    if spacing <= 1.0:
        return []
    stems = ld.detect_stems(cell)
    ink = ld._binary_ink(src)
    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (max(3, int(round(spacing * 1.5))), 1))
    opened = cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel)
    num, labels, stats, _ = cv2.connectedComponentsWithStats(opened, connectivity=8)
    min_w = int(round(spacing * 1.5))
    min_h = max(2, int(round(spacing * 0.10)))
    max_h = max(3, int(round(spacing * 2.5)))
    anchors = [s for s in stems if s.height_canonical >= spacing * 2.8]
    out = []
    for i in range(1, num):
        x, y, w, h, area = stats[i]
        if w < min_w or h < min_h or h > max_h:
            continue
        if area < max(6, spacing) or w / max(1, h) < 2.0:
            continue
        if ld._attached_stem_count(labels, i, anchors, x, y, w, h, spacing,
                                   spacing * 1.0, spacing * 2.5) < 2:
            continue
        n_bars = ld._stacked_bar_count(labels, i, x, y, w, h)
        n_meas, centres = measured_bar_rows(labels, i, x, y, w, h)
        sub_h = max(1, h // n_bars)
        fabricated = [y + k * (h / n_bars) + sub_h // 2 for k in range(n_bars)]
        rec = {"n_bars": int(n_bars), "fill": float(area) / max(1, w * h),
               "h_spaces": h / spacing, "w_spaces": w / spacing,
               "spacing": spacing, "agree": n_meas == n_bars}
        if centres and n_meas == n_bars and len(centres) == n_bars:
            rec["max_dev_spaces"] = max(
                abs(f - m) for f, m in zip(fabricated, centres)) / spacing
        out.append(rec)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", nargs="*", default=DEFAULT_ROWS)
    ap.add_argument("--engraved", nargs="*", default=DEFAULT_ENGRAVED)
    ap.add_argument("--dpi", type=int, default=600,
                    help="`transcribe`'s own default (transcribe.py:4027), "
                         "which is what orchestral_eval takes.")
    args = ap.parse_args()
    index = {r["row_id"]: r for r in json.loads(ROWS.read_text())["rows"]}
    jobs = [(rid, LIB / index[rid]["edition"]["catalog_path"],
             index[rid]["page"]["pdf_page_index"], "scan") for rid in args.rows]
    jobs += [(f"{w} (ENGRAVED)", FIXTURES / f"{w}.pdf", 0, "engraved")
             for w in args.engraved]
    allrecs = []
    for rid, pdf, pi, family in jobs:
        if not pdf.exists():
            print(f"  !! missing {pdf}", file=sys.stderr)
            continue
        page = render_page(pdf, pi, dpi=args.dpi)
        cells = extract_measures(detect_barlines(detect_staves(page)))
        cells = remove_staff_lines(cells)
        recs = [r for c in cells for r in census_cell(c)]
        for r in recs:
            r["row"] = rid
            r["family"] = family
        allrecs += recs
        multi = [r for r in recs if r["n_bars"] >= 2]
        print(f"\n=== {rid}  page {pi}  cells {len(cells)}")
        print(f"  accepted beam components      {len(recs)}")
        print(f"  ... multi-bar (n_bars >= 2)   {len(multi)}"
              f"  = {len(multi)/max(1,len(recs)):.3f}")
        devs = [r["max_dev_spaces"] for r in multi if "max_dev_spaces" in r]
        if devs:
            devs.sort()
            over = sum(1 for d in devs if d > 0.35)
            print(f"  fabricated vs MEASURED bar centre, max deviation per component:")
            print(f"      n={len(devs)}  median {st.median(devs):.3f} sp"
                  f"  p90 {devs[int(.9*len(devs))-1]:.3f}  max {devs[-1]:.3f}")
            print(f"      OVER the 0.35-space clustering tolerance: {over}"
                  f"  = {over/len(devs):.3f}")
        dis = [r for r in multi if not r["agree"]]
        print(f"  columns disagreed with the median count: {len(dis)} of {len(multi)}")
        for lab, sel in (("1 bar", [r for r in recs if r["n_bars"] == 1]),
                         ("2+ bars", multi)):
            if sel:
                f = sorted(r["fill"] for r in sel)
                print(f"  box fill ratio, {lab:8s} n={len(sel):4d}"
                      f"  median {st.median(f):.3f}  p10 {f[int(.1*len(f))]:.3f}")
    out = ROOT / "benchmarks/omr-pipeline-audit-2026-09/beam-bar-census.json"
    out.write_text(json.dumps(allrecs, indent=1))
    print(f"\nwrote {out.relative_to(ROOT)}  ({len(allrecs)} components)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
