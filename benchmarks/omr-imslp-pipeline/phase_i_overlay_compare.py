#!/usr/bin/env python3
"""Phase I — side-by-side OLD vs NEW homography overlay for ONE page.

The Phase H runs failed in part because the catalog labels carried a
~30-60 px x-offset that shifted the model's spatial priors. Phase I
restructures the homography in phase_e_emit_labels.py to anchor on the
*music-start* x (not the cell's raw left edge) for system-first cells.

This helper renders the OLD vs NEW warped element overlays for a single
PDF page so we can visually confirm the alignment shift on the worst
cases (B1 imslp-52848 mvt 1 p007 or p008) before kicking off the full
Phase G batch re-emit (~10 minutes).

Usage:
  python3 benchmarks/omr-imslp-pipeline/phase_i_overlay_compare.py
      --page 8 --work beethoven-symphony-1 --edition imslp-52848 --mvt 1
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks/omr-imslp-pipeline"))

from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.measure_extractor import extract_measures  # noqa: E402

import phase_e_emit_labels as pe  # noqa: E402


DATA_ROOT = Path("/Users/seanjohnson/Desktop/ReEngrave/tools/omr/training/data/imslp")
OUT_BASE = ROOT / "benchmarks/omr-imslp-pipeline/phase-i-overlay"


def _color_for(dsv2_class: str) -> tuple[int, int, int]:
    if dsv2_class.startswith("notehead"):
        return (0, 0, 255)
    if "Clef" in dsv2_class or dsv2_class in ("gClef", "fClef", "cClef"):
        return (0, 200, 0)
    if dsv2_class == "barline":
        return (255, 0, 0)
    if dsv2_class.startswith("key"):
        return (200, 0, 200)
    if dsv2_class.startswith("timeSig"):
        return (255, 255, 0)
    if dsv2_class.startswith("accidental"):
        return (0, 200, 200)
    if dsv2_class.startswith("rest"):
        return (128, 0, 255)
    if dsv2_class.startswith("artic") or dsv2_class.startswith("fermata"):
        return (255, 128, 0)
    if dsv2_class.startswith("dynamic"):
        return (0, 255, 128)
    return (128, 128, 128)


def _draw_warped(img: np.ndarray, warped, label: str, banner_color):
    """Draw warped boxes onto img. Adds a top banner with label text."""
    for dsv2_class, cx, cy, w, h in warped:
        col = _color_for(dsv2_class)
        x0 = int(round(cx - w / 2)); y0 = int(round(cy - h / 2))
        x1 = int(round(cx + w / 2)); y1 = int(round(cy + h / 2))
        cv2.rectangle(img, (x0, y0), (x1, y1), col, 2)
    cv2.rectangle(img, (0, 0), (img.shape[1], 60), banner_color, -1)
    cv2.putText(img, label, (20, 42), cv2.FONT_HERSHEY_SIMPLEX, 1.2,
                (255, 255, 255), 2, cv2.LINE_AA)


def _warp_cell_old(cell, pdf_staff, msd):
    """Old (legacy) homography path — no music-start anchoring."""
    cx0, cy0, cx1, cy1 = cell.bbox_page_px
    H = pe.compute_homography_legacy(
        msd.staff_lines, cx0, cx1, list(pdf_staff.line_ys),
    )
    if H is None:
        return [], None
    warped = pe.warp_elements(
        msd.elements, H, pdf_staff_line_ys=list(pdf_staff.line_ys),
    )
    return warped, (cx0, cy0, cx1, cy1)


def _warp_cell_new(cell, pdf_staff, msd, page_binary):
    """New (Phase I) homography path with music-start anchors."""
    cx0, cy0, cx1, cy1 = cell.bbox_page_px
    is_sys_first = (cell.measure_index == 0)
    cell_binary = page_binary[cy0:cy1, cx0:cx1]
    local_ys = [int(y - cy0) for y in pdf_staff.line_ys]
    pdf_music_x = pe.detect_pdf_music_start_x(
        cell_binary, local_ys, cx0, is_sys_first,
    )
    if is_sys_first:
        v_start = pe.detect_verovio_music_start_x(msd)
        source_left_x = v_start if v_start is not None else float(msd.staff_lines[0][0])
    else:
        source_left_x = float(msd.staff_lines[0][0])
    source_right_x = float(msd.staff_lines[0][2])
    H = pe.compute_homography(
        msd.staff_lines,
        source_left_x, source_right_x,
        pdf_music_x, cx1,
        list(pdf_staff.line_ys),
    )
    if H is None:
        return [], None, pdf_music_x
    warped = pe.warp_elements(
        msd.elements, H, pdf_staff_line_ys=list(pdf_staff.line_ys),
    )
    return warped, (cx0, cy0, cx1, cy1), pdf_music_x


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="beethoven-symphony-1")
    ap.add_argument("--edition", default="imslp-52848")
    ap.add_argument("--mvt", type=int, default=1)
    ap.add_argument("--page", type=int, default=8,
                    help="1-indexed PDF page (default: 8 = worst-offset B1 page)")
    ap.add_argument("--out", default=None,
                    help="Output PNG (default: phase-i-overlay/{key}-p{NN}-compare.png)")
    args = ap.parse_args(argv)

    pdf = DATA_ROOT / args.work / "pdfs" / args.edition / "score.pdf"
    mxl = DATA_ROOT / args.work / "musicxml" / f"mvt-{args.mvt}.mxl"
    yml = DATA_ROOT / args.work / "pdfs" / args.edition / "movements.yaml"
    for p in (pdf, mxl, yml):
        if not p.exists():
            print(f"missing: {p}", file=sys.stderr)
            return 2

    movements = yaml.safe_load(yml.read_text())
    mvt_key = f"mvt_{args.mvt}"
    if mvt_key not in movements["movements"]:
        print(f"{mvt_key} not in {yml}", file=sys.stderr)
        return 2
    p_start, p_end = movements["movements"][mvt_key]["pages"]
    if not (p_start <= args.page <= p_end):
        print(f"WARNING: page {args.page} outside mvt range [{p_start}, {p_end}]")

    print(f"Loading Verovio cache for {mxl.name}...")
    cache = pe.VerovioCache(mxl)

    xml_staff_map = pe.build_pdf_xml_staff_map(mxl)
    print(f"PDF→XML staff map: {xml_staff_map}")

    print(f"Rendering PDF page {args.page}...")
    pi = render_page(pdf, args.page - 1, dpi=pe.PDF_DPI)
    pws = detect_staves(pi)
    cells = extract_measures(pws)
    print(f"  page {pi.width}×{pi.height}, "
          f"{len(pws.staves)} staves, {len(cells)} cells")

    if not cells:
        print("no cells extracted — nothing to compare", file=sys.stderr)
        return 1

    # Compute the same running_measure that process_movement would have at
    # the start of this page (sum of measures across prior pages of the mvt).
    running_measure = 0
    for prior_page in range(p_start, args.page):
        try:
            pi_prior = render_page(pdf, prior_page - 1, dpi=pe.PDF_DPI)
            pws_prior = detect_staves(pi_prior)
            cells_prior = extract_measures(pws_prior)
        except Exception as exc:  # noqa: BLE001
            print(f"  ! prior-page {prior_page} extract failed: {exc}")
            continue
        if not cells_prior:
            continue
        for sys_idx in sorted({c.system_index for c in cells_prior}):
            sys_cells_prior = [c for c in cells_prior if c.system_index == sys_idx]
            if sys_cells_prior:
                running_measure += max(c.measure_index for c in sys_cells_prior) + 1
    print(f"  running_measure at start of p{args.page} = {running_measure}")

    # Pick a SYSTEM-FIRST cell from the first system on this page.
    sys0 = min({c.system_index for c in cells})
    sys0_cells = [c for c in cells if c.system_index == sys0]
    first_staff = min(c.staff_index for c in sys0_cells)
    first_cell = next(
        (c for c in sys0_cells
         if c.staff_index == first_staff and c.measure_index == 0),
        None,
    )
    if first_cell is None:
        print("no system-first cell found", file=sys.stderr)
        return 1
    print(f"  picked cell: staff {first_cell.staff_index}, "
          f"system {first_cell.system_index}, "
          f"measure_index {first_cell.measure_index}, "
          f"bbox {first_cell.bbox_page_px}")

    staves_on_sys = sorted({c.staff_index for c in sys0_cells})
    staff_idx_within_system = staves_on_sys.index(first_cell.staff_index)
    xml_staff = xml_staff_map.get(staff_idx_within_system)
    if xml_staff is None:
        print(f"no XML staff for PDF staff position {staff_idx_within_system}",
              file=sys.stderr)
        return 1

    xml_n = str(running_measure + first_cell.measure_index + 1)
    hit = cache.find_measure(xml_n)
    if hit is None:
        print(f"XML measure {xml_n} not found", file=sys.stderr)
        return 1
    vpage, mid = hit
    svg = cache.svg(vpage)
    staves_data = pe.parse_measure_staves(svg, mid)
    if xml_staff >= len(staves_data):
        print(f"XML staff {xml_staff} out of range "
              f"(measure has {len(staves_data)} staves)", file=sys.stderr)
        return 1
    msd = staves_data[xml_staff]
    print(f"  matched XML measure n={xml_n} (verovio page {vpage}), "
          f"staff index {xml_staff}; {len(msd.elements)} elements")

    pdf_staff = next(
        (s for s in pws.staves if s.staff_index == first_cell.staff_index),
        None,
    )

    # WARP every system-first cell on every staff of every system, OLD + NEW
    page_warped_old: list = []
    page_warped_new: list = []
    music_xs: list[tuple[int, int, int, int]] = []  # (cx0, cx1, pdf_music_x, staff_idx)

    for sys_idx in sorted({c.system_index for c in cells}):
        sys_cells = [c for c in cells if c.system_index == sys_idx]
        staves_on_sys2 = sorted({c.staff_index for c in sys_cells})
        for pdf_staff_idx in staves_on_sys2:
            staff_pos = staves_on_sys2.index(pdf_staff_idx)
            x_staff = xml_staff_map.get(staff_pos)
            if x_staff is None:
                continue
            staff_cells = sorted(
                (c for c in sys_cells if c.staff_index == pdf_staff_idx),
                key=lambda c: c.measure_index,
            )
            if not staff_cells:
                continue
            # Compute system measure offset (running across systems on this page)
            local_running = running_measure
            for prior_sys in sorted({c.system_index for c in cells if c.system_index < sys_idx}):
                prior_sys_cells = [c for c in cells if c.system_index == prior_sys]
                local_running += max(c.measure_index for c in prior_sys_cells) + 1
            ps = next((s for s in pws.staves if s.staff_index == pdf_staff_idx), None)
            if ps is None:
                continue
            for cell in staff_cells:
                xml_n_c = str(local_running + cell.measure_index + 1)
                hit_c = cache.find_measure(xml_n_c)
                if hit_c is None:
                    continue
                vpage_c, mid_c = hit_c
                svg_c = cache.svg(vpage_c)
                staves_data_c = pe.parse_measure_staves(svg_c, mid_c)
                if x_staff >= len(staves_data_c):
                    continue
                msd_c = staves_data_c[x_staff]
                warp_old, _ = _warp_cell_old(cell, ps, msd_c)
                warp_new, _, music_x = _warp_cell_new(cell, ps, msd_c, pi.binary)
                page_warped_old.extend(warp_old)
                page_warped_new.extend(warp_new)
                if cell.measure_index == 0:
                    cx0, _, cx1, _ = cell.bbox_page_px
                    music_xs.append((cx0, cx1, music_x, pdf_staff_idx))

    # Build the side-by-side composite
    base_bgr = cv2.cvtColor(pi.rgb, cv2.COLOR_RGB2BGR)
    left = base_bgr.copy()
    right = base_bgr.copy()
    _draw_warped(left, page_warped_old, "OLD (cell-edge homography)", (40, 40, 180))
    _draw_warped(right, page_warped_new, "NEW (music-start anchor)", (40, 140, 40))
    # Annotate detected music-start xs on the right pane (cyan vertical lines)
    for cx0, cx1, mx, sidx in music_xs:
        for y in range(60, right.shape[0], 24):
            cv2.line(right, (mx, y), (mx, y + 8), (255, 255, 0), 2)
        cv2.line(left, (cx0, 60), (cx0, base_bgr.shape[0]), (180, 180, 180), 1)

    composite = np.hstack([left, right])
    # Scale down for an inspectable PNG (max width 2400)
    if composite.shape[1] > 2400:
        scale = 2400 / composite.shape[1]
        composite = cv2.resize(
            composite, (2400, int(composite.shape[0] * scale)),
            interpolation=cv2.INTER_AREA,
        )

    key = f"{args.work}-{args.edition}-mvt{args.mvt}"
    out_path = (Path(args.out) if args.out
                else OUT_BASE / f"{key}-p{args.page:03d}-compare.png")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), composite)
    print(f"\nWrote {out_path}")
    print(f"  OLD warped boxes: {len(page_warped_old)}")
    print(f"  NEW warped boxes: {len(page_warped_new)}")
    print(f"  System-first cells with music-start detected: {len(music_xs)}")
    if music_xs:
        for cx0, cx1, mx, sidx in music_xs[:8]:
            print(f"    staff {sidx}: cell x [{cx0}, {cx1}], "
                  f"music-start x = {mx} (offset = {mx - cx0} px)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
