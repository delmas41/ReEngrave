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
# SMuFL glyph ID → DSv2 class name (Phase G class-space expansion)
# ─────────────────────────────────────────────────────────────────────────────
#
# Verovio's SVG renders symbols via <use xlink:href="#E0A4-..."/>, where
# the leading 4 hex digits are the SMuFL codepoint (private use area
# U+E000-U+F8FF). Map each one to the DSv2 class name as defined in
# tools/omr/training/deepscores_classes.py.
#
# For DSv2 noteheads (and a few other glyphs), the OnLine/InSpace
# distinction depends on the notehead's y position relative to the staff
# lines — that's resolved at warp time via _split_notehead_line_space.

SMUFL_TO_DSV2 = {
    # Clefs (E050-E07F)
    "E050": "gClef",
    "E051": "gClef",       # gClef8va (octave-up) — fold for training
    "E052": "gClef",       # gClef8vb
    "E053": "gClef",       # gClef15ma
    "E054": "gClef",       # gClef15mb
    "E05C": "cClefAlto",   # default; refined to cClefTenor at warp time if the clef y is near staff line 4
    "E05D": "cClefAlto",
    "E062": "fClef",
    "E063": "fClef",       # fClef8va
    "E064": "fClef",       # fClef8vb
    "E069": "unpitchedPercussionClef1",
    "E06A": "unpitchedPercussionClef1",
    # Time signatures
    "E080": "timeSig0",
    "E081": "timeSig1",
    "E082": "timeSig2",
    "E083": "timeSig3",
    "E084": "timeSig4",
    "E085": "timeSig5",
    "E086": "timeSig6",
    "E087": "timeSig7",
    "E088": "timeSig8",
    "E089": "timeSig9",
    "E08A": "timeSigCommon",        # NB: also unpitchedPercussionClef1; resolve via SVG class context
    "E08B": "timeSigCutCommon",
    # Noteheads — needs OnLine/InSpace suffix
    "E0A0": "noteheadDoubleWhole",
    "E0A2": "noteheadWhole",
    "E0A3": "noteheadHalf",
    "E0A4": "noteheadBlack",
    # Accidentals (standalone — keySig variants handled separately)
    "E260": "accidentalFlat",
    "E261": "accidentalNatural",
    "E262": "accidentalSharp",
    "E263": "accidentalDoubleSharp",
    "E264": "accidentalDoubleFlat",
    # Articulations
    "E4A0": "articAccentAbove",
    "E4A1": "articAccentBelow",
    "E4A2": "articStaccatoAbove",
    "E4A3": "articStaccatoBelow",
    "E4A4": "articTenutoAbove",
    "E4A5": "articTenutoBelow",
    "E4A6": "articStaccatissimoAbove",
    "E4A7": "articStaccatissimoBelow",
    "E4AC": "articMarcatoAbove",
    "E4AD": "articMarcatoBelow",
    # Fermatas
    "E4C0": "fermataAbove",
    "E4C1": "fermataBelow",
    "E4D1": "caesura",
    # Rests
    "E4E1": "restWhole",
    "E4E2": "restHalf",
    "E4E3": "restQuarter",
    "E4E4": "rest8th",
    "E4E5": "rest16th",
    "E4E6": "rest32nd",
    "E4E7": "rest64th",
    "E4E8": "rest128th",
    "E4EE": "restHBar",
    # Dynamics (text-based — Verovio still uses use refs)
    "E520": "dynamicPiano",
    "E521": "dynamicMezzo",
    "E522": "dynamicForte",
    "E523": "dynamicRinforzando",
    "E524": "dynamicSforzando",
    "E525": "dynamicZ",
    "E526": "dynamicNiente",
    # Misc structural (mapped to "structural" category)
    "E003": "brace",
    "E1E7": "augmentationDot",
    # Beam / staff line itself — usually drawn by paths, not glyphs; the
    # YOLO model has separate classes for them but they're easier to label
    # via classical CV than via this Verovio path.
}


