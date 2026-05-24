#!/usr/bin/env python3
"""Phase C — pixel-perfect alignment MVP for Beethoven 5 mvt 1.

For a single (PDF page, XML measure) pair:

  1. Load mvt-1.mxl via Verovio at a fixed page geometry.
  2. Render the SVG page containing the target XML measure.
  3. Rasterize the SVG to PNG at the same DPI as the PDF render.
  4. Parse staff lines for the target measure × staff from the SVG.
  5. Run our staff detector on the PDF page; pick the staff for the same
     part position.
  6. Build a homography from rendered-staff-line endpoints to PDF-staff-line
     endpoints.
  7. Warp the rendered measure image into PDF coordinates and blend over the
     PDF page for visual verification.

This is a focused proof that the staff-line-correspondence homography is
sound on a Breitkopf 1862 / OpenScore Verovio pair. Scaling to the full
catalog (warping every XML element, generating YOLO labels) is the next
phase, not in this MVP.

Outputs: phase-c-output/pixelperfect-{xml_measure}-{staff_idx}.png
"""

from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.measure_extractor import extract_measures  # noqa: E402

import verovio  # noqa: E402

REPO_ROOT = Path("/Users/seanjohnson/Desktop/ReEngrave")
WORK_DIR = REPO_ROOT / "tools/omr/training/data/imslp/beethoven-symphony-5"
PDF_PATH = WORK_DIR / "pdfs/imslp-52624/score.pdf"
MXL_PATH = WORK_DIR / "musicxml/mvt-1.mxl"
OUT_DIR = REPO_ROOT / ".claude/worktrees/interesting-curran-3ca1b7/benchmarks/omr-imslp-pipeline/phase-c-output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Page geometry. Verovio's pageWidth/pageHeight options bound the layout
# space, but the SVG's declared width/height equal those values while
# internal element coords go to multiples that DON'T fit (the scale option
# is a percentage but doesn't fully resize content). We declare large
# enough page bounds + low scale to keep coords inside the SVG viewport,
# then rewrite the SVG with an explicit viewBox before rasterization so
# the rasterizer maps internal coords 1:1 to PNG pixels.
VEROVIO_PAGE_WIDTH = 2100
VEROVIO_PAGE_HEIGHT = 2970
VEROVIO_SCALE = 50

# PDF render DPI. The PDF coord system here is in pixels at this DPI.
PDF_DPI = 300


@dataclass
class RenderedMeasure:
    xml_n: str                   # XML measure number ("1", "2", ...)
    verovio_page: int            # 1-indexed Verovio page containing the measure
    staff_lines_per_staff: list[list[tuple[float, float, float, float]]]
    # one list of 5 line endpoints per staff: (x_start, y_start, x_end, y_end)

    @property
    def num_staves(self) -> int:
        return len(self.staff_lines_per_staff)


# ─────────────────────────────────────────────────────────────────────────────
# Verovio loading + per-measure staff-line extraction
# ─────────────────────────────────────────────────────────────────────────────


def load_verovio() -> verovio.toolkit:
    tk = verovio.toolkit()
    # NB: Verovio's Python binding wants a dict here, NOT a JSON string —
    # passing a string yields "Cannot parse JSON std::string" and silently
    # leaves options at default.
    tk.setOptions({
        "pageWidth": VEROVIO_PAGE_WIDTH,
        "pageHeight": VEROVIO_PAGE_HEIGHT,
        "scale": VEROVIO_SCALE,
        "header": "none",
        "footer": "none",
    })
    with open(MXL_PATH, "rb") as f:
        ok = tk.loadZipDataBase64(base64.b64encode(f.read()).decode())
    if not ok:
        raise RuntimeError("Verovio failed to load .mxl")
    return tk


def find_measure_in_verovio(tk: verovio.toolkit, xml_n: str) -> tuple[int, str]:
    """Return (verovio_page_1indexed, verovio_element_id) for the given XML
    measure number."""
    for p in range(1, tk.getPageCount() + 1):
        svg = tk.renderToSVG(p)
        for vid in re.findall(r'<g id="([^"]+)" class="measure"[^>]*>', svg):
            attr = tk.getElementAttr(vid)
            if attr.get("n") == str(xml_n):
                return p, vid
    raise RuntimeError(f"XML measure {xml_n} not found in Verovio output")


