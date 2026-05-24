#!/usr/bin/env python3
"""Phase E — emit YOLO labels for every (PDF cell × XML measure) pair on the
pages of a single movement.

This extends the Phase C `phase_c_pixel_perfect.py` MVP from "demonstrate
one measure" to "emit full per-cell YOLO labels for a movement". The
strategy:

  1. Load the movement's .mxl via Verovio.
  2. For every PDF page in the movement's page range:
       a. Render the page; detect staves; extract measure cells.
       b. Match each PDF staff to its corresponding XML part (by ordered
          position — the catalog-ready editions all use the standard
          orchestral score layout, so PDF staff 0 = first part listed in
          the XML, PDF staff 1 = second, etc.).
       c. Compute a running XML measure index for each system (= measure
          count in prior systems of this movement, + cell's measure_index
          on this system).
       d. For each (staff, measure_idx) cell, fetch the matching XML
          measure on the matching part, parse staff lines + noteheads +
          clef + accidental positions from the Verovio SVG, compute the
          5-line homography to the cell's PDF region, and warp every
          element position onto the PDF pixel grid.
       e. Emit YOLO labels: notehead bboxes, clef bbox, key-sig and
          time-sig bboxes (system-first cells only), barline bbox (cell
          right edge).
  3. Output: one .txt YOLO label per PDF page in
     {OUT_DIR}/labels/{page:03d}.txt; also write a sidecar PNG with the
     warped boxes drawn over the page, for visual review.

Start with Beethoven 1 imslp-52848 mvt 1 (cleanest catalog-ready pair).
Iterate by visual inspection before scaling to the rest of the catalog.

CLASS IDS (subset of DSv2-compatible labels used in this MVP):
   0 = notehead    (any duration; we'll split into black/half/whole later)
   1 = clef        (any clef type)
   2 = barline
   3 = keysig
   4 = timesig
   5 = accidental  (sharp/flat/natural — separate from notehead so the
                    detector learns them independently)
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.measure_extractor import extract_measures  # noqa: E402

import verovio  # noqa: E402

REPO_ROOT = Path("/Users/seanjohnson/Desktop/ReEngrave")
DATA_ROOT = REPO_ROOT / "tools/omr/training/data/imslp"
OUT_BASE = (
    REPO_ROOT
    / ".claude/worktrees/interesting-curran-3ca1b7"
    / "benchmarks/omr-imslp-pipeline/phase-e-labels"
)

# Verovio page geometry (same as Phase C MVP — gives enough internal
# coord precision without the rasterizer truncating long staves).
VEROVIO_PAGE_WIDTH = 2100
VEROVIO_PAGE_HEIGHT = 2970
VEROVIO_SCALE = 50
PDF_DPI = 300

CLASS_NOTEHEAD = 0
CLASS_CLEF = 1
CLASS_BARLINE = 2
CLASS_KEYSIG = 3
CLASS_TIMESIG = 4
CLASS_ACCIDENTAL = 5


# ─────────────────────────────────────────────────────────────────────────────
# Verovio caching
# ─────────────────────────────────────────────────────────────────────────────


class VerovioCache:
    """Lazily renders Verovio pages and indexes measure id → (page, svg)."""

    def __init__(self, mxl_path: Path) -> None:
        self.mxl_path = mxl_path
        self.tk = verovio.toolkit()
        self.tk.setOptions({
            "pageWidth": VEROVIO_PAGE_WIDTH,
            "pageHeight": VEROVIO_PAGE_HEIGHT,
            "scale": VEROVIO_SCALE,
            "header": "none",
            "footer": "none",
        })
        with open(mxl_path, "rb") as f:
            ok = self.tk.loadZipDataBase64(base64.b64encode(f.read()).decode())
        if not ok:
            raise RuntimeError(f"Verovio failed to load {mxl_path}")
        self.n_pages = self.tk.getPageCount()
        # measure_n (XML measure number string) → (verovio_page, measure_id_in_svg)
        self._measure_index: dict[str, tuple[int, str]] = {}
        self._svg_cache: dict[int, str] = {}
        self._build_measure_index()

    def _build_measure_index(self) -> None:
        for p in range(1, self.n_pages + 1):
            svg = self._svg_for_page(p)
            for vid in re.findall(r'<g id="([^"]+)" class="measure"[^>]*>', svg):
                attr = self.tk.getElementAttr(vid)
                n = attr.get("n")
                if n and n not in self._measure_index:
                    self._measure_index[n] = (p, vid)

    def _svg_for_page(self, p: int) -> str:
        if p not in self._svg_cache:
            self._svg_cache[p] = self.tk.renderToSVG(p)
        return self._svg_cache[p]

    def find_measure(self, xml_n: str) -> Optional[tuple[int, str]]:
        return self._measure_index.get(xml_n)

    def svg(self, page: int) -> str:
        return self._svg_for_page(page)


# ─────────────────────────────────────────────────────────────────────────────
# Per-measure SVG parsing
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class MeasureStaffData:
    """Staff lines + element positions for one (XML measure × XML staff)."""

    staff_lines: list[tuple[float, float, float, float]]      # 5 endpoints
    elements: list[tuple[str, float, float, float, float]]    # (kind, x, y, w, h) in Verovio internal coords


def parse_measure_staves(svg: str, measure_id: str) -> list[MeasureStaffData]:
    """Walk the <g class="measure" id="..."> subtree and return per-staff data."""
    from lxml import etree
    parser = etree.XMLParser(remove_blank_text=False)
    root = etree.fromstring(svg.encode("utf-8"), parser)
    ns = {"svg": "http://www.w3.org/2000/svg",
          "xlink": "http://www.w3.org/1999/xlink"}

    measure_els = root.xpath(f'//svg:g[@id="{measure_id}"]', namespaces=ns)
    if not measure_els:
        return []
    measure_el = measure_els[0]

    out: list[MeasureStaffData] = []
    trans_re = re.compile(r'translate\(([\d.\-]+)[,\s]+([\d.\-]+)\)')

    for staff_el in measure_el.xpath('.//svg:g[@class="staff"]', namespaces=ns):
        lines: list[tuple[float, float, float, float]] = []
        for path in staff_el.xpath('./svg:path', namespaces=ns)[:5]:
            d = path.get("d", "")
            m = re.match(r'M\s*([\d.\-]+)\s+([\d.\-]+)\s+L\s*([\d.\-]+)\s+([\d.\-]+)', d)
            if m:
                lines.append(tuple(float(x) for x in m.groups()))
        if len(lines) != 5:
            continue

        # Staff-line spacing in Verovio units → approximate element extent
        staff_top = lines[0][1]
        staff_bot = lines[-1][1]
        line_spacing = (staff_bot - staff_top) / 4 if staff_bot > staff_top else 50
        # Element extents (rough; tuned later via overlay review)
        nh_w = line_spacing * 1.3
        nh_h = line_spacing * 1.0
        clef_w = line_spacing * 2.5
        clef_h = line_spacing * 5.0
        acc_w = line_spacing * 1.0
        acc_h = line_spacing * 2.2

        elements: list[tuple[str, float, float, float, float]] = []

        def harvest(kind: str, parent, w: float, h: float):
            for use in parent.xpath('.//svg:use', namespaces=ns):
                t = use.get("transform", "")
                m = trans_re.search(t)
                if m:
                    elements.append((kind, float(m.group(1)), float(m.group(2)), w, h))

        for nh_g in staff_el.xpath('.//svg:g[@class="notehead"]', namespaces=ns):
            harvest("notehead", nh_g, nh_w, nh_h)
        for clef_g in staff_el.xpath('.//svg:g[@class="clef"]', namespaces=ns):
            harvest("clef", clef_g, clef_w, clef_h)
        for acc_g in staff_el.xpath(
            './/svg:g[@class="accid"] | .//svg:g[@class="accidental"]',
            namespaces=ns,
        ):
            harvest("accidental", acc_g, acc_w, acc_h)
        # Key signature accidentals usually live in <g class="keySig">
        for ks_g in staff_el.xpath('.//svg:g[@class="keySig"]', namespaces=ns):
            harvest("keysig_acc", ks_g, acc_w, acc_h)

        out.append(MeasureStaffData(staff_lines=lines, elements=elements))

    return out


# ─────────────────────────────────────────────────────────────────────────────
# Homography from Verovio staff lines → PDF cell pixel coordinates
# ─────────────────────────────────────────────────────────────────────────────


def compute_homography(
    rendered_lines: list[tuple[float, float, float, float]],
    pdf_cell_x0: int,
    pdf_cell_x1: int,
    pdf_staff_line_ys: list[int],
) -> Optional[np.ndarray]:
    """Map Verovio internal coords of a (one-measure) staff onto its PDF
    cell. Uses the 5 staff lines × 2 endpoints (10 correspondence
    points)."""
    if len(rendered_lines) != 5 or len(pdf_staff_line_ys) != 5:
        return None
    src_pts = []
    for x0, y0, x1, y1 in rendered_lines:
        src_pts.append((x0, y0))
        src_pts.append((x1, y1))
    src_pts = np.asarray(src_pts, dtype=np.float32)

    dst_pts = []
    for y in pdf_staff_line_ys:
        dst_pts.append((pdf_cell_x0, y))
        dst_pts.append((pdf_cell_x1, y))
    dst_pts = np.asarray(dst_pts, dtype=np.float32)

    H, _ = cv2.findHomography(src_pts, dst_pts, method=cv2.RANSAC)
    return H


def warp_elements(
    elements: list[tuple[str, float, float, float, float]],
    H: np.ndarray,
) -> list[tuple[str, float, float, float, float]]:
    """Apply homography to (kind, x, y, w, h) tuples. Width/height are
    scaled by the local linear approximation of H at the element's position
    (cheaper than warping bbox corners, accurate enough for the MVP)."""
    out: list[tuple[str, float, float, float, float]] = []
    if not elements:
        return out
    pts = np.array([[(x, y)] for _, x, y, _, _ in elements], dtype=np.float32)
    warped = cv2.perspectiveTransform(pts, H).reshape(-1, 2)
    # Local scale factor — derived from the (1,1) jacobian of the homography
    # in the middle of the source space. For a near-affine H this is just
    # sqrt(|det J|) which is roughly the staff scale ratio.
    src_test = np.array([[(0, 0), (100, 0), (0, 100)]], dtype=np.float32)
    warped_test = cv2.perspectiveTransform(src_test, H).reshape(-1, 2)
    dx = warped_test[1] - warped_test[0]
    dy = warped_test[2] - warped_test[0]
    sx = float(np.linalg.norm(dx) / 100)
    sy = float(np.linalg.norm(dy) / 100)
    for (kind, _, _, w, h), (px, py) in zip(elements, warped):
        out.append((kind, float(px), float(py), w * sx, h * sy))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# XML staff → PDF staff mapping
# ─────────────────────────────────────────────────────────────────────────────
#
# Beethoven 1 imslp-52848 mvt 1 is the cleanest catalog pair. The 1862
# Werke layout in this edition uses 12 visible instrument staves per
# system. Hauptstimme's beethoven-symphony-1/mvt-1.mxl, however, splits
# many of these into separate parts (Flauto 1 + Flauto 2 instead of a
# combined Flauti staff, etc.). The mapping below assigns each PDF staff
# the FIRST matching XML part (so the printed Flauti staff which carries
# both flute voices maps to XML staff "Flauto 1" for label-generation
# purposes — the warped notehead positions for Flauto 1 should mostly
# coincide with the visible Flauti staff positions, with the secondary
# Flauto 2 voice riding on the same staff).
#
# For now we hardcode for Beethoven 1; future editions will need their
# own mapping or an automatic mapper that reads <part-list> instrument
# names from the .mxl.

PDF_XML_STAFF_MAP_BEETHOVEN_1 = {
    # pdf_staff_index_within_system: xml_staff_index_in_rendered_verovio
    0: 0,    # Flauti  → Flauto 1
    1: 2,    # Oboi   → Oboe 1
    2: 4,    # Clarinetti → Clarinet 1
    3: 6,    # Fagotti → Bassoon 1
    4: 8,    # Corni   → Horn 1
    5: 10,   # Trombe  → Trumpet 1
    6: 12,   # Timpani
    7: 13,   # Violini I
    8: 14,   # Violini II
    9: 15,   # Viola
    10: 16,  # Violoncello
    11: 17,  # Basso (Contrabasso)
}


# ─────────────────────────────────────────────────────────────────────────────
# YOLO label conversion
# ─────────────────────────────────────────────────────────────────────────────


def warped_to_yolo(
    warped: list[tuple[str, float, float, float, float]],
    image_w: int,
    image_h: int,
) -> list[tuple[int, float, float, float, float]]:
    """Convert (kind, cx, cy, w, h) in PDF pixels → YOLO (class, cx, cy, w, h)
    normalized to image dims. Clamps to [0,1]."""
    kind_to_class = {
        "notehead": CLASS_NOTEHEAD,
        "clef": CLASS_CLEF,
        "barline": CLASS_BARLINE,
        "keysig_acc": CLASS_KEYSIG,
        "timesig": CLASS_TIMESIG,
        "accidental": CLASS_ACCIDENTAL,
    }
    out: list[tuple[int, float, float, float, float]] = []
    for kind, cx, cy, w, h in warped:
        cls = kind_to_class.get(kind)
        if cls is None:
            continue
        ncx = max(0.0, min(1.0, cx / image_w))
        ncy = max(0.0, min(1.0, cy / image_h))
        nw = max(0.0, min(1.0, w / image_w))
        nh = max(0.0, min(1.0, h / image_h))
        if nw <= 0 or nh <= 0:
            continue
        out.append((cls, ncx, ncy, nw, nh))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Main per-movement driver
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
    """Walk every page in the range, emit YOLO labels per page, and
    (optionally) save overlay PNGs."""
    print(f"Loading Verovio cache for {mxl_path.name}...")
    cache = VerovioCache(mxl_path)
    print(f"  indexed {len(cache._measure_index)} measures across "
          f"{cache.n_pages} Verovio pages")

    out_dir.mkdir(parents=True, exist_ok=True)
    labels_dir = out_dir / "labels"
    labels_dir.mkdir(exist_ok=True)
    overlays_dir = out_dir / "overlays"
    if debug_overlays:
        overlays_dir.mkdir(exist_ok=True)

    p_start, p_end = pdf_pages_1indexed
    running_measure = 0   # XML measure index across the movement (1-based)
    summary = {
        "movement_pages": [p_start, p_end],
        "pages_processed": 0,
        "cells_total": 0,
        "cells_with_xml_match": 0,
        "labels_total": 0,
        "homography_failures": 0,
    }

    pages_iter = range(p_start, p_end + 1)
    if max_pages is not None:
        pages_iter = list(pages_iter)[:max_pages]

    for pdf_page in pages_iter:
        print(f"\n── PDF page {pdf_page} ──")
        try:
            pi = render_page(pdf_path, pdf_page - 1, dpi=PDF_DPI)
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

        # Group cells by (system, staff_index) so we can compute
        # measure-within-movement = running_measure + offset.
        # On this page, the LEFTMOST cell (measure_index 0) on each system
        # is the start; cells with measure_index k are the k+1-th measure
        # of that system.
        cells_by_system_staff: dict[tuple[int, int], list] = {}
        for c in cells:
            cells_by_system_staff.setdefault(
                (c.system_index, c.staff_index), []
            ).append(c)
        for k in cells_by_system_staff:
            cells_by_system_staff[k].sort(key=lambda c: c.measure_index)

        page_labels: list[tuple[int, float, float, float, float]] = []
        page_warped_for_overlay: list[tuple[str, float, float, float, float]] = []

        # For each system on this page:
        systems = sorted({c.system_index for c in cells})
        # Number of measures in this system = max measure_index + 1 across all staves
        for sys_idx in systems:
            sys_cells = [c for c in cells if c.system_index == sys_idx]
            if not sys_cells:
                continue
            n_measures = max(c.measure_index for c in sys_cells) + 1
            staves_on_sys = sorted({c.staff_index for c in sys_cells})

            for staff_idx_within_page in staves_on_sys:
                # Pull cells for this staff in this system
                staff_cells = cells_by_system_staff.get(
                    (sys_idx, staff_idx_within_page), []
                )
                if not staff_cells:
                    continue

                # Map PDF staff (within-system position) → XML staff
                staff_idx_within_system = staves_on_sys.index(
                    staff_idx_within_page
                )
                xml_staff = xml_staff_map.get(staff_idx_within_system)
                if xml_staff is None:
                    continue

                for cell in staff_cells:
                    summary["cells_total"] += 1
                    # XML measure index = running_measure + (system measure offset) + 1
                    xml_n = str(running_measure + cell.measure_index + 1)
                    hit = cache.find_measure(xml_n)
                    if hit is None:
                        continue
                    summary["cells_with_xml_match"] += 1
                    vpage, mid = hit
                    svg = cache.svg(vpage)
                    staves_data = parse_measure_staves(svg, mid)
                    if xml_staff >= len(staves_data):
                        continue
                    msd = staves_data[xml_staff]

                    # Get PDF cell anchor: the staff this cell belongs to
                    pdf_staff = next(
                        (s for s in pws.staves if s.staff_index == staff_idx_within_page),
                        None,
                    )
                    if pdf_staff is None:
                        continue

                    cx0, cy0, cx1, cy1 = cell.bbox_page_px
                    H = compute_homography(
                        msd.staff_lines,
                        cx0, cx1,
                        list(pdf_staff.line_ys),
                    )
                    if H is None:
                        summary["homography_failures"] += 1
                        continue

                    warped = warp_elements(msd.elements, H)

                    # Synthesize barline at cell right edge
                    barline_h = pdf_staff.bottom_y - pdf_staff.top_y + 6
                    barline_cy = (pdf_staff.top_y + pdf_staff.bottom_y) / 2
                    warped.append((
                        "barline",
                        float(cx1), float(barline_cy),
                        max(3.0, barline_h * 0.02),
                        float(barline_h),
                    ))
                    page_warped_for_overlay.extend(warped)

                    yolo = warped_to_yolo(warped, pi.width, pi.height)
                    page_labels.extend(yolo)

            # System done — advance running measure
            running_measure += n_measures

        summary["labels_total"] += len(page_labels)

        # Write labels
        label_path = labels_dir / f"p{pdf_page:03d}.txt"
        with label_path.open("w") as f:
            for cls, cx, cy, w, h in page_labels:
                f.write(f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")

        # Overlay
        if debug_overlays:
            overlay = cv2.cvtColor(pi.rgb, cv2.COLOR_RGB2BGR).copy()
            colors = {
                "notehead":   (0, 0, 255),
                "clef":       (0, 200, 0),
                "barline":    (255, 0, 0),
                "keysig_acc": (200, 0, 200),
                "accidental": (0, 200, 200),
            }
            for kind, cx, cy, w, h in page_warped_for_overlay:
                col = colors.get(kind, (128, 128, 128))
                x0 = int(round(cx - w / 2))
                y0 = int(round(cy - h / 2))
                x1 = int(round(cx + w / 2))
                y1 = int(round(cy + h / 2))
                cv2.rectangle(overlay, (x0, y0), (x1, y1), col, 2)
            overlay_path = overlays_dir / f"p{pdf_page:03d}.png"
            cv2.imwrite(str(overlay_path), overlay)

        summary["pages_processed"] += 1
        print(f"  wrote {len(page_labels)} labels → {label_path.name}")

    # Write summary
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
    parser.add_argument("--max-pages", type=int, default=None,
                        help="Cap pages processed (for iterative testing)")
    parser.add_argument("--no-overlays", action="store_true")
    args = parser.parse_args(argv[1:])

    pdf = DATA_ROOT / args.work / "pdfs" / args.edition / "score.pdf"
    mxl = DATA_ROOT / args.work / "musicxml" / f"mvt-{args.mvt}.mxl"
    yml = DATA_ROOT / args.work / "pdfs" / args.edition / "movements.yaml"
    if not pdf.exists():
        print(f"PDF missing: {pdf}")
        return 1
    if not mxl.exists():
        print(f"MXL missing: {mxl}")
        return 1
    if not yml.exists():
        print(f"movements.yaml missing: {yml}")
        return 1

    movements = yaml.safe_load(yml.read_text())
    mvt_key = f"mvt_{args.mvt}"
    if mvt_key not in movements["movements"]:
        print(f"{mvt_key} not in movements.yaml")
        return 1
    pages = movements["movements"][mvt_key]["pages"]
    p_start, p_end = pages

    out_dir = OUT_BASE / f"{args.work}-{args.edition}-mvt{args.mvt}"
    print(f"Working on {args.work}/{args.edition} mvt {args.mvt}, "
          f"pages {p_start}-{p_end}")
    print(f"Out: {out_dir}")

    if args.work == "beethoven-symphony-1":
        xml_staff_map = PDF_XML_STAFF_MAP_BEETHOVEN_1
    else:
        print(f"No PDF→XML staff map for {args.work} — add one to the script")
        return 1

    summary = process_movement(
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