def smufl_id_from_href(href: str) -> str | None:
    """Extract the 4-hex-digit SMuFL codepoint from a Verovio use href.
    Returns None if href doesn't look like a SMuFL symbol id."""
    if not href:
        return None
    href = href.lstrip("#")
    parts = href.split("-", 1)
    code = parts[0].upper()
    if len(code) == 4 and all(c in "0123456789ABCDEF" for c in code):
        return code
    return None


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
    # Each element: (dsv2_class_name, smufl_id, x, y, w, h) in Verovio internal coords.
    # dsv2_class_name may still be a generic base (e.g. "noteheadBlack") until
    # the OnLine/InSpace refinement at warp time.
    elements: list[tuple[str, str, float, float, float, float]]


def parse_measure_staves(svg: str, measure_id: str) -> list[MeasureStaffData]:
    """Walk the <g class="measure" id="..."> subtree and return per-staff data.

    For each <use> we extract the SMuFL glyph ID from its xlink:href and look
    up the DSv2 class name in SMUFL_TO_DSV2. Glyphs we don't recognize fall
    back to the parent <g class=...> hint (notehead/clef/accidental)."""
    from lxml import etree
    parser = etree.XMLParser(remove_blank_text=False)
    root = etree.fromstring(svg.encode("utf-8"), parser)
    ns = {"svg": "http://www.w3.org/2000/svg",
          "xlink": "http://www.w3.org/1999/xlink"}
    xlink = "{http://www.w3.org/1999/xlink}href"

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

        # Staff-line spacing in Verovio units → element extents
        staff_top = lines[0][1]
        staff_bot = lines[-1][1]
        line_spacing = (staff_bot - staff_top) / 4 if staff_bot > staff_top else 50

        elements: list[tuple[str, str, float, float, float, float]] = []

        def harvest(group_kind: str, parent, default_w: float, default_h: float):
            for use in parent.xpath('.//svg:use', namespaces=ns):
                t = use.get("transform", "")
                m = trans_re.search(t)
                if not m:
                    continue
                x, y = float(m.group(1)), float(m.group(2))
                href = use.get(xlink) or use.get("href") or ""
                smufl = smufl_id_from_href(href) or ""
                # Map SMuFL → DSv2 class; fall back to group_kind base when unknown.
                # Note: SMuFL E08A is timeSigCommon (in `<g class="meterSig">`)
                # but also unpitchedPercussionClef1 (in `<g class="clef">`).
                # Resolve by parent group class.
                dsv2 = SMUFL_TO_DSV2.get(smufl)
                if dsv2 is None:
                    dsv2 = group_kind  # fallback to the parent's <g class=...>
                elif smufl == "E08A":
                    dsv2 = "unpitchedPercussionClef1" if group_kind == "clef" else "timeSigCommon"
                # Per-class extent (in Verovio units)
                w, h = _element_extent(dsv2, line_spacing, default_w, default_h)
                elements.append((dsv2, smufl, x, y, w, h))

        # Notehead group
        for nh_g in staff_el.xpath('.//svg:g[@class="notehead"]', namespaces=ns):
            harvest("noteheadBlack", nh_g, line_spacing * 1.3, line_spacing * 1.0)
        # Clef group
        for clef_g in staff_el.xpath('.//svg:g[@class="clef"]', namespaces=ns):
            harvest("gClef", clef_g, line_spacing * 2.5, line_spacing * 5.0)
        # Accidental (standalone)
        for acc_g in staff_el.xpath(
            './/svg:g[@class="accid"] | .//svg:g[@class="accidental"]',
            namespaces=ns,
        ):
            harvest("accidentalSharp", acc_g, line_spacing * 1.0, line_spacing * 2.2)
        # Key signature — these are accidentals but live in keySig group
        for ks_g in staff_el.xpath('.//svg:g[@class="keySig"]', namespaces=ns):
            # Use the SMuFL id to distinguish keyFlat/keyNatural/keySharp.
            for use in ks_g.xpath('.//svg:use', namespaces=ns):
                t = use.get("transform", "")
                m = trans_re.search(t)
                if not m:
                    continue
                x, y = float(m.group(1)), float(m.group(2))
                href = use.get(xlink) or use.get("href") or ""
                smufl = smufl_id_from_href(href) or ""
                # SMuFL accidental codes used in key signatures:
                #   E260 flat, E261 natural, E262 sharp
                key_class_map = {
                    "E260": "keyFlat",
                    "E261": "keyNatural",
                    "E262": "keySharp",
                }
                dsv2 = key_class_map.get(smufl, "keySharp")
                w, h = _element_extent(dsv2, line_spacing,
                                       line_spacing * 1.0, line_spacing * 2.2)
                elements.append((dsv2, smufl, x, y, w, h))
        # Time signature digits
        for ts_g in staff_el.xpath('.//svg:g[@class="meterSig"]', namespaces=ns):
            harvest("timeSig4", ts_g, line_spacing * 1.6, line_spacing * 2.0)
        # Rests
        for r_g in staff_el.xpath('.//svg:g[@class="rest"]', namespaces=ns):
            harvest("restQuarter", r_g, line_spacing * 1.5, line_spacing * 2.5)
        # Articulations + ornaments + fermatas
        for art_g in staff_el.xpath(
            './/svg:g[@class="artic"] | .//svg:g[@class="ornament"] '
            '| .//svg:g[@class="fermata"]',
            namespaces=ns,
        ):
            harvest("articStaccatoAbove", art_g, line_spacing * 1.2, line_spacing * 0.8)
        # Dynamics — Verovio puts these under <g class="dynam"> using text or use refs
        for dyn_g in staff_el.xpath('.//svg:g[@class="dynam"]', namespaces=ns):
            harvest("dynamicForte", dyn_g, line_spacing * 2.5, line_spacing * 2.0)

        out.append(MeasureStaffData(staff_lines=lines, elements=elements))

    return out


