#!/usr/bin/env python3
"""Agent I, round 4 — what `binarize`'s 25-PIXEL window spans, at each live DPI.

⚠️ `threshold_sauvola` REFUSES AN EVEN WINDOW on any dimension, so the
DPI-scaled comparison below uses 51, not 50. Anyone proposing a
`window_size = f(dpi)` rule has to round to odd or it raises at run time —
found here by the probe crashing, and worth knowing before a fix is written.

THE SUSPICION (architecture map, stage 1): `preprocessing.binarize` calls
`threshold_sauvola(gray, window_size=25, k=0.2)`. 25 is a PIXEL constant in a
pipeline whose house style scales everything by staff spacing — and `OMR_DPI`
legitimately runs at 300 (container default) and 600 (CLI default, and
`transcribe.py`'s own), DELIBERATELY, because 300 wins on sparse authored
fixtures and 600 on dense orchestral pages. So both regimes are live and the
window means different things in each.

THREE MEASUREMENTS, in increasing directness:

  A. what 25 px SPANS, in staff spaces and in staff-line thicknesses, at each
     DPI on real pages;
  B. the CONTROL that makes A trustworthy — spacing must scale ~2.0x from 300
     to 600, because it is a physical distance times dpi/72. If it does not,
     the geometry measurement is itself unstable and A cannot be read;
  C. the DIRECT experiment, which needs no staff detection at all: binarise the
     SAME 600-dpi raster at window 25 (what ships) and at window 50 (the
     DPI-scaled equivalent of 25-at-300) and measure how much of the page gets
     a different verdict, and where.

⚠️ MEASURING STAGE 1 IS UNAVOIDABLY MEASURING ITS OUTPUT. There is no earlier
artefact. What this probe does NOT do is read the final page dict: A/B read the
binary raster and the staff geometry directly, and C reads only rasters. Where
a number depends on `detect_staves` — which consumes the binary this stage
produced — it is marked (downstream) and B is the control for it.

⚠️ NO FIX IS PROPOSED. Binarisation is upstream of literally everything; a
change here needs its own A/B on both families.

    python3 .../probe_sauvola_dpi_scale.py [--dpis 300 600] [--pages N]
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2                      # noqa: E402
import fitz                     # noqa: E402
import numpy as np              # noqa: E402
from skimage.filters import threshold_sauvola   # noqa: E402

from _fixtureroot import fixture_root, require_nonempty   # noqa: E402
from tools.omr.preprocessing import binarize              # noqa: E402
from tools.omr.staff_detector import detect_staves        # noqa: E402
from tools.omr.types import PageImage                     # noqa: E402

ROOT = fixture_root(Path("/Users/seanjohnson/Desktop/ReEngrave"))

#: Two scanned editions (different publishers, different rasters) and two
#: engraved fixtures. The engraved half matters: a LilyPond page is vector
#: source, so its staff spacing at a given DPI is whatever the renderer chose,
#: and it is the family where 300 was measured to win.
#: ⚠️ PART D — THE POPULATION THE BENCHMARKS DO NOT CONTAIN. Every one of the
#: 20 scan-gate rows is a BITONAL raster (ccitt/jbig2, `works.json`'s own
#: `raster` field), so an adaptive threshold has nothing to adapt to on any of
#: them and any window gives the same answer. A full census of the score
#: library finds 48 of 289 editions (16.6%) are 8-bit. These are four of them,
#: and they are where the window's scale actually decides something.
GREYSCALE_PAGES = [
    ("grey-beethoven9-schott-1826", "library/editions/beethoven/symphony-9-op125/"
     "beethoven--symphony-9-op125--schott-1826--imslp46254.pdf", 4),
    ("grey-beethoven7-steiner-1816", "library/editions/beethoven/symphony-7-op92/"
     "beethoven--symphony-7-op92--s-a-steiner-co-1816--imslp46251.pdf", 4),
    ("grey-haydn100-breitkopf-1857", "library/editions/haydn/"
     "symphony-100-in-g-major-hob-i-100/"
     "haydn--symphony-100-in-g-major-hob-i-100--breitkopf-und-hartel-1857--imslp546542.pdf", 4),
    ("grey-brahms-tragic-simrock-1881", "library/editions/brahms/tragic-overture-op81/"
     "brahms--tragic-overture-op81--simrock-1881--imslp23111.pdf", 4),
]

PAGES = [
    ("scan-beethoven5-litolff-p1", "library/editions/beethoven/symphony-5-op67/"
     "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf", 1),
    ("scan-brahms1-breitkopf-p1", "library/editions/brahms/symphony-1-op68/"
     "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf", 0),
    ("engraved-brahms1", "benchmarks/omr-orchestral-e2e/fixtures/brahms-sym1-mvt1.pdf", 0),
    ("engraved-mozart41", "benchmarks/omr-orchestral-e2e/fixtures/mozart-sym41-mvt1.pdf", 0),
]


def raw_rgb(pdf: Path, page_index: int, dpi: int) -> np.ndarray:
    """`render_page`'s render step ALONE — same channel dispatch, no binarise,
    no deskew. Needed because `render_page` bakes binarisation in."""
    doc = fitz.open(pdf)
    try:
        pix = doc[page_index].get_pixmap(dpi=dpi, alpha=False)
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n)
        if pix.n == 1:
            return cv2.cvtColor(arr, cv2.COLOR_GRAY2RGB)
        if pix.n == 3:
            return arr.copy()
        if pix.n == 4:
            return cv2.cvtColor(arr, cv2.COLOR_RGBA2RGB)
        raise RuntimeError(f"unexpected channel count {pix.n}")
    finally:
        doc.close()


def run_stats(binary: np.ndarray, axis: int) -> list[int]:
    """Lengths of contiguous ink runs along `axis`. Ink is 0, paper 255.

    A stroke's thickness is what a too-small threshold window distorts, so this
    is the quantity the window has to be commensurate with.
    """
    ink = binary == 0
    if axis == 1:
        ink = ink.T
    out: list[int] = []
    # sample every 16th line — a full census is not needed for a median
    for i in range(0, ink.shape[1], 16):
        col = ink[:, i]
        if not col.any():
            continue
        d = np.diff(col.astype(np.int8))
        starts = np.flatnonzero(d == 1) + 1
        ends = np.flatnonzero(d == -1) + 1
        if col[0]:
            starts = np.r_[0, starts]
        if col[-1]:
            ends = np.r_[ends, col.size]
        n = min(len(starts), len(ends))
        out.extend((ends[:n] - starts[:n]).tolist())
    return out


def geometry(rgb: np.ndarray, dpi: int, pdf: Path, page_index: int):
    """(downstream) staff spacing and line thickness — needs `detect_staves`,
    which consumes the binary this stage produced. Control B checks it."""
    binary = binarize(rgb)
    page = PageImage(pdf_path=pdf, page_index=page_index, dpi=dpi,
                     rgb=rgb, binary=binary, skew_correction_deg=0.0)
    pws = detect_staves(page)
    sp = [s.line_spacing_px for s in pws.staves if s.line_spacing_px > 0]
    th = [s.median_line_thickness_px for s in pws.staves
          if s.median_line_thickness_px]
    return (len(pws.staves),
            st.median(sp) if sp else None,
            st.median(th) if th else None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dpis", type=int, nargs="*", default=[300, 600])
    ap.add_argument("--window", type=int, default=25)
    args = ap.parse_args()

    jobs = require_nonempty(
        [(n, ROOT / r, p) for n, r, p in PAGES if (ROOT / r).is_file()],
        "stage-1 input PDFs", ROOT, "PAGES")
    if len(jobs) < len(PAGES):
        missing = [n for n, r, _ in PAGES if not (ROOT / r).is_file()]
        print(f"WARNING: {len(missing)} page(s) unresolved: {missing}",
              file=sys.stderr)

    W = args.window
    rows = []
    print("=== A + B — what a 25-px window spans, and does spacing scale?  "
          "(spacing/thickness are DOWNSTREAM of binarize)\n")
    print(f"{'page':30s}{'dpi':>5s}{'staves':>7s}{'spacing':>9s}"
          f"{'thick':>7s}{'W/space':>9s}{'W/thick':>9s}")
    per_page: dict[str, dict[int, tuple]] = {}
    for name, pdf, pi in jobs:
        for dpi in args.dpis:
            rgb = raw_rgb(pdf, pi, dpi)
            n, sp, th = geometry(rgb, dpi, pdf, pi)
            per_page.setdefault(name, {})[dpi] = (n, sp, th)
            f_sp = f"{W/sp:9.2f}" if sp else "        -"
            f_th = f"{W/th:9.2f}" if th else "        -"
            print(f"{name:30s}{dpi:5d}{n:7d}"
                  f"{(sp if sp else float('nan')):9.2f}"
                  f"{(th if th else float('nan')):7.2f}{f_sp}{f_th}")
            rows.append({"page": name, "dpi": dpi, "n_staves": n,
                         "spacing_px": sp, "thickness_px": th,
                         "window_in_spaces": (W / sp) if sp else None,
                         "window_in_thicknesses": (W / th) if th else None})
    print("\n  CONTROL B — spacing must scale ~2.0x from 300 to 600:")
    for name, d in per_page.items():
        if 300 in d and 600 in d and d[300][1] and d[600][1]:
            r = d[600][1] / d[300][1]
            flag = "" if 1.9 <= r <= 2.1 else "   <== NOT ~2.0, geometry unstable"
            print(f"    {name:30s} {d[300][1]:.2f} -> {d[600][1]:.2f}"
                  f"  ratio {r:.3f}{flag}")

    print("\n=== C — the DIRECT experiment: same 600-dpi raster, window 25 vs 50"
          "  (no staff detection anywhere)\n")
    print(f"{'page':30s}{'ink@25':>9s}{'ink@50':>9s}{'pixels':>9s}"
          f"{'differ':>9s}{'medrun25':>10s}{'medrun50':>10s}")
    for name, pdf, pi in jobs:
        rgb = raw_rgb(pdf, pi, 600)
        b25 = binarize(rgb, window_size=W)
        # 2W+1, not 2W: skimage refuses an even window on any dimension.
        b50 = binarize(rgb, window_size=W * 2 + 1)
        ink25 = float((b25 == 0).mean())
        ink50 = float((b50 == 0).mean())
        differ = float((b25 != b50).mean())
        r25, r50 = run_stats(b25, 0), run_stats(b50, 0)
        m25 = st.median(r25) if r25 else float("nan")
        m50 = st.median(r50) if r50 else float("nan")
        print(f"{name:30s}{ink25:9.4f}{ink50:9.4f}{b25.size:9d}"
              f"{differ:9.4f}{m25:10.1f}{m50:10.1f}")
        rows.append({"page": name, "dpi": 600, "experiment": "window_25_vs_50",
                     "ink_25": ink25, "ink_50": ink50,
                     "pixels_disagreeing": differ,
                     "median_vertical_run_25": m25,
                     "median_vertical_run_50": m50})

    print("\n=== D — the same experiment on GREYSCALE scans, which no benchmark"
          " holds\n")
    grey = require_nonempty(
        [(n, ROOT / r, p) for n, r, p in GREYSCALE_PAGES if (ROOT / r).is_file()],
        "greyscale edition PDFs", ROOT, "GREYSCALE_PAGES")
    print(f"{'page':34s}{'dpi':>5s}{'greys':>7s}{'ink@25':>9s}{'ink@51':>9s}"
          f"{'differ':>9s}{'run25':>7s}{'run51':>7s}")
    for name, pdf, pi in grey:
        for dpi in args.dpis:
            rgb = raw_rgb(pdf, pi, dpi)
            g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
            levels = int((np.bincount(g.ravel(), minlength=256)
                          > g.size * 1e-5).sum())
            b25 = binarize(rgb, window_size=W)
            b51 = binarize(rgb, window_size=W * 2 + 1)
            r25, r51 = run_stats(b25, 0), run_stats(b51, 0)
            m25 = st.median(r25) if r25 else float("nan")
            m51 = st.median(r51) if r51 else float("nan")
            print(f"{name:34s}{dpi:5d}{levels:7d}{(b25 == 0).mean():9.4f}"
                  f"{(b51 == 0).mean():9.4f}{(b25 != b51).mean():9.4f}"
                  f"{m25:7.1f}{m51:7.1f}")
            rows.append({"page": name, "dpi": dpi, "experiment": "greyscale_25_vs_51",
                         "grey_levels": levels,
                         "ink_25": float((b25 == 0).mean()),
                         "ink_51": float((b51 == 0).mean()),
                         "pixels_disagreeing": float((b25 != b51).mean()),
                         "median_vertical_run_25": m25,
                         "median_vertical_run_51": m51})
            del rgb, g, b25, b51

    out = REPO / "benchmarks/omr-pipeline-audit-2026-09/sauvola-dpi-scale.json"
    out.write_text(json.dumps(rows, indent=1))
    print(f"\nwrote {out.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
