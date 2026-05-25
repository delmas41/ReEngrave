#!/usr/bin/env python3
"""Phase J — emit YOLO labels for STRUCTURAL classes only.

Rewrite of phase_e_emit_labels.py focused on the three classes the
catalog training was originally intended for (per NOTES.md):

  • barline → prod class 207 (repurposing the underutilized "staff" slot;
    prod model has ~0 detections of class 207 because staff lines are
    classical-CV detected, so no functionality is lost)
  • stem     → prod class 41
  • beam     → prod class 121

Phase I (commit 2b735d1) and Phase H attempts 1+2 trained on labels that
included noteheads/clefs/keysigs/etc, which is exactly what the
production model already knows. That dense-class training on sparser
catalog labels caused the "predict nothing" shortcut. Phase J inverts
this: emit ONLY the new structural information, keep prod's existing
knowledge of noteheads/clefs/etc. alive via mix-mode training with a
small DSv2 sample.

Reuses (imports) from phase_e_emit_labels.py:
  * VerovioCache              — page → measure index lookup
  * build_pdf_xml_staff_map   — PDF staff ↔ XML staff mapping
  * compute_homography        — music-start-anchored homography
  * detect_pdf_music_start_x  — PDF cell scan for clef-setup right edge
  * detect_verovio_music_start_x — Verovio leftmost notehead/rest x

Outputs YOLO label files in the PROD-208 class space directly (no
snapshot→prod remap step needed — we know we're only emitting 3 classes).

CLI:
  python3 benchmarks/omr-imslp-pipeline/phase_j_emit_labels.py \\
      --work beethoven-symphony-1 --edition imslp-52848 --mvt 1
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
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


# Prod-208 class IDs for the three structural classes.
CLASS_STEM = 41
CLASS_BEAM = 121
CLASS_BARLINE = 207   # repurposed "staff" slot (prod has ~0 detections of class 207)

DATA_ROOT = Path("/Users/seanjohnson/Desktop/ReEngrave/tools/omr/training/data/imslp")
OUT_BASE = ROOT / "benchmarks/omr-imslp-pipeline/phase-j-labels"


# ─────────────────────────────────────────────────────────────────────────────
# Structural element extraction from one measure's SVG
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class StructuralData:
    """Stems + beams for one (XML measure × XML staff), in Verovio coords."""
    staff_lines: list[tuple[float, float, float, float]]     # 5 endpoints
    stems: list[tuple[float, float, float, float]]           # (cx, cy, w, h)
    beams: list[tuple[float, float, float, float]]           # (cx, cy, w, h)


def parse_measure_structural(svg: str, measure_id: str) -> list[StructuralData]:
    """Extract staff lines + stems + beams from a single Verovio measure's
    SVG subtree. Returns one StructuralData per staff in the measure.

    Stems are <path d="M x1 y1 L x2 y2" stroke-width="N" /> inside
    <g class="stem">. Beams are <polygon points="x1,y1 x2,y2 x3,y3 x4,y4">
    inside <g class="beam">. Both live under the staff's <g class="layer">."""
    from lxml import etree
    parser = etree.XMLParser(remove_blank_text=False)
    root = etree.fromstring(svg.encode("utf-8"), parser)
    ns = {"svg": "http://www.w3.org/2000/svg"}

    measure_els = root.xpath(f'//svg:g[@id="{measure_id}"]', namespaces=ns)
    if not measure_els:
        return []
    measure_el = measure_els[0]

    out: list[StructuralData] = []

    for staff_el in measure_el.xpath('.//svg:g[@class="staff"]', namespaces=ns):
        # 5 staff lines (top → bottom)
        lines: list[tuple[float, float, float, float]] = []
        for path in staff_el.xpath('./svg:path', namespaces=ns)[:5]:
            d = path.get("d", "")
            m = re.match(r'M\s*([\d.\-]+)\s+([\d.\-]+)\s+L\s*([\d.\-]+)\s+([\d.\-]+)', d)
            if m:
                lines.append(tuple(float(x) for x in m.groups()))
        if len(lines) != 5:
            continue

        # Stems — inside any <g class="stem"> under this staff
        stems: list[tuple[float, float, float, float]] = []
        for stem_g in staff_el.xpath('.//svg:g[@class="stem"]', namespaces=ns):
            for path in stem_g.xpath('./svg:path', namespaces=ns):
                d = path.get("d", "")
                m = re.match(r'M\s*([\d.\-]+)\s+([\d.\-]+)\s+L\s*([\d.\-]+)\s+([\d.\-]+)', d)
                if not m:
                    continue
                x1, y1, x2, y2 = (float(v) for v in m.groups())
                try:
                    sw = float(path.get("stroke-width", "18"))
                except ValueError:
                    sw = 18.0
                # Stem is vertical: same x, different y. Width = stroke.
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2
                w = max(sw, 6.0)
                h = abs(y2 - y1) + sw
                if h > 6.0:
                    stems.append((cx, cy, w, h))

        # Beams — polygons inside <g class="beam">
        beams: list[tuple[float, float, float, float]] = []
        for beam_g in staff_el.xpath('.//svg:g[@class="beam"]', namespaces=ns):
            for poly in beam_g.xpath('./svg:polygon', namespaces=ns):
                pts_str = poly.get("points", "")
                pts: list[tuple[float, float]] = []
                for tok in pts_str.split():
                    if "," in tok:
                        a, b = tok.split(",", 1)
                        try:
                            pts.append((float(a), float(b)))
                        except ValueError:
                            pass
                if len(pts) < 3:
                    continue
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                cx = (min(xs) + max(xs)) / 2
                cy = (min(ys) + max(ys)) / 2
                w = max(max(xs) - min(xs), 4.0)
                h = max(max(ys) - min(ys), 4.0)
                beams.append((cx, cy, w, h))

        out.append(StructuralData(staff_lines=lines, stems=stems, beams=beams))

    return out