def _element_extent(
    dsv2_class: str,
    line_spacing: float,
    default_w: float,
    default_h: float,
) -> tuple[float, float]:
    """Return a (width, height) in Verovio internal units for a given DSv2
    class. Heuristic — tuned later via overlay review."""
    # Tall thin glyphs
    if dsv2_class in ("gClef", "fClef", "cClef", "unpitchedPercussionClef1"):
        return line_spacing * 2.5, line_spacing * 5.5
    if dsv2_class.startswith("timeSig"):
        return line_spacing * 1.6, line_spacing * 2.2
    if dsv2_class.startswith("accidental") or dsv2_class.startswith("key"):
        return line_spacing * 1.0, line_spacing * 2.2
    if dsv2_class.startswith("notehead"):
        return line_spacing * 1.3, line_spacing * 1.0
    if dsv2_class.startswith("rest"):
        return line_spacing * 1.5, line_spacing * 2.5
    if dsv2_class.startswith("artic"):
        return line_spacing * 1.0, line_spacing * 0.7
    if dsv2_class.startswith("fermata"):
        return line_spacing * 2.0, line_spacing * 1.2
    if dsv2_class.startswith("dynamic"):
        return line_spacing * 2.5, line_spacing * 2.0
    return default_w, default_h


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
    elements: list[tuple[str, str, float, float, float, float]],
    H: np.ndarray,
    pdf_staff_line_ys: list[int] | None = None,
) -> list[tuple[str, float, float, float, float]]:
    """Apply homography to (dsv2_class, smufl, x, y, w, h) tuples and return
    a list of (dsv2_class_refined, cx_pdf, cy_pdf, w_pdf, h_pdf) tuples in
    PDF pixel coords. The dsv2_class is refined post-warp where it depends
    on PDF-space geometry:
      - notehead{Black,Half,Whole,DoubleWhole} → suffixed with OnLine /
        InSpace by comparing warped y vs the PDF staff line ys.
    """
    out: list[tuple[str, float, float, float, float]] = []
    if not elements:
        return out
    pts = np.array([[(x, y)] for _, _, x, y, _, _ in elements], dtype=np.float32)
    warped = cv2.perspectiveTransform(pts, H).reshape(-1, 2)
    src_test = np.array([[(0, 0), (100, 0), (0, 100)]], dtype=np.float32)
    warped_test = cv2.perspectiveTransform(src_test, H).reshape(-1, 2)
    dx = warped_test[1] - warped_test[0]
    dy = warped_test[2] - warped_test[0]
    sx = float(np.linalg.norm(dx) / 100)
    sy = float(np.linalg.norm(dy) / 100)
    line_ys = sorted(pdf_staff_line_ys) if pdf_staff_line_ys else None
    avg_line_gap = (line_ys[-1] - line_ys[0]) / 4 if line_ys else 18

    for (dsv2_class, _smufl, _vx, _vy, w, h), (px, py) in zip(elements, warped):
        refined = dsv2_class
        # Refine notehead{Black,Half,Whole,DoubleWhole} → OnLine/InSpace.
        if dsv2_class.startswith("notehead") and line_ys:
            on_line = _is_on_staff_line(py, line_ys, avg_line_gap)
            refined = f"{dsv2_class}{'OnLine' if on_line else 'InSpace'}"
        # Refine C clef alto/tenor by where the clef center sits on the
        # staff: alto = middle line (index 2), tenor = 4th from top (index 3).
        elif dsv2_class == "cClefAlto" and line_ys and len(line_ys) == 5:
            d_alto = abs(py - line_ys[2])
            d_tenor = abs(py - line_ys[3])
            if d_tenor < d_alto:
                refined = "cClefTenor"
        out.append((refined, float(px), float(py), w * sx, h * sy))
    return out


