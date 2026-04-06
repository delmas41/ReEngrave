"""
MusicXML builder — assembles Claude Vision's per-page JSON output into valid MusicXML.

Expected input format (per page JSON):
{
  "page": 1,
  "header": {                          # only on page 1
    "title": "...",
    "composer": "...",
    "tempo": "Allegro",
    "key": "C major",
    "time": "4/4"
  },
  "parts": [
    {
      "part_id": "P1",
      "part_name": "Violin I",
      "clef": "treble",
      "measures": [
        {"number": 1, "xml": "<measure number=\"1\">...</measure>"}
      ]
    }
  ]
}
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET


# ---------------------------------------------------------------------------
# Key/time signature helpers
# ---------------------------------------------------------------------------

_KEY_MAP = {
    "C major": 0, "G major": 1, "D major": 2, "A major": 3,
    "E major": 4, "B major": 5, "F# major": 6, "C# major": 7,
    "F major": -1, "Bb major": -2, "Eb major": -3, "Ab major": -4,
    "Db major": -5, "Gb major": -6, "Cb major": -7,
    "A minor": 0, "E minor": 1, "B minor": 2, "F# minor": 3,
    "C# minor": 4, "G# minor": 5, "D# minor": 6, "A# minor": 7,
    "D minor": -1, "G minor": -2, "C minor": -3, "F minor": -4,
    "Bb minor": -5, "Eb minor": -6, "Ab minor": -7,
}

_CLEF_MAP = {
    "treble": ("G", 2),
    "bass": ("F", 4),
    "alto": ("C", 3),
    "tenor": ("C", 4),
}


def _key_fifths(key_str: str) -> int:
    return _KEY_MAP.get(key_str, 0)


def _key_mode(key_str: str) -> str:
    return "minor" if "minor" in key_str.lower() else "major"


def _parse_time(time_str: str) -> tuple[str, str]:
    """Parse '4/4' into ('4', '4')."""
    parts = time_str.split("/")
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return "4", "4"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_document(page_results: list[dict]) -> str:
    """Assemble per-page JSON results into a complete MusicXML document.

    Args:
        page_results: List of page JSON dicts, sorted by page number.

    Returns:
        Complete MusicXML string.
    """
    if not page_results:
        raise ValueError("No page results to assemble")

    page_results = sorted(page_results, key=lambda p: p.get("page", 0))
    first_page = page_results[0]
    header = first_page.get("header", {})

    # Collect all unique parts across pages (page 1 defines the canonical list)
    parts_registry: dict[str, str] = {}  # part_id -> part_name
    for part in first_page.get("parts", []):
        parts_registry[part["part_id"]] = part.get("part_name", part["part_id"])

    # Build the document
    root = ET.Element("score-partwise", version="4.0")

    # Work section
    work = ET.SubElement(root, "work")
    ET.SubElement(work, "work-title").text = header.get("title", "Untitled")

    # Identification
    ident = ET.SubElement(root, "identification")
    creator = ET.SubElement(ident, "creator", type="composer")
    creator.text = header.get("composer", "Unknown")

    # Part list
    part_list = ET.SubElement(root, "part-list")
    for pid, pname in parts_registry.items():
        sp = ET.SubElement(part_list, "score-part", id=pid)
        ET.SubElement(sp, "part-name").text = pname

    # Collect measures per part across all pages
    part_measures: dict[str, list[str]] = {pid: [] for pid in parts_registry}

    for page in page_results:
        for part_data in page.get("parts", []):
            pid = part_data["part_id"]
            if pid not in part_measures:
                # Part appeared on a later page but not page 1 — add it
                parts_registry[pid] = part_data.get("part_name", pid)
                part_measures[pid] = []
                sp = ET.SubElement(part_list, "score-part", id=pid)
                ET.SubElement(sp, "part-name").text = parts_registry[pid]

            for m in part_data.get("measures", []):
                xml_str = m.get("xml", "")
                if xml_str.strip():
                    part_measures[pid].append(xml_str)

    # Build part elements with their measures
    for pid in parts_registry:
        part_el = ET.SubElement(root, "part", id=pid)
        measures = part_measures.get(pid, [])

        if not measures:
            # Empty part — add a single empty measure
            empty = ET.SubElement(part_el, "measure", number="1")
            _add_attributes_element(
                empty,
                header.get("key", "C major"),
                header.get("time", "4/4"),
                _CLEF_MAP.get("treble", ("G", 2)),
            )
            continue

        for i, measure_xml in enumerate(measures):
            measure_el = _parse_measure_xml(measure_xml)
            if measure_el is None:
                continue

            # Inject attributes on the first measure if not present
            if i == 0 and measure_el.find("attributes") is None:
                clef_name = "treble"
                for page in page_results:
                    for pd in page.get("parts", []):
                        if pd["part_id"] == pid:
                            clef_name = pd.get("clef", "treble")
                            break

                _add_attributes_element(
                    measure_el,
                    header.get("key", "C major"),
                    header.get("time", "4/4"),
                    _CLEF_MAP.get(clef_name, ("G", 2)),
                    insert_at=0,
                )

            part_el.append(measure_el)

    return _serialize(root)


def validate_musicxml(xml_string: str) -> list[str]:
    """Basic structural validation of a MusicXML string.

    Returns a list of warning messages (empty = valid).
    """
    warnings = []

    try:
        root = ET.fromstring(xml_string)
    except ET.ParseError as e:
        return [f"XML parse error: {e}"]

    if root.tag != "score-partwise":
        warnings.append(f"Expected root <score-partwise>, got <{root.tag}>")

    part_list = root.find("part-list")
    if part_list is None:
        warnings.append("Missing <part-list>")
    else:
        declared_parts = {sp.get("id") for sp in part_list.findall("score-part")}
        actual_parts = {p.get("id") for p in root.findall("part")}
        missing = declared_parts - actual_parts
        extra = actual_parts - declared_parts
        if missing:
            warnings.append(f"Declared but missing parts: {missing}")
        if extra:
            warnings.append(f"Undeclared parts: {extra}")

    for part in root.findall("part"):
        measures = part.findall("measure")
        if not measures:
            warnings.append(f"Part {part.get('id')} has no measures")

        # Check measure numbering
        numbers = []
        for m in measures:
            num = m.get("number")
            if num is not None:
                try:
                    numbers.append(int(num))
                except ValueError:
                    warnings.append(f"Non-integer measure number: {num}")

        if numbers and numbers != sorted(numbers):
            warnings.append(f"Part {part.get('id')}: measure numbers not in order")

    return warnings


def load_page_json(path: str) -> dict:
    """Load a page JSON file produced by Claude Vision OMR."""
    with open(path) as f:
        return json.load(f)


def load_all_pages(directory: str) -> list[dict]:
    """Load all page_NNN.json files from a directory, sorted by page number."""
    pages = []
    for p in sorted(Path(directory).glob("page_*.json")):
        pages.append(load_page_json(str(p)))
    return pages


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_measure_xml(xml_str: str) -> ET.Element | None:
    """Parse a <measure> XML fragment. Handles common issues."""
    xml_str = xml_str.strip()
    if not xml_str:
        return None

    # If wrapped in markdown code fences, strip them
    if xml_str.startswith("```"):
        lines = xml_str.split("\n")
        xml_str = "\n".join(lines[1:-1] if len(lines) > 2 else lines)

    try:
        return ET.fromstring(xml_str)
    except ET.ParseError:
        # Try wrapping in a root element if it's fragments
        try:
            return ET.fromstring(f"<measure>{xml_str}</measure>")
        except ET.ParseError:
            return None


def _add_attributes_element(
    measure: ET.Element,
    key: str,
    time: str,
    clef: tuple[str, int],
    insert_at: int = 0,
) -> None:
    """Insert a <attributes> element into a measure."""
    attrs = ET.Element("attributes")

    divisions = ET.SubElement(attrs, "divisions")
    divisions.text = "1"

    key_el = ET.SubElement(attrs, "key")
    ET.SubElement(key_el, "fifths").text = str(_key_fifths(key))
    ET.SubElement(key_el, "mode").text = _key_mode(key)

    beats, beat_type = _parse_time(time)
    time_el = ET.SubElement(attrs, "time")
    ET.SubElement(time_el, "beats").text = beats
    ET.SubElement(time_el, "beat-type").text = beat_type

    clef_el = ET.SubElement(attrs, "clef")
    ET.SubElement(clef_el, "sign").text = clef[0]
    ET.SubElement(clef_el, "line").text = str(clef[1])

    measure.insert(insert_at, attrs)


def _serialize(root: ET.Element) -> str:
    """Serialize an ElementTree to a MusicXML string with declaration."""
    ET.indent(root, space="  ")
    xml_bytes = ET.tostring(root, encoding="unicode", xml_declaration=False)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + \
           '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" ' + \
           '"http://www.musicxml.org/dtds/partwise.dtd">\n' + \
           xml_bytes