def parse_measure_elements(svg: str, measure_id: str) -> tuple[
    list[list[tuple[float, float, float, float]]],
    list[list[tuple[str, float, float]]],
]:
    """Walk the <g class="measure" id="..."> subtree. Return:
      - staff_lines_per_staff: 5 staff-line endpoints (x0,y0,x1,y1) per part
      - elements_per_staff: list of (kind, x, y) tuples in Verovio internal
        coords for the visible glyphs (noteheads, clef, etc.) per part
    Both lists are aligned by staff index (document order)."""
    from lxml import etree
    parser = etree.XMLParser(remove_blank_text=False)
    root = etree.fromstring(svg.encode("utf-8"), parser)
    ns = {"svg": "http://www.w3.org/2000/svg",
          "xlink": "http://www.w3.org/1999/xlink"}

    measures = root.xpath(f'//svg:g[@id="{measure_id}"]', namespaces=ns)
    if not measures:
        raise RuntimeError(f"measure id {measure_id} not in SVG")
    measure_el = measures[0]

    staff_lines: list[list[tuple[float, float, float, float]]] = []
    elements: list[list[tuple[str, float, float]]] = []

    for staff_el in measure_el.xpath('.//svg:g[@class="staff"]', namespaces=ns):
        # 5 staff-line paths (the first 5 <path> direct children)
        lines: list[tuple[float, float, float, float]] = []
        for p in staff_el.xpath('./svg:path', namespaces=ns)[:5]:
            d = p.get("d", "")
            m = re.match(r'M\s*([\d.\-]+)\s+([\d.\-]+)\s+L\s*([\d.\-]+)\s+([\d.\-]+)', d)
            if m:
                lines.append(tuple(float(x) for x in m.groups()))
        if len(lines) != 5:
            continue
        staff_lines.append(lines)

        # Element positions. Verovio places glyphs via
        # <use transform="translate(X, Y) scale(0.72, 0.72)" xlink:href="..."/>
        # — positions come from the transform's translate(), not x/y attrs.
        staff_elements: list[tuple[str, float, float]] = []
        trans_re = re.compile(r'translate\(([\d.\-]+)[,\s]+([\d.\-]+)\)')

        def harvest(kind: str, parent):
            for use in parent.xpath('.//svg:use', namespaces=ns):
                t = use.get("transform", "")
                m = trans_re.search(t)
                if m:
                    staff_elements.append((kind, float(m.group(1)), float(m.group(2))))

        for nh_g in staff_el.xpath('.//svg:g[@class="notehead"]', namespaces=ns):
            harvest("notehead", nh_g)
        for clef_g in staff_el.xpath('.//svg:g[@class="clef"]', namespaces=ns):
            harvest("clef", clef_g)
        elements.append(staff_elements)

    return staff_lines, elements


def get_rendered_measure(tk: verovio.toolkit, xml_n: str) -> tuple[
    RenderedMeasure,
    list[list[tuple[str, float, float]]],
    str,
]:
    """Return the rendered staff data + element positions + raw SVG."""
    verovio_page, measure_id = find_measure_in_verovio(tk, xml_n)
    svg = tk.renderToSVG(verovio_page)
    staves, elements = parse_measure_elements(svg, measure_id)
    return RenderedMeasure(
        xml_n=xml_n,
        verovio_page=verovio_page,
        staff_lines_per_staff=staves,
    ), elements, svg


# ─────────────────────────────────────────────────────────────────────────────
# SVG → PNG rasterization
# ─────────────────────────────────────────────────────────────────────────────


