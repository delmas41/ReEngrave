#!/usr/bin/env python3
"""Phase C — cell-level XML↔PDF alignment validation.

Single-pair validation for Beethoven 5 mvt 1 against the 1862 Breitkopf IMSLP
edition (imslp-52624), PDF pages 7-40.

Output: JSON manifest mapping {xml_measure_number → [pdf_cell_bbox_per_staff...]}
plus a stats report.
"""

from __future__ import annotations

import json
import sys
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.measure_extractor import extract_measures  # noqa: E402


REPO_ROOT = Path("/Users/seanjohnson/Desktop/ReEngrave")
DATA_ROOT = REPO_ROOT / "tools/omr/training/data/imslp"
WORK_DIR = DATA_ROOT / "beethoven-symphony-5"
PDF_PATH = WORK_DIR / "pdfs/imslp-52624/score.pdf"
MXL_PATH = WORK_DIR / "musicxml/mvt-1.mxl"
OUT_DIR = REPO_ROOT / ".claude/worktrees/interesting-curran-3ca1b7/benchmarks/omr-imslp-pipeline/phase-c-output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MVT1_FIRST_PAGE = 7   # 1-indexed PDF page
MVT1_LAST_PAGE = 40   # 1-indexed PDF page inclusive
DPI = 300             # 300 is enough to read; 600 is what production uses


# ─────────────────────────────────────────────────────────────────────────────
# XML parsing
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class XmlMeasure:
    number: int                  # measure number from XML attribute
    is_implicit: bool            # anacrusis flag
    time_signature: str | None   # e.g. "2/4"
    key_fifths: int | None       # XML <key><fifths>
    clef_changes: list[str]      # per-staff clef changes at this measure start
    barline_type: str            # "regular", "double", "final", "repeat-start", "repeat-end"
    has_repeat_start: bool
    has_repeat_end: bool
    dynamics: list[str]          # ["pp", "ff", ...] anywhere in measure
    note_count_total: int        # crude — sum across all parts


def parse_xml_measures(mxl_path: Path) -> tuple[list[XmlMeasure], int]:
    """Return (measures_for_part0, num_parts). All parts in a MusicXML score
    have identical measure structure, so part 0 is representative."""
    with zipfile.ZipFile(mxl_path) as z:
        main = next(n for n in z.namelist() if n.endswith(".xml") and "META-INF" not in n)
        with z.open(main) as f:
            tree = ET.parse(f)
    root = tree.getroot()
    parts = root.findall(".//part")
    num_parts = len(parts)
    if num_parts == 0:
        raise RuntimeError("no <part> elements in XML")

    # First, harvest dynamics and note counts ACROSS all parts per measure.
    # Then attribute-style fields (time, key, clef, barline) from part 0.
    dynamics_by_measure: dict[int, list[str]] = {}
    note_count_by_measure: dict[int, int] = {}
    for part in parts:
        for m in part.findall("measure"):
            mn = int(m.get("number"))
            for dyn in m.findall(".//direction-type/dynamics/*"):
                tag = dyn.tag
                dynamics_by_measure.setdefault(mn, []).append(tag)
            note_count_by_measure[mn] = note_count_by_measure.get(mn, 0) + len(m.findall(".//note"))

    measures: list[XmlMeasure] = []
    for m in parts[0].findall("measure"):
        mn = int(m.get("number"))
        is_implicit = m.get("implicit", "no") == "yes"
        attrs = m.find("attributes")
        time_sig = None
        key_fifths = None
        clef_changes: list[str] = []
        if attrs is not None:
            t = attrs.find("time")
            if t is not None:
                beats = t.findtext("beats")
                btype = t.findtext("beat-type")
                if beats and btype:
                    time_sig = f"{beats}/{btype}"
            k = attrs.find("key")
            if k is not None:
                f = k.findtext("fifths")
                if f is not None:
                    key_fifths = int(f)
            for c in attrs.findall("clef"):
                sign = c.findtext("sign") or "?"
                line = c.findtext("line") or "?"
                clef_changes.append(f"{sign}{line}")

        barline_type = "regular"
        has_repeat_start = False
        has_repeat_end = False
        for bl in m.findall("barline"):
            loc = bl.get("location", "right")
            style = bl.findtext("bar-style") or "regular"
            repeat = bl.find("repeat")
            if repeat is not None:
                direction = repeat.get("direction")
                if direction == "backward":
                    has_repeat_end = True
                elif direction == "forward":
                    has_repeat_start = True
            if loc == "right":
                barline_type = style

        measures.append(XmlMeasure(
            number=mn,
            is_implicit=is_implicit,
            time_signature=time_sig,
            key_fifths=key_fifths,
            clef_changes=clef_changes,
            barline_type=barline_type,
            has_repeat_start=has_repeat_start,
            has_repeat_end=has_repeat_end,
            dynamics=dynamics_by_measure.get(mn, []),
            note_count_total=note_count_by_measure.get(mn, 0),
        ))
    return measures, num_parts