def _is_on_staff_line(y: float, line_ys: list[int], avg_gap: float) -> bool:
    """Return True if y is within ±30% of avg_gap of any of the 5 staff
    lines (or any ledger-line extension above/below). Otherwise it's in a
    space (between lines, or in the middle of a between-ledger gap)."""
    # Walk both staff lines and extrapolated ledger lines.
    tol = avg_gap * 0.3
    # Generate ledger line ys above and below the staff (4 above, 4 below)
    ledger_ys = []
    for i in range(1, 5):
        ledger_ys.append(line_ys[0] - i * avg_gap)
        ledger_ys.append(line_ys[-1] + i * avg_gap)
    all_lines = list(line_ys) + ledger_ys
    return any(abs(y - ly) <= tol for ly in all_lines)


# ─────────────────────────────────────────────────────────────────────────────
# XML staff → PDF staff mapping
# ─────────────────────────────────────────────────────────────────────────────
#
# Symphonic score convention (standard since ~1820):
#   • Winds/brass come in numbered pairs (Flute 1, Flute 2; Oboe 1, Oboe 2;
#     ...) and are written on ONE staff per family. Verovio renders each
#     numbered part as its own staff system, so for label generation we
#     map the visible "Flauti" staff to XML staff index of FLUTE 1 — the
#     warped positions for Flute 2 ride on the same staff and would
#     duplicate the labels.
#   • Strings (Violin 1, Violin 2, Viola, Violoncello, Contrabass) get
#     their own staff each, even when numbered.
#   • Timpani and other percussion are always solo-staff.
#
# Build the map by walking the part-list and grouping consecutive parts
# whose instrument-family is in COMBINE_FAMILIES.

COMBINE_FAMILIES = {
    "flute", "piccolo",
    "oboe", "english horn", "cor anglais",
    "clarinet", "bass clarinet",
    "bassoon", "contrabassoon",
    "horn", "french horn", "corno",
    "trumpet", "tromba",
    "trombone",
    "tuba",
}
# Strings + percussion stay separate even when numbered.
SEPARATE_FAMILIES = {
    "violin", "violini",
    "viola",
    "violoncello", "cello",
    "contrabass", "double bass", "bass",
    "timpani",
    "percussion", "snare drum", "bass drum", "cymbal",
    "harp", "celesta", "piano",
}


