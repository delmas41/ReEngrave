#!/usr/bin/env python3
"""Phase I — zoom check on system-first cells of one page.

Renders a 2-col composite (OLD vs NEW) cropped tightly to the leftmost
system on the page so the alignment shift is easy to see.

Usage:
  python3 benchmarks/omr-imslp-pipeline/phase_i_zoom_check.py \\
      --work beethoven-symphony-1 --edition imslp-52848 --mvt 1 --page 7
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

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
    return (128, 128, 128)


def _draw(img, warped):
    for cls, cx, cy, w, h in warped:
        col = _color_for(cls)
        x0 = int(round(cx - w / 2)); y0 = int(round(cy - h / 2))
        x1 = int(round(cx + w / 2)); y1 = int(round(cy + h / 2))
        cv2.rectangle(img, (x0, y0), (x1, y1), col, 2)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="beethoven-symphony-1")
    ap.add_argument("--edition", default="imslp-52848")
    ap.add_argument("--mvt", type=int, default=1)
    ap.add_argument("--page", type=int, default=7)
    ap.add_argument("--out", default=None)
    ap.add_argument("--zoom-x-pad", type=int, default=200,
                    help="Extra pixels of context to the right of cell")
    args = ap.parse_args(argv)

    pdf = DATA_ROOT / args.work / "pdfs" / args.edition / "score.pdf"
    mxl = DATA_ROOT / args.work / "musicxml" / f"mvt-{args.mvt}.mxl"
    yml = DATA_ROOT / args.work / "pdfs" / args.edition / "movements.yaml"
    movements = yaml.safe_load(yml.read_text())
    p_start, _ = movements["movements"][f"mvt_{args.mvt}"]["pages"]

    cache = pe.VerovioCache(mxl)
    xml_staff_map = pe.build_pdf_xml_staff_map(mxl)

    pi = render_page(pdf, args.page - 1, dpi=pe.PDF_DPI)
    pws = detect_staves(pi)
    cells = extract_measures(pws)
    print(f"page {pi.width}×{pi.height}, {len(pws.staves)} staves, {len(cells)} cells")

    # Compute running_measure up to this page
    running_measure = 0
    for prior_page in range(p_start, args.page):
        try:
            pi_prior = render_page(pdf, prior_page - 1, dpi=pe.PDF_DPI)
            pws_prior = detect_staves(pi_prior)
            cells_prior = extract_measures(pws_prior)
        except Exception:
            continue
        if not cells_prior:
            continue
        for sys_idx in sorted({c.system_index for c in cells_prior}):
            sys_cells_prior = [c for c in cells_prior if c.system_index == sys_idx]
            if sys_cells_prior:
                running_measure += max(c.measure_index for c in sys_cells_prior) + 1
    print(f"running_measure at start = {running_measure}")

    # Take the first system only, and warp every staff's first cell + the
    # first 1-2 cells after it for context.
    sys0 = min({c.system_index for c in cells})
    sys_cells = [c for c in cells if c.system_index == sys0]
    if not sys_cells:
        print("no cells in first system", file=sys.stderr)
        return 1

    staves_on_sys = sorted({c.staff_index for c in sys_cells})

    warped_old: list = []
    warped_new: list = []
    # crop bounds
    min_x = min(c.bbox_page_px[0] for c in sys_cells)
    max_x = max(c.bbox_page_px[2] for c in sys_cells
                if c.measure_index <= 1)  # 1st and 2nd cell
    min_y = min(c.bbox_page_px[1] for c in sys_cells)
    max_y = max(c.bbox_page_px[3] for c in sys_cells)

    # Add lots of context to the left so we can see warped boxes that
    # land OUTSIDE the cell's bbox (Verovio clefs map to roughly the
    # cell's negative space when the new music-start anchor is used).
    min_x = max(0, min_x - 400)
    max_x = min(pi.width, max_x + args.zoom_x_pad)
    min_y = max(0, min_y - 30)
    max_y = min(pi.height, max_y + 30)

    for pdf_staff_idx in staves_on_sys:
        staff_pos = staves_on_sys.index(pdf_staff_idx)
        x_staff = xml_staff_map.get(staff_pos)
        if x_staff is None:
            continue
        ps = next((s for s in pws.staves if s.staff_index == pdf_staff_idx), None)
        if ps is None:
            continue
        # only first 1-2 cells per staff
        staff_cells = sorted(
            (c for c in sys_cells if c.staff_index == pdf_staff_idx
             and c.measure_index <= 1),
            key=lambda c: c.measure_index,
        )
        for cell in staff_cells:
            xml_n = str(running_measure + cell.measure_index + 1)
            hit = cache.find_measure(xml_n)
            if hit is None:
                continue
            vpage, mid = hit
            staves_data = pe.parse_measure_staves(cache.svg(vpage), mid)
            if x_staff >= len(staves_data):
                continue
            msd = staves_data[x_staff]
            cx0, cy0, cx1, cy1 = cell.bbox_page_px

            # OLD homography
            H_old = pe.compute_homography_legacy(
                msd.staff_lines, cx0, cx1, list(ps.line_ys),
            )
            if H_old is not None:
                w_old = pe.warp_elements(msd.elements, H_old,
                                         pdf_staff_line_ys=list(ps.line_ys))
                warped_old.extend(w_old)

            # NEW homography
            is_sf = (cell.measure_index == 0)
            cell_bin = pi.binary[cy0:cy1, cx0:cx1]
            lys = [int(y - cy0) for y in ps.line_ys]
            pdf_music_x = pe.detect_pdf_music_start_x(cell_bin, lys, cx0, is_sf)
            if is_sf:
                vs = pe.detect_verovio_music_start_x(msd)
                slx = vs if vs is not None else float(msd.staff_lines[0][0])
            else:
                slx = float(msd.staff_lines[0][0])
            srx = float(msd.staff_lines[0][2])
            H_new = pe.compute_homography(msd.staff_lines, slx, srx,
                                          pdf_music_x, cx1, list(ps.line_ys))
            if H_new is not None:
                w_new = pe.warp_elements(msd.elements, H_new,
                                         pdf_staff_line_ys=list(ps.line_ys))
                warped_new.extend(w_new)
            if is_sf:
                print(f"  staff {pdf_staff_idx} (xml {x_staff}): "
                      f"cell [{cx0}, {cx1}], pdf_music_x={pdf_music_x} "
                      f"(offset={pdf_music_x - cx0} px), "
                      f"src_left={slx:.0f}, src_right={srx:.0f}")

    base = cv2.cvtColor(pi.rgb, cv2.COLOR_RGB2BGR)
    left = base.copy()
    right = base.copy()
    _draw(left, warped_old)
    _draw(right, warped_new)
    # Crop both panes
    left_crop = left[min_y:max_y, min_x:max_x].copy()
    right_crop = right[min_y:max_y, min_x:max_x].copy()

    # Banner
    for img, txt, col in (
        (left_crop, "OLD (cell-edge homography)", (40, 40, 180)),
        (right_crop, "NEW (music-start anchor)", (40, 140, 40)),
    ):
        cv2.rectangle(img, (0, 0), (img.shape[1], 50), col, -1)
        cv2.putText(img, txt, (15, 36), cv2.FONT_HERSHEY_SIMPLEX,
                    1.0, (255, 255, 255), 2, cv2.LINE_AA)

    composite = np.hstack([left_crop, right_crop])
    # Cap output width to keep it inspectable
    if composite.shape[1] > 2800:
        s = 2800 / composite.shape[1]
        composite = cv2.resize(composite,
                               (2800, int(composite.shape[0] * s)),
                               interpolation=cv2.INTER_AREA)
    key = f"{args.work}-{args.edition}-mvt{args.mvt}"
    out_path = (Path(args.out) if args.out
                else OUT_BASE / f"{key}-p{args.page:03d}-zoom.png")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), composite)
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
