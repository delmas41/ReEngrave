#!/usr/bin/env python3
"""Agent I — N4: the FABRICATED beam-bar coordinates, priced against the ones
the mask already holds, and against the clustering decision that consumes them.

THE MECHANISM.
  * `line_detection._stacked_bar_count` finds, per sampled column, the rows
    where ink STARTS (`cols & ~above`, `:374-376`). Those rows ARE the bars'
    positions. It reduces them to `median(count)` and throws them away.
  * `detect_beams:546` SYNTHESISES the positions instead: the component's box
    is cut into `n_bars` equal slices, `y_canonical = y + k*(h/n_bars)`,
    `height = h // n_bars`.
  * `rhythm._beams_attached_to_stem` then clusters beam y-CENTRES at
    `BEAM_Y_CLUSTER_FACTOR (0.35) x staff spacing` to decide how many levels a
    stem carries — hence the note's duration.

So whenever `n_bars > 1` a duration is decided by clustering coordinates nobody
measured. THE QUESTION THAT DECIDES WHETHER IT MATTERS is not whether the
coordinates differ, it is whether the difference crosses the cluster tolerance:

    fabricated gaps are all h/n by construction  -> levels = n if h/n > tol else 1
    measured gaps vary                           -> levels = 1 + #(gap > tol)

A displacement under the tolerance is a real defect with zero consequence; one
over it changes a duration.

⚠️ SAMPLING IS THE WHOLE RESULT HERE. An earlier run of this probe covered two
`p1` rows — the two cleanest prints in the gate — found 0 of 277 multi-bar
components, and was written up as "unreachable". It was a biased sample, not a
null: every hit in the corpus is on a p2/p3/p4/p6 row or on Bach. The default
row set below is therefore THE WHOLE 20-ROW GATE plus every engraved fixture.

⚠️ FIXTURES LIVE IN THE MAIN CHECKOUT ONLY (`library/` and the
`omr-orchestral-e2e/fixtures/` build products are gitignored), so a worktree
cannot resolve them relatively. `OMR_FIXTURE_ROOT` names the checkout; a
missing input or an empty census is a NON-ZERO EXIT, never a clean all-zero
table. A probe that reports "nothing found" when it means "I looked in the
wrong place" is this audit's own recurring failure.

    OMR_FIXTURE_ROOT=/path/to/ReEngrave python3 .../probe_beam_bar_positions.py
"""
from __future__ import annotations
import argparse, json, os, statistics as st, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import cv2, numpy as np  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.measure_extractor import detect_barlines, extract_measures  # noqa: E402
from tools.omr.staff_line_removal import remove_staff_lines  # noqa: E402
from tools.omr import line_detection as ld  # noqa: E402
from tools.omr.rhythm import BEAM_Y_CLUSTER_FACTOR  # noqa: E402

#: The checkout holding `library/` and the engraved fixtures. Both are
#: gitignored build products / large binaries, so they exist in ONE place.
FIXTURE_ROOT = Path(os.environ.get(
    "OMR_FIXTURE_ROOT", "/Users/seanjohnson/Desktop/ReEngrave"))
ROWS_JSON = ROOT / "benchmarks/omr-scan-e2e-2026-09/works.json"


