"""How far the FABRICATED beam bands sit from the measured ones, and what it costs.

`detect_beams` used to place a stacked component's bars by dividing its
bounding box into `n_bars` equal slices. This walks the same component loop
over real pages and computes BOTH placements, then asks the only question that
decides whether the difference matters: does the beam-LEVEL count change, since
a level is a note's duration.

    python3 benchmarks/omr-beam-bar-bands-2026-09/probe_bar_placement.py --scans
    python3 benchmarks/omr-beam-bar-bands-2026-09/probe_bar_placement.py --engraved
    python3 benchmarks/omr-beam-bar-bands-2026-09/probe_bar_placement.py --all

⚠️ THIS PROBE MUST FAIL LOUDLY, and the reason is in this defect's own history.
The finding was RETRACTED once on a census that returned a clean `n_bars == 1`
everywhere — from a biased sample of two pages, both of them `p1` rows, the two
cleanest prints in the gate. A probe that prints zeros at exit 0 from the wrong
tree is indistinguishable from a probe that found nothing. So:

  * every input is resolved from `__file__`, never from the CWD;
  * gitignored engraved fixtures come from `OMR_FIXTURE_ROOT` (default: the
    main checkout's build directory), and a missing one is named, not skipped;
  * an empty or short input set EXITS NON-ZERO before measuring anything.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.omr.line_detection import (  # noqa: E402
    _attached_stem_count, _binary_ink, _staff_line_spacing, _stacked_bar_bands,
    LineDetection, detect_stems,
)
from tools.omr.measure_extractor import (  # noqa: E402
    detect_barlines, extract_measures, majority_bars_by_system,
    resegment_fused_measures,
)
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.rhythm import BEAM_Y_CLUSTER_FACTOR, _beams_attached_to_stem  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.staff_line_removal import remove_staff_lines  # noqa: E402

SCAN_ROWS = REPO / "benchmarks/omr-scan-e2e-2026-09/works.json"
LIBRARY = Path(
    os.environ.get("OMR_LIBRARY_ROOT", "/Users/seanjohnson/Desktop/ReEngrave/library")
)
FIXTURES = Path(
    os.environ.get(
        "OMR_FIXTURE_ROOT",
        "/Users/seanjohnson/Desktop/ReEngrave/benchmarks/omr-orchestral-e2e/fixtures",
    )
)
# The same eleven the engraved benchmark pools. Named, so a missing one is a
# reported absence rather than a silently smaller corpus.
ENGRAVED = [
    "beethoven-sym3-mvt1", "beethoven-sym5-mvt1", "brahms-sym1-mvt1",
    "brahms-sym4-mvt1", "bruckner-sym5-mvt1", "dvorak-sym9-mvt4",
    "mahler-sym5-mvt1", "mozart-sym40-mvt1", "mozart-sym41-mvt1",
    "tchaikovsky-sym4-mvt2", "tchaikovsky-sym6-mvt2",
]


def die(msg: str) -> None:
    print(f"FATAL: {msg}", file=sys.stderr)
    raise SystemExit(2)


def scan_pages() -> list[tuple[str, Path, int]]:
    if not SCAN_ROWS.is_file():
        die(f"scan gate rows not found: {SCAN_ROWS}")
    rows = json.loads(SCAN_ROWS.read_text())
    rows = rows["rows"] if isinstance(rows, dict) and "rows" in rows else rows
    out, missing = [], []
    for r in rows:
        pdf = LIBRARY / r["edition"]["catalog_path"]
        if not pdf.is_file():
            missing.append(f"{r['row_id']} -> {pdf}")
            continue
        out.append((r["row_id"], pdf, int(r["page"]["pdf_page_index"])))
    if missing:
        print(f"WARN: {len(missing)} scan rows have no PDF:", file=sys.stderr)
        for m in missing:
            print(f"  {m}", file=sys.stderr)
    if len(out) < len(rows):
        die(f"only {len(out)} of {len(rows)} scan rows resolved — refusing a partial gate")
    return out


def engraved_pages() -> list[tuple[str, Path, int]]:
    out, missing = [], []
    for name in ENGRAVED:
        pdf = FIXTURES / f"{name}.pdf"
        (out if pdf.is_file() else missing).append(
            (name, pdf, 0) if pdf.is_file() else f"{name} -> {pdf}"
        )
    if missing:
        print(f"WARN: {len(missing)} engraved fixtures absent "
              f"(regenerate with orchestral_eval):", file=sys.stderr)
        for m in missing:
            print(f"  {m}", file=sys.stderr)
    if not out:
        die(f"no engraved fixtures under {FIXTURES} — set OMR_FIXTURE_ROOT")
    return out


def cells_for(pdf: Path, page_index: int, dpi: int):
    page = render_page(pdf, page_index, dpi=dpi)
    pws = detect_barlines(detect_staves(page))
    cells = extract_measures(pws)
    cells = resegment_fused_measures(
        pws, cells, expected_bars_by_system=majority_bars_by_system(cells))
    remove_staff_lines(cells)
    return cells


def _beam(x, y, w, h) -> LineDetection:
    return LineDetection(smufl_name="beam", category="structural",
                         x_canonical=int(x), y_canonical=int(y),
                         width_canonical=int(w), height_canonical=int(h),
                         confidence=1.0)


def probe_cell(cell) -> dict:
    """Both placements for one cell, plus the level counts each produces."""
    src = cell.image_no_staff if cell.image_no_staff is not None else cell.image
    if src is None or src.size == 0:
        return {}
    spacing = _staff_line_spacing(cell)
    if spacing <= 1.0:
        return {}
    stems = detect_stems(cell)
    ink = _binary_ink(src)
    kernel_w = max(3, int(round(spacing * 1.5)))
    opened = cv2.morphologyEx(
        ink, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_w, 1)))
    num, labels, stats, _ = cv2.connectedComponentsWithStats(opened, connectivity=8)

    min_w = int(round(spacing * 1.5))
    min_h = max(2, int(round(spacing * 0.10)))
    max_h = max(3, int(round(spacing * 2.5)))
    tol, reach = spacing * 1.0, spacing * 2.5
    anchors = [s for s in stems if s.height_canonical >= spacing * 2.8]

    old, new, multi = [], [], []
    for i in range(1, num):
        x, y, w, h, area = (int(v) for v in stats[i][:5])
        if w < min_w or h < min_h or h > max_h or area < max(6, spacing):
            continue
        if w / max(1, h) < 2.0:
            continue
        if _attached_stem_count(labels, i, anchors, x, y, w, h,
                                spacing, tol, reach) < 2:
            continue
        n_bars, bands = _stacked_bar_bands(labels, i, x, y, w, h)
        sub_h = max(1, h // n_bars)
        o = [(int(y + k * (h / n_bars)), int(sub_h)) for k in range(n_bars)]
        n = o if bands is None else [(int(y + t), max(1, int(b - t + 1)))
                                     for t, b in bands]
        old += [_beam(x, py, w, ph) for py, ph in o]
        new += [_beam(x, py, w, ph) for py, ph in n]
        if n_bars > 1:
            multi.append({
                "n_bars": n_bars, "box": [x, y, w, h], "spacing": spacing,
                "measured": bands is not None,
                "old": o, "new": n,
                "d_centre": [abs((o[k][0] + o[k][1] // 2) - (n[k][0] + n[k][1] // 2))
                             / spacing for k in range(n_bars)],
                "d_edge": [abs(o[k][0] - n[k][0]) / spacing for k in range(n_bars)],
            })

    cluster_tol = spacing * BEAM_Y_CLUSTER_FACTOR
    changed = []
    for s in stems:
        lo = _beams_attached_to_stem(s, old, cluster_tol)
        ln = _beams_attached_to_stem(s, new, cluster_tol)
        if lo != ln:
            changed.append({"stem": [s.x_canonical, s.y_canonical,
                                     s.height_canonical], "old": lo, "new": ln})
    return {"n_components": len([b for b in old]), "multi": multi,
            "level_changes": changed}


def run(pages, dpi: int, tag: str) -> dict:
    tot_comp = tot_multi = 0
    all_multi, all_changes = [], []
    for row_id, pdf, pidx in pages:
        try:
            cells = cells_for(pdf, pidx, dpi)
        except Exception as exc:                       # noqa: BLE001
            die(f"{row_id}: page {pidx} of {pdf} failed to render: {exc!r}")
        n_c = n_m = 0
        for cell in cells:
            r = probe_cell(cell)
            if not r:
                continue
            n_c += r["n_components"]
            n_m += len(r["multi"])
            for m in r["multi"]:
                m["row"] = row_id
                all_multi.append(m)
            for c in r["level_changes"]:
                c["row"] = row_id
                all_changes.append(c)
        tot_comp += n_c
        tot_multi += n_m
        print(f"  {row_id:38s} bars={n_c:5d}  multi-bar components={n_m:3d}")
    n_stacked_bars = sum(m["n_bars"] for m in all_multi)
    print(f"\n{tag}: {tot_comp} emitted bars from {tot_comp - n_stacked_bars + tot_multi} "
          f"components; {tot_multi} components read more than one bar and emit "
          f"{n_stacked_bars} of those bars; {len(all_changes)} STEMS change beam level")
    # ⚠️ That last figure is an UPPER BOUND on duration changes, not a count of
    # them. `rhythm` only calls `_beams_attached_to_stem` for a stem that
    # `_stem_for_notehead` matched to a notehead, so a spurious stem can change
    # its level without changing anything exported. `control_scan_durations.sh`
    # runs the real pipeline and is the figure to quote.
    if all_multi:
        dc = np.array([v for m in all_multi for v in m["d_centre"]])
        de = np.array([v for m in all_multi for v in m["d_edge"]])
        print(f"  displacement (staff spaces): centre median {np.median(dc):.3f} "
              f"max {dc.max():.3f} | edge median {np.median(de):.3f} max {de.max():.3f}")
        print(f"  over the 0.35 clustering tolerance: centre {(dc > 0.35).sum()}, "
              f"edge {(de > 0.35).sum()}")
    for c in all_changes:
        print(f"  LEVEL CHANGE {c['row']} stem@{c['stem']}: {c['old']} -> {c['new']}")
    return {"components": tot_comp, "multi": all_multi, "changes": all_changes}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scans", action="store_true")
    ap.add_argument("--engraved", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    if not (a.scans or a.engraved or a.all):
        die("pick --scans, --engraved or --all")

    result = {}
    if a.scans or a.all:
        print("=== SCAN GATE (20 rows, dpi %d) ===" % a.dpi)
        result["scans"] = run(scan_pages(), a.dpi, "SCANS")
    if a.engraved or a.all:
        print("\n=== ENGRAVED FIXTURES (11 works, dpi %d) ===" % a.dpi)
        result["engraved"] = run(engraved_pages(), a.dpi, "ENGRAVED")
    if a.out:
        a.out.write_text(json.dumps(result, indent=1, default=float))
        print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