# ─────────────────────────────────────────────────────────────────────────────
# YOLO label conversion (prod-208 IDs directly)
# ─────────────────────────────────────────────────────────────────────────────


def to_yolo_norm(
    boxes: list[tuple[int, float, float, float, float]],
    image_w: int,
    image_h: int,
) -> list[tuple[int, float, float, float, float]]:
    """(cls, cx, cy, w, h) in page-px → YOLO (cls, cx, cy, w, h) normalized."""
    out = []
    for cls, cx, cy, w, h in boxes:
        ncx = max(0.0, min(1.0, cx / image_w))
        ncy = max(0.0, min(1.0, cy / image_h))
        nw = max(0.0, min(1.0, w / image_w))
        nh = max(0.0, min(1.0, h / image_h))
        if nw <= 0 or nh <= 0:
            continue
        out.append((cls, ncx, ncy, nw, nh))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Per-movement driver
# ─────────────────────────────────────────────────────────────────────────────


def process_movement(
    pdf_path: Path,
    mxl_path: Path,
    pdf_pages_1indexed: tuple[int, int],
    xml_staff_map: dict[int, int],
    out_dir: Path,
    debug_overlays: bool = True,
    max_pages: Optional[int] = None,
) -> dict:
    print(f"Loading Verovio cache for {mxl_path.name}...")
    cache = pe.VerovioCache(mxl_path)
    print(f"  indexed {len(cache._measure_index)} measures across "
          f"{cache.n_pages} Verovio pages")

    out_dir.mkdir(parents=True, exist_ok=True)
    labels_dir = out_dir / "labels"
    labels_dir.mkdir(exist_ok=True)
    overlays_dir = out_dir / "overlays"
    if debug_overlays:
        overlays_dir.mkdir(exist_ok=True)

    p_start, p_end = pdf_pages_1indexed
    running_measure = 0
    summary = {
        "movement_pages": [p_start, p_end],
        "pages_processed": 0,
        "cells_total": 0,
        "cells_with_xml_match": 0,
        "barlines_emitted": 0,
        "stems_emitted": 0,
        "beams_emitted": 0,
        "labels_total": 0,
        "homography_failures": 0,
    }

    pages_iter = range(p_start, p_end + 1)
    if max_pages is not None:
        pages_iter = list(pages_iter)[:max_pages]

    for pdf_page in pages_iter:
        print(f"\n── PDF page {pdf_page} ──")
        try:
            pi = render_page(pdf_path, pdf_page - 1, dpi=pe.PDF_DPI)
        except Exception as exc:
            print(f"  ! render_page failed: {exc}")
            continue
        try:
            pws = detect_staves(pi)
            cells = extract_measures(pws)
        except Exception as exc:
            print(f"  ! staff/measure extraction failed: {exc}")
            continue

        print(f"  page {pi.width}×{pi.height}, "
              f"{len(pws.staves)} staves, {len(cells)} cells")
        if not cells:
            continue

        cells_by_system_staff: dict[tuple[int, int], list] = {}
        for c in cells:
            cells_by_system_staff.setdefault(
                (c.system_index, c.staff_index), []
            ).append(c)
        for k in cells_by_system_staff:
            cells_by_system_staff[k].sort(key=lambda c: c.measure_index)

        page_labels: list[tuple[int, float, float, float, float]] = []
        page_warped_for_overlay: list[tuple[str, float, float, float, float]] = []

        systems = sorted({c.system_index for c in cells})
        for sys_idx in systems:
            sys_cells = [c for c in cells if c.system_index == sys_idx]
            if not sys_cells:
                continue
            n_measures = max(c.measure_index for c in sys_cells) + 1
            staves_on_sys = sorted({c.staff_index for c in sys_cells})

            for staff_idx_within_page in staves_on_sys:
                staff_cells = cells_by_system_staff.get(
                    (sys_idx, staff_idx_within_page), []
                )
                if not staff_cells:
                    continue

                staff_idx_within_system = staves_on_sys.index(staff_idx_within_page)
                xml_staff = xml_staff_map.get(staff_idx_within_system)
                if xml_staff is None:
                    continue

                pdf_staff = next(
                    (s for s in pws.staves if s.staff_index == staff_idx_within_page),
                    None,
                )
                if pdf_staff is None:
                    continue

                for cell in staff_cells:
                    summary["cells_total"] += 1
                    xml_n = str(running_measure + cell.measure_index + 1)
                    hit = cache.find_measure(xml_n)
                    if hit is None:
                        continue
                    summary["cells_with_xml_match"] += 1
                    vpage, mid = hit
                    svg = cache.svg(vpage)
                    staves_data = parse_measure_structural(svg, mid)
                    if xml_staff >= len(staves_data):
                        continue
                    sd = staves_data[xml_staff]

                    cx0, cy0, cx1, cy1 = cell.bbox_page_px
                    is_system_first = (cell.measure_index == 0)
                    cell_binary = pi.binary[cy0:cy1, cx0:cx1]
                    local_line_ys = [int(y - cy0) for y in pdf_staff.line_ys]
                    pdf_music_x = pe.detect_pdf_music_start_x(
                        cell_binary, local_line_ys, cx0, is_system_first,
                    )
                    if is_system_first:
                        # For structural elements (stems/beams), source-left
                        # is the leftmost stem/beam x — but those might not
                        # exist on this cell. Fall back to staff_lines[0][0]
                        # so the homography stays well-defined.
                        v_xs = [s[0] - s[2] / 2 for s in sd.stems] + \
                               [b[0] - b[2] / 2 for b in sd.beams]
                        if v_xs:
                            source_left_x = float(min(v_xs))
                        else:
                            source_left_x = float(sd.staff_lines[0][0])
                    else:
                        source_left_x = float(sd.staff_lines[0][0])
                    source_right_x = float(sd.staff_lines[0][2])

                    H = pe.compute_homography(
                        sd.staff_lines,
                        source_left_x, source_right_x,
                        pdf_music_x, cx1,
                        list(pdf_staff.line_ys),
                    )
                    if H is None:
                        summary["homography_failures"] += 1
                        continue

                    # Warp stems and beams via the homography
                    src_to_warp = []
                    for cx_v, cy_v, w_v, h_v in sd.stems:
                        src_to_warp.append((CLASS_STEM, cx_v, cy_v, w_v, h_v))
                    for cx_v, cy_v, w_v, h_v in sd.beams:
                        src_to_warp.append((CLASS_BEAM, cx_v, cy_v, w_v, h_v))

                    if src_to_warp:
                        pts = np.array(
                            [[(b[1], b[2])] for b in src_to_warp],
                            dtype=np.float32,
                        )
                        warped = cv2.perspectiveTransform(pts, H).reshape(-1, 2)
                        # Compute pixel scale from a test triangle to scale w/h
                        src_test = np.array(
                            [[(0, 0), (100, 0), (0, 100)]], dtype=np.float32,
                        )
                        warped_test = cv2.perspectiveTransform(src_test, H).reshape(-1, 2)
                        dx = warped_test[1] - warped_test[0]
                        dy = warped_test[2] - warped_test[0]
                        sx = float(np.linalg.norm(dx) / 100)
                        sy = float(np.linalg.norm(dy) / 100)

                        for (cls, _, _, w_v, h_v), (px, py) in zip(src_to_warp, warped):
                            w_px = max(2.0, w_v * sx)
                            h_px = max(2.0, h_v * sy)
                            page_labels.append((
                                cls, float(px), float(py), w_px, h_px,
                            ))
                            if cls == CLASS_STEM:
                                summary["stems_emitted"] += 1
                                page_warped_for_overlay.append(
                                    ("stem", float(px), float(py), w_px, h_px),
                                )
                            elif cls == CLASS_BEAM:
                                summary["beams_emitted"] += 1
                                page_warped_for_overlay.append(
                                    ("beam", float(px), float(py), w_px, h_px),
                                )

                    # Synthesize ONE barline at the cell right edge per staff.
                    # Height = staff span + small pad; width = ~2.5% of staff
                    # height (matches engraver-typical 2-3 px at 300 DPI).
                    barline_top = float(pdf_staff.top_y) - 3
                    barline_bot = float(pdf_staff.bottom_y) + 3
                    barline_cy = (barline_top + barline_bot) / 2
                    barline_h = barline_bot - barline_top
                    barline_w = max(4.0, barline_h * 0.025)
                    page_labels.append((
                        CLASS_BARLINE,
                        float(cx1), barline_cy,
                        barline_w, barline_h,
                    ))
                    page_warped_for_overlay.append((
                        "barline", float(cx1), barline_cy,
                        barline_w, barline_h,
                    ))
                    summary["barlines_emitted"] += 1

            running_measure += n_measures

        # Normalize to YOLO and write
        yolo = to_yolo_norm(page_labels, pi.width, pi.height)
        summary["labels_total"] += len(yolo)
        label_path = labels_dir / f"p{pdf_page:03d}.txt"
        with label_path.open("w") as f:
            for cls, cx, cy, w, h in yolo:
                f.write(f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")

        if debug_overlays:
            overlay = cv2.cvtColor(pi.rgb, cv2.COLOR_RGB2BGR).copy()
            colors = {
                "stem":    (0, 200, 0),     # green
                "beam":    (255, 0, 0),     # blue
                "barline": (0, 0, 255),     # red
            }
            for kind, cx, cy, w, h in page_warped_for_overlay:
                col = colors.get(kind, (128, 128, 128))
                x0 = int(round(cx - w / 2)); y0 = int(round(cy - h / 2))
                x1 = int(round(cx + w / 2)); y1 = int(round(cy + h / 2))
                cv2.rectangle(overlay, (x0, y0), (x1, y1), col, 2)
            cv2.imwrite(str(overlays_dir / f"p{pdf_page:03d}.png"), overlay)

        summary["pages_processed"] += 1
        print(f"  wrote {len(yolo)} labels "
              f"(stems={summary['stems_emitted']} beams={summary['beams_emitted']} "
              f"barlines={summary['barlines_emitted']}) → {label_path.name}")

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nSummary: {summary}")
    return summary


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", default="beethoven-symphony-1")
    parser.add_argument("--edition", default="imslp-52848")
    parser.add_argument("--mvt", type=int, default=1)
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--no-overlays", action="store_true")
    args = parser.parse_args(argv[1:])

    pdf = DATA_ROOT / args.work / "pdfs" / args.edition / "score.pdf"
    mxl = DATA_ROOT / args.work / "musicxml" / f"mvt-{args.mvt}.mxl"
    yml = DATA_ROOT / args.work / "pdfs" / args.edition / "movements.yaml"
    for p in (pdf, mxl, yml):
        if not p.exists():
            print(f"missing: {p}", file=sys.stderr)
            return 1

    movements = yaml.safe_load(yml.read_text())
    mvt_key = f"mvt_{args.mvt}"
    if mvt_key not in movements["movements"]:
        print(f"{mvt_key} not in {yml}", file=sys.stderr)
        return 1
    pages = movements["movements"][mvt_key]["pages"]
    p_start, p_end = pages

    out_dir = OUT_BASE / f"{args.work}-{args.edition}-mvt{args.mvt}"
    print(f"Working on {args.work}/{args.edition} mvt {args.mvt}, "
          f"pages {p_start}-{p_end}")
    print(f"Out: {out_dir}")

    xml_staff_map = pe.build_pdf_xml_staff_map(mxl)
    print(f"PDF→XML staff map: {xml_staff_map}")

    process_movement(
        pdf_path=pdf,
        mxl_path=mxl,
        pdf_pages_1indexed=(p_start, p_end),
        xml_staff_map=xml_staff_map,
        out_dir=out_dir,
        debug_overlays=not args.no_overlays,
        max_pages=args.max_pages,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