def svg_to_png(svg: str, target_width_px: int) -> np.ndarray:
    """Rasterize SVG to PNG. First rewrites the SVG's width/height into a
    viewBox so the content's internal coordinates (which can extend far
    beyond Verovio's declared pageWidth) map cleanly to pixel space.
    Returns BGR ndarray. The rasterized image width is target_width_px;
    height scales proportionally."""
    # Verovio emits <svg width="Xpx" height="Ypx"> with no viewBox. Inject
    # one matching that declared size so rasterization maps content area
    # 1:1 with the rasterizer's coordinate system.
    svg_with_viewbox = re.sub(
        r'<svg([^>]*?)width="(\d+(?:\.\d+)?)px"([^>]*?)height="(\d+(?:\.\d+)?)px"([^>]*?)>',
        lambda m: (
            f'<svg{m.group(1)}width="{target_width_px}px"{m.group(3)}'
            f'height="{int(float(m.group(4)) * target_width_px / float(m.group(2)))}px"'
            f'{m.group(5)} viewBox="0 0 {m.group(2)} {m.group(4)}">'
        ),
        svg,
        count=1,
    )
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp_in, \
         tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_out:
        tmp_in.write(svg_with_viewbox.encode("utf-8"))
        tmp_in.flush()
        try:
            import cairosvg
            cairosvg.svg2png(url=tmp_in.name, write_to=tmp_out.name, output_width=target_width_px)
        except Exception:
            subprocess.run(
                ["rsvg-convert", "-w", str(target_width_px),
                 "-o", tmp_out.name, tmp_in.name],
                check=True,
            )
        img = cv2.imread(tmp_out.name, cv2.IMREAD_COLOR)
        if img is None:
            raise RuntimeError(f"Failed to read rasterized PNG at {tmp_out.name}")
    return img


# ─────────────────────────────────────────────────────────────────────────────
# Coord conversion: Verovio internal units → pixels at PDF_DPI
# ─────────────────────────────────────────────────────────────────────────────


def verovio_to_pixel(coord: float, page_dim_mm10: int, scale: int, png_dim_px: int) -> float:
    """Verovio uses 10ths-of-millimeter internally; layout output coordinates
    are in those units * scale/100. The rasterizer maps page_dim_mm10 →
    png_dim_px pixels. So pixel = coord / page_dim_mm10 * png_dim_px (the
    scale cancels because both numerator and denominator scale by it)."""
    return coord / page_dim_mm10 * png_dim_px


# ─────────────────────────────────────────────────────────────────────────────
# Main: build homography and warp overlay
# ─────────────────────────────────────────────────────────────────────────────