# ─────────────────────────────────────────────────────────────────────────────
# Repeat-style classification
# ─────────────────────────────────────────────────────────────────────────────


def classify_xml_repeat_style(xml_measures: list[XmlMeasure]) -> dict:
    """Determine whether the XML notates repeats or has them written out.

    Two MusicXML conventions coexist:
      - NOTATED: the XML uses <repeat direction="forward|backward"/> elements
        and the measure count matches the printed score. PDF count = XML count.
      - EXPANDED: the XML omits <repeat> elements and writes the repeated
        measures twice, so the played measure count equals the XML count and
        the PDF count is smaller. Common in some MuseScore exports.

    Without a heuristic that finds the repeat boundary in the XML
    (content-duplication detection), we can't compute the exact target PDF
    count for the EXPANDED case. This classifier flags ambiguity so the
    caller can request manual input or hand-spot-check.

    Returns a dict with keys:
        style: "notated" | "expanded?" | "no-repeat"
        repeat_count: number of <repeat> elements in the XML
        expected_pdf_measures: best-guess PDF measure count
        notes: human-readable explanation
    """
    repeat_count = sum(
        (1 if m.has_repeat_start else 0) + (1 if m.has_repeat_end else 0)
        for m in xml_measures
    )
    n = len(xml_measures)

    if repeat_count > 0:
        return {
            "style": "notated",
            "repeat_count": repeat_count,
            "expected_pdf_measures": n,
            "notes": (
                f"XML uses {repeat_count} <repeat> element(s); the score is notated "
                f"with repeat signs and PDF measure count should match XML."
            ),
        }

    return {
        "style": "expanded?",
        "repeat_count": 0,
        "expected_pdf_measures": n,
        "notes": (
            "No <repeat> elements in the XML. Could be (a) a piece without repeats "
            "(true PDF count == XML count) or (b) the XML wrote repeats out (true "
            "PDF count < XML count). Disambiguate by hand-counting one PDF page "
            "or by checking for measure-by-measure content duplication in the XML."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# PDF cell extraction
# ─────────────────────────────────────────────────────────────────────────────


def extract_cells_for_range(pdf_path: Path, page_indices: list[int], dpi: int = DPI):
    """Run staff & barline detection + measure extraction on each page.
    Returns: (per_page_results, total_cells)
    per_page_results: list of dicts with page metadata + cells
    """
    results = []
    for page_idx in page_indices:
        print(f"  page {page_idx + 1}: rendering @ {dpi} DPI...", flush=True)
        try:
            pi = render_page(pdf_path, page_idx, dpi=dpi)
            pws = detect_staves(pi)
            cells = extract_measures(pws)
        except Exception as e:
            print(f"    ! page {page_idx + 1} failed: {e}", flush=True)
            results.append({"page_index": page_idx, "error": str(e)})
            continue

        # Number of unique (system, staff_within_system) → count per-system measure totals
        by_system: dict[int, dict] = {}
        for c in cells:
            by_system.setdefault(c.system_index, {"n_staves": set(), "max_m": -1, "barlines": []})
            by_system[c.system_index]["n_staves"].add(c.staff_index)
            by_system[c.system_index]["max_m"] = max(by_system[c.system_index]["max_m"], c.measure_index)

        for sys_idx in sorted(by_system):
            sys_info = by_system[sys_idx]
            sys_info["n_staves"] = len(sys_info["n_staves"])
            sys_info["measures_in_system"] = sys_info["max_m"] + 1
            del sys_info["max_m"]
            del sys_info["barlines"]

        results.append({
            "page_index": page_idx,
            "n_staves_detected": len(pws.staves),
            "n_systems": len(by_system),
            "systems": by_system,
            "cells": cells,
            "image_height": pi.height,
            "image_width": pi.width,
        })
        n_cells = len(cells)
        n_systems = len(by_system)
        sys_summary = ", ".join(f"sys{s}={by_system[s]['n_staves']}×{by_system[s]['measures_in_system']}" for s in sorted(by_system))
        print(f"    {n_systems} system(s), {n_cells} cells [{sys_summary}]", flush=True)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Alignment
# ─────────────────────────────────────────────────────────────────────────────


def build_alignment(per_page_results, xml_measures: list[XmlMeasure]):
    """For each cell, compute its absolute measure number (1-indexed) by
    accumulating measure counts across systems and pages. Then group cells by
    (absolute_measure_number, staff_within_system).

    Returns: dict {absolute_measure_number: {(page_idx, system_idx, staff_idx): bbox}}
    """
    alignment: dict[int, list] = {}
    cumulative_measures = 0    # measures before the current system

    for page in per_page_results:
        if "error" in page or not page.get("systems"):
            continue
        page_idx = page["page_index"]
        for sys_idx in sorted(page["systems"]):
            sys_meas = page["systems"][sys_idx]["measures_in_system"]
            for cell in page["cells"]:
                if cell.system_index != sys_idx:
                    continue
                abs_m = cumulative_measures + cell.measure_index + 1
                alignment.setdefault(abs_m, []).append({
                    "page_index": page_idx,
                    "system_index": sys_idx,
                    "staff_index": cell.staff_index,
                    "bbox_page_px": list(cell.bbox_page_px),
                })
            cumulative_measures += sys_meas

    return alignment, cumulative_measures


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def main() -> int:
    print(f"PDF : {PDF_PATH}")
    print(f"XML : {MXL_PATH}")
    print(f"Pages: {MVT1_FIRST_PAGE}-{MVT1_LAST_PAGE} (1-indexed)\n")

    print("── XML parse ──")
    xml_measures, num_parts = parse_xml_measures(MXL_PATH)
    print(f"XML: {len(xml_measures)} measures across {num_parts} parts")
    print(f"  first measure: number={xml_measures[0].number}, implicit={xml_measures[0].is_implicit}, "
          f"time_sig={xml_measures[0].time_signature}, key={xml_measures[0].key_fifths}, "
          f"clefs={xml_measures[0].clef_changes[:3]}...")
    print(f"  last measure:  number={xml_measures[-1].number}, barline={xml_measures[-1].barline_type}")
    print(f"  non-regular barlines: {sum(1 for m in xml_measures if m.barline_type != 'regular')}")

    repeat_info = classify_xml_repeat_style(xml_measures)
    print(f"  repeat style:  {repeat_info['style']}  ({repeat_info['repeat_count']} <repeat> elements)")
    print(f"    {repeat_info['notes']}")
    print()

    print("── PDF cell extraction ──")
    page_indices = list(range(MVT1_FIRST_PAGE - 1, MVT1_LAST_PAGE))  # 0-indexed
    per_page = extract_cells_for_range(PDF_PATH, page_indices, dpi=DPI)
    print()

    print("── Alignment ──")
    alignment, total_pdf_measures = build_alignment(per_page, xml_measures)
    expected_pdf = repeat_info["expected_pdf_measures"]
    print(f"PDF detected: {total_pdf_measures} measures across {len(per_page)} pages")
    print(f"XML measures: {len(xml_measures)}")
    print(f"Expected PDF: {expected_pdf}  (from XML count, repeat style = {repeat_info['style']})")
    delta = total_pdf_measures - expected_pdf
    if delta == 0:
        print("PDF count matches expected.")
    else:
        pct = 100.0 * delta / max(expected_pdf, 1)
        print(f"MISMATCH: PDF is {delta:+d} ({pct:+.1f}%) from expected.")
        if repeat_info["style"] == "expanded?" and delta < 0:
            print("  (negative delta + ambiguous repeat style — XML may have repeats written out;"
                  " check by hand.)")
    print()

    # Write the manifest
    manifest = {
        "pdf_path": str(PDF_PATH),
        "xml_path": str(MXL_PATH),
        "page_range_1indexed": [MVT1_FIRST_PAGE, MVT1_LAST_PAGE],
        "dpi": DPI,
        "xml_measure_count": len(xml_measures),
        "xml_repeat_style": repeat_info["style"],
        "xml_repeat_element_count": repeat_info["repeat_count"],
        "expected_pdf_measures": expected_pdf,
        "pdf_measure_count": total_pdf_measures,
        "delta": delta,
        "alignment": {
            str(m): cells for m, cells in alignment.items()
        },
        "per_page_summary": [
            {k: v for k, v in p.items() if k != "cells"} | {"cell_count": len(p.get("cells", []))}
            for p in per_page
        ],
        "xml_measures_summary": [asdict(m) for m in xml_measures[:5]] + ["..."] + [asdict(m) for m in xml_measures[-3:]],
    }
    out_path = OUT_DIR / "cell_alignment.json"
    out_path.write_text(json.dumps(manifest, indent=2, default=str))
    print(f"Wrote {out_path}")
    return 0 if delta == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