def measured_bar_rows(labels, label, x, y, w, h, max_samples=48):
    """The bars' MEASURED centre rows and extents — what `_stacked_bar_count`
    computes and discards. Mirrors its sampling exactly, then keeps the runs.

    Returns `(n_bars_median, [(centre, top, bottom) per bar], n_disagreeing)`
    or `(n, None, d)` where no column agrees with the median count.
    """
    roi = labels[y:y + h, x:x + w] == label
    if roi.size == 0:
        return 1, None, 0
    step = max(1, roi.shape[1] // max_samples)
    cols = roi[:, ::step]
    above = np.vstack([np.zeros((1, cols.shape[1]), dtype=bool), cols[:-1]])
    starts = cols & ~above
    counts = starts.sum(axis=0)
    nz = counts[counts > 0]
    if nz.size == 0:
        return 1, None, 0
    n = max(1, int(np.median(nz)))
    good = [c for c in range(cols.shape[1]) if counts[c] == n]
    disagree = int((nz != n).sum())
    if not good:
        return n, None, disagree
    per_bar = [[] for _ in range(n)]
    for c in good:
        rows = np.flatnonzero(starts[:, c])
        for k, r0 in enumerate(rows[:n]):
            nxt = rows[k + 1] if k + 1 < len(rows) else cols.shape[0]
            run = cols[r0:nxt, c]
            run_len = int(np.argmin(run)) if (~run).any() else int(nxt - r0)
            per_bar[k].append((r0, run_len))
    bars = []
    for v in per_bar:
        if not v:
            return n, None, disagree
        r0 = float(np.mean([a for a, _ in v]))
        rl = float(np.mean([b for _, b in v]))
        bars.append((y + r0 + rl / 2.0, y + r0, y + r0 + rl))
    return n, bars, disagree


def _levels(centres, tol):
    """`rhythm._beams_attached_to_stem._count`, exactly: a new level wherever
    two sorted centres are more than `tol` apart."""
    ys = sorted(centres)
    return 1 + sum(1 for i in range(1, len(ys)) if ys[i] - ys[i - 1] > tol)


def census_cell(cell):
    src = cell.image_no_staff if cell.image_no_staff is not None else cell.image
    if src is None or src.size == 0:
        return []
    spacing = ld._staff_line_spacing(cell)
    if spacing <= 1.0:
        return []
    tol = spacing * BEAM_Y_CLUSTER_FACTOR
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
        rec = {"n_bars": int(n_bars), "fill": float(area) / max(1, w * h),
               "h_spaces": h / spacing, "w_spaces": w / spacing,
               "spacing": float(spacing), "tol_spaces": BEAM_Y_CLUSTER_FACTOR}
        if n_bars >= 2:
            n_meas, bars, disagree = measured_bar_rows(labels, i, x, y, w, h)
            rec["col_disagreements"] = disagree
            rec["counts_agree"] = bool(n_meas == n_bars and bars)
            sub_h = max(1, h // n_bars)
            fab = [(y + k * (h / n_bars) + sub_h // 2,
                    y + k * (h / n_bars),
                    y + k * (h / n_bars) + sub_h) for k in range(n_bars)]
            rec["fab_centres"] = [round(c, 2) for c, _, _ in fab]
            # what a level count on THIS component alone resolves to
            rec["levels_fab"] = _levels([c for c, _, _ in fab], tol)
            if bars and n_meas == n_bars:
                rec["meas_centres"] = [round(c, 2) for c, _, _ in bars]
                rec["max_dev_spaces"] = max(
                    abs(f[0] - m[0]) for f, m in zip(fab, bars)) / spacing
                rec["levels_meas"] = _levels([c for c, _, _ in bars], tol)
                rec["level_flip"] = rec["levels_fab"] != rec["levels_meas"]
                rec["gap_fab_spaces"] = (h / n_bars) / spacing
                rec["gaps_meas_spaces"] = [
                    round((bars[k + 1][0] - bars[k][0]) / spacing, 3)
                    for k in range(n_bars - 1)]
                # band displacement, which decides the end-window assignment
                rec["max_band_dev_spaces"] = max(
                    max(abs(f[1] - m[1]), abs(f[2] - m[2]))
                    for f, m in zip(fab, bars)) / spacing
        out.append(rec)
    return out


def run_page(pdf: Path, page_index: int, dpi: int):
    page = render_page(pdf, page_index, dpi=dpi)
    cells = remove_staff_lines(extract_measures(detect_barlines(detect_staves(page))))
    return cells, [r for c in cells for r in census_cell(c)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", nargs="*", default=None,
                    help="scan row_ids; default = the whole 20-row gate")
    ap.add_argument("--engraved", nargs="*", default=None,
                    help="fixture stems; default = every fixture present")
    ap.add_argument("--dpi", type=int, default=600,
                    help="transcribe.py:4027's default, which orchestral_eval takes")
    args = ap.parse_args()

    if not FIXTURE_ROOT.is_dir():
        print(f"FATAL: OMR_FIXTURE_ROOT does not exist: {FIXTURE_ROOT}",
              file=sys.stderr)
        return 2
    lib = FIXTURE_ROOT / "library"
    fixtures = FIXTURE_ROOT / "benchmarks/omr-orchestral-e2e/fixtures"
    rows = {r["row_id"]: r for r in json.loads(ROWS_JSON.read_text())["rows"]}
    want_rows = args.rows if args.rows is not None else list(rows)
    jobs = [(rid, lib / rows[rid]["edition"]["catalog_path"],
             rows[rid]["page"]["pdf_page_index"], "scan") for rid in want_rows]
    stems = (args.engraved if args.engraved is not None
             else sorted(p.stem for p in fixtures.glob("*.pdf")))
    jobs += [(f"{s} (ENGRAVED)", fixtures / f"{s}.pdf", 0, "engraved")
             for s in stems]

    missing = [str(p) for _r, p, _i, _f in jobs if not p.exists()]
    if missing or not jobs:
        print(f"FATAL: {len(missing)} input(s) missing under {FIXTURE_ROOT}; "
              f"set OMR_FIXTURE_ROOT to the checkout that holds library/ and "
              f"benchmarks/omr-orchestral-e2e/fixtures/", file=sys.stderr)
        for m in missing[:5]:
            print(f"  {m}", file=sys.stderr)
        return 2

    allrecs = []
    for rid, pdf, pi, family in jobs:
        cells, recs = run_page(pdf, pi, args.dpi)
        for r in recs:
            r["row"], r["family"] = rid, family
        allrecs += recs
        multi = [r for r in recs if r["n_bars"] >= 2]
        flips = [r for r in multi if r.get("level_flip")]
        print(f"{rid:38s} cells {len(cells):4d}  components {len(recs):4d}"
              f"  multi-bar {len(multi):3d}  level-flips {len(flips):3d}",
              flush=True)

    if not allrecs:
        print("FATAL: 0 beam components over the whole job set — that is an "
              "instrument failure, not a result.", file=sys.stderr)
        return 2

    multi = [r for r in allrecs if r["n_bars"] >= 2]
    print(f"\n=== {len(allrecs)} accepted beam components, "
          f"{len(multi)} multi-bar ({len(multi)/len(allrecs):.4f})")
    if not multi:
        print("no multi-bar components in this sample — the fabrication branch "
              "did not execute. THAT IS A STATEMENT ABOUT THIS SAMPLE.")
    else:
        agree = [r for r in multi if r.get("counts_agree")]
        # ⚠️ TWO DIFFERENT QUANTITIES, and an earlier version of this probe
        # labelled the first as if it were the second. `agree` counts
        # COMPONENTS whose measured run-count equals `_stacked_bar_count`'s;
        # `col_disagreements` counts SAMPLED COLUMNS that differ from their own
        # component's median.
        print(f"  components whose MEASURED count matches _stacked_bar_count: "
              f"{len(agree)}/{len(multi)}")
        print(f"  sampled COLUMNS differing from their component's median: "
              f"{sum(r.get('col_disagreements', 0) for r in multi)}")
        devs = sorted(r["max_dev_spaces"] for r in agree if "max_dev_spaces" in r)
        if devs:
            print(f"  FABRICATED vs MEASURED bar centre, max per component:")
            print(f"      n={len(devs)}  median {st.median(devs):.3f} sp"
                  f"  p90 {devs[int(.9*len(devs))-1]:.3f}  max {devs[-1]:.3f}")
            print(f"      over the {BEAM_Y_CLUSTER_FACTOR} sp cluster tolerance: "
                  f"{sum(1 for d in devs if d > BEAM_Y_CLUSTER_FACTOR)}")
        bands = sorted(r["max_band_dev_spaces"] for r in agree
                       if "max_band_dev_spaces" in r)
        if bands:
            print(f"  band edge displacement: median {st.median(bands):.3f} sp"
                  f"  max {bands[-1]:.3f}")
        flips = [r for r in agree if r.get("level_flip")]
        print(f"  ⚠️ LEVEL-COUNT FLIPS (the fabrication changes how many beam")
        print(f"     levels this component resolves to): {len(flips)}"
              f" of {len(agree)}  = {len(flips)/max(1,len(agree)):.3f}")
        for r in flips[:8]:
            print(f"        {r['row']:34s} n_bars {r['n_bars']}"
                  f"  fab {r['levels_fab']} -> meas {r['levels_meas']}"
                  f"  gap_fab {r['gap_fab_spaces']:.3f} sp"
                  f"  gaps_meas {r['gaps_meas_spaces']}")
    out = ROOT / "benchmarks/omr-pipeline-audit-2026-09/beam-bar-census.json"
    out.write_text(json.dumps(allrecs, indent=1))
    print(f"\nwrote {out.relative_to(ROOT)}  ({len(allrecs)} components)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