def main(
    xml_measure: str = "1",
    xml_staff_idx: int = 13,         # XML staff 13 = Violin 1 in this Beethoven 5 mvt 1 file
    pdf_page_1indexed: int = 7,      # mvt 1 first music page
    pdf_staff_idx: int = 7,          # PDF staff 7 = Violini I in the 1862 Breitkopf layout
) -> int:
    print(f"Verovio target: XML measure {xml_measure}, XML staff {xml_staff_idx}")
    print(f"PDF target:     page {pdf_page_1indexed}, PDF staff {pdf_staff_idx}\n")

    print("── Loading Verovio + rendering MXL ──")
    tk = load_verovio()
    rendered, elements_per_staff, svg = get_rendered_measure(tk, xml_measure)
    print(f"  measure {xml_measure} is on Verovio page {rendered.verovio_page}")
    print(f"  rendered measure has {rendered.num_staves} staves")

    if len(rendered.staff_lines_per_staff) <= xml_staff_idx:
        print(f"  ! rendered measure only has {rendered.num_staves} staves, "
              f"can't index XML staff {xml_staff_idx}")
        return 1

    rendered_staff = rendered.staff_lines_per_staff[xml_staff_idx]
    rendered_elements = elements_per_staff[xml_staff_idx]
    print(f"  rendered XML staff {xml_staff_idx}:")
    for i, (x0, y0, x1, y1) in enumerate(rendered_staff):
        print(f"    line {i}: ({x0:.0f},{y0:.0f}) → ({x1:.0f},{y1:.0f})")
    print(f"  elements on XML staff {xml_staff_idx}: {len(rendered_elements)}")
    for kind, x, y in rendered_elements[:10]:
        print(f"    {kind} @ ({x:.0f},{y:.0f})")
    if len(rendered_elements) > 10:
        print(f"    ... +{len(rendered_elements) - 10} more")

    print(f"\n── Rendering PDF page {pdf_page_1indexed} + detecting staves ──")
    pi = render_page(PDF_PATH, pdf_page_1indexed - 1, dpi=PDF_DPI)
    pws = detect_staves(pi)
    print(f"  PDF page: {pi.width} × {pi.height} @ {PDF_DPI} DPI")
    print(f"  staves detected: {len(pws.staves)}")
    if len(pws.staves) <= pdf_staff_idx:
        print(f"  ! only {len(pws.staves)} staves; can't index {pdf_staff_idx}")
        return 1
    target_staff = sorted(pws.staves, key=lambda s: s.top_y)[pdf_staff_idx]
    print(f"  target PDF staff: line_ys={target_staff.line_ys}, "
          f"x=[{target_staff.x_start}..{target_staff.x_end}]")

    # Extract measure cells on this page; pick the cell for this staff at
    # measure_index 0 (the leftmost measure on the staff). That cell's bbox
    # gives us the x range that the Verovio measure should map to.
    cells = extract_measures(pws)
    target_cells = [c for c in cells
                    if c.staff_index == target_staff.staff_index
                    and c.measure_index == 0]
    if not target_cells:
        print(f"  ! no cell found for staff {target_staff.staff_index} measure 0")
        return 1
    target_cell = target_cells[0]
    cx0, cy0, cx1, cy1 = target_cell.bbox_page_px
    print(f"  PDF cell for measure 0: bbox=({cx0},{cy0}) → ({cx1},{cy1})")

    # Homography correspondence points. Source = Verovio measure's staff
    # lines (which span ONLY that one measure's width). Destination = PDF
    # CELL's x range (the matching measure region) at the staff's line ys.
    src_pts = []
    for x0, y0, x1, y1 in rendered_staff:
        src_pts.append((x0, y0))
        src_pts.append((x1, y1))
    src_pts = np.asarray(src_pts, dtype=np.float32)

    dst_pts = []
    for y in target_staff.line_ys:
        dst_pts.append((cx0, y))
        dst_pts.append((cx1, y))
    dst_pts = np.asarray(dst_pts, dtype=np.float32)

    print("\n── Computing homography (Verovio internal coords → PDF px) ──")
    H, mask = cv2.findHomography(src_pts, dst_pts, method=cv2.RANSAC)
    if H is None:
        print("  ! homography failed")
        return 1
    inliers = int(mask.sum()) if mask is not None else 0
    print(f"  RANSAC inliers: {inliers}/{len(src_pts)}")

    print("\n── Warping rendered element positions to PDF coords ──")
    pts = np.array([[(x, y)] for _, x, y in rendered_elements], dtype=np.float32)
    if len(pts) == 0:
        print("  ! no elements to warp")
        warped_pts = np.zeros((0, 2), dtype=np.float32)
    else:
        warped_pts = cv2.perspectiveTransform(pts, H).reshape(-1, 2)
    for (kind, _, _), (px, py) in zip(rendered_elements[:6], warped_pts[:6]):
        print(f"    {kind} → PDF ({px:.0f}, {py:.0f})")

    # Visualize: draw the PDF page with markers at the warped element positions
    overlay = cv2.cvtColor(pi.rgb, cv2.COLOR_RGB2BGR).copy()
    # Mark the PDF cell boundary (the region this measure should occupy)
    cv2.rectangle(overlay, (cx0, target_staff.top_y - 5), (cx1, target_staff.bottom_y + 5), (255, 0, 0), 3)
    # Draw warped elements: noteheads as filled red circles, clef as filled green square
    for (kind, _, _), (px, py) in zip(rendered_elements, warped_pts):
        if kind == "notehead":
            cv2.circle(overlay, (int(round(px)), int(round(py))), 12, (0, 0, 255), -1)
            cv2.circle(overlay, (int(round(px)), int(round(py))), 12, (0, 0, 0), 1)
        elif kind == "clef":
            cv2.rectangle(overlay, (int(px) - 10, int(py) - 18), (int(px) + 10, int(py) + 18), (0, 200, 0), -1)
            cv2.rectangle(overlay, (int(px) - 10, int(py) - 18), (int(px) + 10, int(py) + 18), (0, 0, 0), 1)

    pad = 200
    y_top = max(0, target_staff.top_y - pad)
    y_bot = min(pi.height, target_staff.bottom_y + pad)
    crop = overlay[y_top:y_bot, :]
    out_path = OUT_DIR / f"pixelperfect-m{xml_measure}-xstaff{xml_staff_idx}-pstaff{pdf_staff_idx}.png"
    cv2.imwrite(str(out_path), crop)
    print(f"\nWrote {out_path}")
    print(f"(blue lines = PDF staff anchor, red dots = warped XML noteheads, green box = warped clef)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