def _family_of(part_name: str) -> str:
    """Strip trailing number/voice tag from a part name to get its family.
    'Flute 1' → 'flute', 'Bb Clarinet 2' → 'clarinet',
    'C Horn 1' → 'horn'."""
    import re as _re
    name = part_name.strip().lower()
    # Strip leading transposition / key tags ("Bb", "C", "F", etc.)
    name = _re.sub(r"^[a-z]+\s+(?=[a-z])", "", name) if " " in name else name
    # Strip trailing number/roman
    name = _re.sub(r"\s+\d+$", "", name)
    name = _re.sub(r"\s+[ivxIVX]+$", "", name)
    # Strip parenthetical descriptors ("Bb (alto) Horn 1" → "horn")
    name = _re.sub(r"\([^)]*\)\s*", "", name).strip()
    # Strip leading "Bb" / "C" / "F" / "Eb" / "A" prefix again post-paren
    name = _re.sub(r"^[a-g]b?\s+", "", name)
    return name.strip()


def build_pdf_xml_staff_map(mxl_path: Path) -> dict[int, int]:
    """Read <part-list>/<score-part> from the .mxl and build a
    PDF_staff_index → XML_staff_index map by grouping consecutive parts
    whose family is in COMBINE_FAMILIES."""
    import zipfile
    from lxml import etree

    with zipfile.ZipFile(mxl_path) as zf:
        main = next(m for m in zf.namelist()
                    if m.endswith(".xml") and "META-INF" not in m)
        with zf.open(main) as f:
            root = etree.fromstring(f.read())
    score_parts = root.findall(".//part-list/score-part")
    parts: list[tuple[int, str, str]] = []
    for idx, sp in enumerate(score_parts):
        name_el = sp.find("part-name")
        name = (name_el.text or "").strip() if name_el is not None else ""
        family = _family_of(name)
        parts.append((idx, name, family))

    pdf_to_xml: dict[int, int] = {}
    pdf_staff_idx = 0
    i = 0
    while i < len(parts):
        xml_idx, _, family = parts[i]
        pdf_to_xml[pdf_staff_idx] = xml_idx
        if family in COMBINE_FAMILIES:
            # consume consecutive parts in the same family
            j = i + 1
            while j < len(parts) and parts[j][2] == family:
                j += 1
            i = j
        else:
            # solo / string section
            i += 1
        pdf_staff_idx += 1
    return pdf_to_xml


# Beethoven 1 imslp-52848 mvt 1 hardcoded reference. Kept for back-compat
# and for the regression check below; runtime now uses build_pdf_xml_staff_map.
PDF_XML_STAFF_MAP_BEETHOVEN_1 = {
    0: 0,    # Flauti  → Flute 1
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


def _build_dsv2_class_index() -> dict[str, int]:
    """Build DSv2 class_name → integer_id for YOLO. Pulled in lazily so
    the script still runs when tools.omr is not on the path (tests)."""
    try:
        from tools.omr.training.deepscores_classes import DEEPSCORES_V2_CLASSES
    except Exception:
        return {}
    return {name: idx for idx, name in enumerate(DEEPSCORES_V2_CLASSES)}


# Built once at import time. None if the DSv2 list isn't reachable; then
# we'll fall back to the 6-class MVP labels for backward compatibility.
DSV2_CLASS_INDEX: dict[str, int] = _build_dsv2_class_index()


# Barline gets a synthetic class. DSv2's published 146-class list does
# NOT include a "barline" entry — barlines are detected via classical CV
# in the existing pipeline. To keep the YOLO labels strictly DSv2-
# compatible we drop barlines from the YOLO emission (warped_to_yolo's
# `dropped` counter will surface them in the summary for diagnostics).
# Overlay drawing still uses this name to color the synthesized barline.
BARLINE_DSV2_CLASS = "barline"   # filtered out by warped_to_yolo; for overlays only


def warped_to_yolo(
    warped: list[tuple[str, float, float, float, float]],
    image_w: int,
    image_h: int,
) -> tuple[list[tuple[int, float, float, float, float]], dict[str, int]]:
    """Convert (dsv2_class, cx, cy, w, h) in PDF px → YOLO (class_id, cx,
    cy, w, h) normalized to image dims. Class id comes from
    DSV2_CLASS_INDEX; classes not present in the DSv2 list are dropped
    (and counted in the returned `dropped` dict for diagnostics).

    Returns (yolo_labels, dropped_counts)."""
    out: list[tuple[int, float, float, float, float]] = []
    dropped: dict[str, int] = {}
    for dsv2_class, cx, cy, w, h in warped:
        cls = DSV2_CLASS_INDEX.get(dsv2_class)
        if cls is None:
            dropped[dsv2_class] = dropped.get(dsv2_class, 0) + 1
            continue
        ncx = max(0.0, min(1.0, cx / image_w))
        ncy = max(0.0, min(1.0, cy / image_h))
        nw = max(0.0, min(1.0, w / image_w))
        nh = max(0.0, min(1.0, h / image_h))
        if nw <= 0 or nh <= 0:
            continue
        out.append((cls, ncx, ncy, nw, nh))
    return out, dropped


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

                    warped = warp_elements(
                        msd.elements, H,
                        pdf_staff_line_ys=list(pdf_staff.line_ys),
                    )

                    # Synthesize barline at cell right edge (DSv2 has a single
                    # "barline" class — finer barline-type discrimination
                    # belongs to a follow-up class-list extension).
                    barline_h = pdf_staff.bottom_y - pdf_staff.top_y + 6
                    barline_cy = (pdf_staff.top_y + pdf_staff.bottom_y) / 2
                    warped.append((
                        BARLINE_DSV2_CLASS,
                        float(cx1), float(barline_cy),
                        max(3.0, barline_h * 0.02),
                        float(barline_h),
                    ))
                    page_warped_for_overlay.extend(warped)

                    yolo, dropped = warped_to_yolo(warped, pi.width, pi.height)
                    page_labels.extend(yolo)
                    for k, v in dropped.items():
                        summary.setdefault("dropped_classes", {})
                        summary["dropped_classes"][k] = (
                            summary["dropped_classes"].get(k, 0) + v
                        )

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

            def _color_for(dsv2_class: str) -> tuple[int, int, int]:
                # Group DSv2 classes by visual category and assign a color.
                if dsv2_class.startswith("notehead"):
                    return (0, 0, 255)      # red
                if dsv2_class in ("gClef", "fClef", "cClef") or "Clef" in dsv2_class:
                    return (0, 200, 0)      # green
                if dsv2_class == "barline":
                    return (255, 0, 0)      # blue
                if dsv2_class.startswith("key"):
                    return (200, 0, 200)    # magenta
                if dsv2_class.startswith("timeSig"):
                    return (255, 255, 0)    # cyan
                if dsv2_class.startswith("accidental"):
                    return (0, 200, 200)    # yellow-ish
                if dsv2_class.startswith("rest"):
                    return (128, 0, 255)    # purple
                if dsv2_class.startswith("artic") or dsv2_class.startswith("fermata"):
                    return (255, 128, 0)    # orange
                if dsv2_class.startswith("dynamic"):
                    return (0, 255, 128)    # teal
                return (128, 128, 128)      # gray = unknown

            for dsv2_class, cx, cy, w, h in page_warped_for_overlay:
                col = _color_for(dsv2_class)
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

    xml_staff_map = build_pdf_xml_staff_map(mxl)
    print(f"PDF→XML staff map ({len(xml_staff_map)} PDF staves): {xml_staff_map}")
    # Sanity check against the Beethoven 1 hard-coded reference
    if args.work == "beethoven-symphony-1" and args.mvt == 1:
        ref = PDF_XML_STAFF_MAP_BEETHOVEN_1
        if xml_staff_map != ref:
            print(f"  ! auto-generated map differs from Beethoven 1 reference")
            print(f"    ref: {ref}")

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
