"""
OMR pipeline — core functions for the /engrave skill.

Usage as CLI:
    python omr_pipeline.py extract <pdf_path> [output_dir]
    python omr_pipeline.py assemble <fragments_dir> <output_path>
    python omr_pipeline.py diff <musicxml_a> <musicxml_b>
    python omr_pipeline.py patch <base_musicxml> <corrections_json> <output_dir>
    python omr_pipeline.py engrave <musicxml_path> <output_dir>
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from typing import Optional

from config import OUTPUT_DIR, PDF_DPI
from musicxml_builder import build_document, load_all_pages, validate_musicxml


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class MeasureData:
    """A single measure extracted from a MusicXML file."""

    def __init__(self, part_id: str, part_name: str, measure_number: int,
                 xml_content: str, notes_hash: str):
        self.part_id = part_id
        self.part_name = part_name
        self.measure_number = measure_number
        self.xml_content = xml_content
        self.notes_hash = notes_hash

    def __repr__(self):
        return f"MeasureData({self.part_id}, m{self.measure_number}, hash={self.notes_hash[:8]})"


class DiffResult:
    """Result of comparing two sets of measures."""

    def __init__(self):
        self.agreements: list[dict] = []
        self.disagreements: list[dict] = []
        self.only_in_a: list[dict] = []
        self.only_in_b: list[dict] = []

    def summary(self) -> str:
        total = len(self.agreements) + len(self.disagreements)
        return (
            f"{len(self.agreements)}/{total} measures agree, "
            f"{len(self.disagreements)} disagreements"
        )

    def to_dict(self) -> dict:
        return {
            "summary": self.summary(),
            "total_measures": len(self.agreements) + len(self.disagreements),
            "agreements": self.agreements,
            "disagreements": self.disagreements,
            "only_in_engine_a": self.only_in_a,
            "only_in_engine_b": self.only_in_b,
        }


# ---------------------------------------------------------------------------
# Phase 1: PDF → page images
# ---------------------------------------------------------------------------


def extract_pages(pdf_path: str, output_dir: str | None = None) -> list[str]:
    """Convert each PDF page to a PNG image.

    Returns list of PNG file paths.
    """
    from pdf2image import convert_from_path

    if output_dir is None:
        output_dir = os.path.join(OUTPUT_DIR, "pages")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    images = convert_from_path(pdf_path, dpi=PDF_DPI)
    paths = []
    for i, img in enumerate(images):
        out_path = os.path.join(output_dir, f"page_{i + 1:03d}.png")
        img.save(out_path, "PNG")
        paths.append(out_path)
        print(f"  Extracted page {i + 1}/{len(images)}")

    return paths


# ---------------------------------------------------------------------------
# Phase 3: Assemble & Diff
# ---------------------------------------------------------------------------


def assemble_from_claude_vision(fragments_dir: str, output_path: str) -> str:
    """Assemble Claude Vision's page JSONs into a complete MusicXML file."""
    pages = load_all_pages(fragments_dir)
    if not pages:
        raise FileNotFoundError(f"No page_*.json files in {fragments_dir}")

    xml_str = build_document(pages)
    warnings = validate_musicxml(xml_str)
    if warnings:
        print(f"  MusicXML validation warnings:")
        for w in warnings:
            print(f"    - {w}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_str)

    print(f"  Assembled MusicXML: {output_path}")
    return output_path


def parse_measures(musicxml_path: str) -> list[MeasureData]:
    """Extract per-measure, per-part data from a MusicXML file.

    Returns a list of MeasureData with normalized note hashes for comparison.
    """
    tree = ET.parse(musicxml_path)
    root = tree.getroot()

    # Handle namespaced MusicXML
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"

    # Build part name lookup
    part_names: dict[str, str] = {}
    for sp in root.iter(f"{ns}score-part"):
        pid = sp.get("id", "")
        name_el = sp.find(f"{ns}part-name")
        part_names[pid] = name_el.text if name_el is not None and name_el.text else pid

    measures: list[MeasureData] = []
    for part in root.iter(f"{ns}part"):
        pid = part.get("id", "unknown")
        pname = part_names.get(pid, pid)

        for measure in part.iter(f"{ns}measure"):
            num_str = measure.get("number", "0")
            try:
                num = int(num_str)
            except ValueError:
                continue

            xml_content = ET.tostring(measure, encoding="unicode")
            notes_hash = _compute_notes_hash(measure, ns)

            measures.append(MeasureData(
                part_id=pid,
                part_name=pname,
                measure_number=num,
                xml_content=xml_content,
                notes_hash=notes_hash,
            ))

    return measures


def diff_measures(measures_a: list[MeasureData], measures_b: list[MeasureData],
                  engine_a: str = "claude_vision", engine_b: str = "oemer") -> DiffResult:
    """Structurally compare two sets of measures.

    Uses notes_hash for fast equality, then detailed comparison for disagreements.
    """
    result = DiffResult()

    # Index by (part_id, measure_number)
    index_a: dict[tuple[str, int], MeasureData] = {
        (m.part_id, m.measure_number): m for m in measures_a
    }
    index_b: dict[tuple[str, int], MeasureData] = {
        (m.part_id, m.measure_number): m for m in measures_b
    }

    all_keys = set(index_a.keys()) | set(index_b.keys())

    for key in sorted(all_keys):
        part_id, measure_num = key
        a = index_a.get(key)
        b = index_b.get(key)

        if a and not b:
            result.only_in_a.append({
                "part_id": part_id,
                "part_name": a.part_name,
                "measure": measure_num,
                "engine": engine_a,
                "xml": a.xml_content,
            })
        elif b and not a:
            result.only_in_b.append({
                "part_id": part_id,
                "part_name": b.part_name,
                "measure": measure_num,
                "engine": engine_b,
                "xml": b.xml_content,
            })
        elif a.notes_hash == b.notes_hash:
            result.agreements.append({
                "part_id": part_id,
                "part_name": a.part_name,
                "measure": measure_num,
                "notes_hash": a.notes_hash,
            })
        else:
            # Disagreement — compute detailed diff
            detail = _detailed_diff(a, b)
            result.disagreements.append({
                "part_id": part_id,
                "part_name": a.part_name,
                "measure": measure_num,
                "engine_a": engine_a,
                "engine_b": engine_b,
                "engine_a_xml": a.xml_content,
                "engine_b_xml": b.xml_content,
                "diff_details": detail,
            })

    return result


# ---------------------------------------------------------------------------
# Phase 5: Patch & Export
# ---------------------------------------------------------------------------


def apply_corrections(base_musicxml: str, corrections: list[dict],
                      output_path: str) -> str:
    """Apply accepted corrections to a MusicXML file.

    Each correction dict:
        {
            "part_id": "P1",
            "measure": 5,
            "action": "replace",        # replace | keep
            "replacement_xml": "<measure>...</measure>",  # only for replace
        }
    """
    tree = ET.parse(base_musicxml)
    root = tree.getroot()

    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"

    applied = 0
    for correction in corrections:
        if correction.get("action") != "replace":
            continue

        part_id = correction["part_id"]
        measure_num = correction["measure"]
        replacement_xml = correction["replacement_xml"]

        # Find the part
        target_part = None
        for part in root.iter(f"{ns}part"):
            if part.get("id") == part_id:
                target_part = part
                break

        if target_part is None:
            print(f"  Warning: part {part_id} not found, skipping correction")
            continue

        # Find the measure
        target_measure = None
        target_index = None
        for i, measure in enumerate(target_part):
            if measure.tag.endswith("measure") and measure.get("number") == str(measure_num):
                target_measure = measure
                target_index = i
                break

        if target_measure is None:
            print(f"  Warning: measure {measure_num} in part {part_id} not found")
            continue

        # Parse replacement and swap
        try:
            new_measure = ET.fromstring(replacement_xml)
        except ET.ParseError as e:
            print(f"  Warning: invalid replacement XML for m{measure_num}: {e}")
            continue

        target_part.remove(target_measure)
        target_part.insert(target_index, new_measure)
        applied += 1

    # Write output
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    ET.indent(root, space="  ")
    tree.write(output_path, encoding="unicode", xml_declaration=True)
    print(f"  Applied {applied}/{len(corrections)} corrections → {output_path}")
    return output_path


def engrave_pdf(musicxml_path: str, output_dir: str) -> tuple[str, str]:
    """Convert MusicXML → LilyPond → PDF.

    Returns (ly_path, pdf_path).
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    stem = Path(musicxml_path).stem

    ly_path = os.path.join(output_dir, f"{stem}.ly")
    pdf_path = os.path.join(output_dir, f"{stem}.pdf")

    # Step 1: MusicXML → LilyPond
    result = subprocess.run(
        ["musicxml2ly", "-o", ly_path, musicxml_path],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"musicxml2ly failed: {result.stderr[:500]}")
    print(f"  Converted to LilyPond: {ly_path}")

    # Step 2: LilyPond → PDF
    result = subprocess.run(
        ["lilypond", "-o", os.path.join(output_dir, stem), ly_path],
        capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(f"lilypond failed: {result.stderr[:500]}")

    if not os.path.isfile(pdf_path):
        # LilyPond sometimes appends .pdf automatically
        candidates = list(Path(output_dir).glob(f"{stem}*.pdf"))
        if candidates:
            pdf_path = str(candidates[0])
        else:
            raise RuntimeError("LilyPond produced no PDF output")

    print(f"  Engraved PDF: {pdf_path}")
    return ly_path, pdf_path


# ---------------------------------------------------------------------------
# Notes hash computation
# ---------------------------------------------------------------------------


def _compute_notes_hash(measure: ET.Element, ns: str = "") -> str:
    """Compute a SHA256 hash of the musically significant content in a measure.

    Extracts notes/rests with pitch, octave, duration, and accidental,
    producing a stable hash for equality comparison.
    """
    note_tuples = []

    for note in measure.iter(f"{ns}note"):
        # Skip grace notes in hash (they're details, not structure)
        if note.find(f"{ns}grace") is not None:
            continue

        is_rest = note.find(f"{ns}rest") is not None
        is_chord = note.find(f"{ns}chord") is not None

        if is_rest:
            duration = _get_text(note, f"{ns}duration", "0")
            note_type = _get_text(note, f"{ns}type", "quarter")
            note_tuples.append(f"R:{duration}:{note_type}")
        else:
            pitch_el = note.find(f"{ns}pitch")
            if pitch_el is not None:
                step = _get_text(pitch_el, f"{ns}step", "C")
                octave = _get_text(pitch_el, f"{ns}octave", "4")
                alter = _get_text(pitch_el, f"{ns}alter", "0")
            else:
                step, octave, alter = "C", "4", "0"

            duration = _get_text(note, f"{ns}duration", "0")
            note_type = _get_text(note, f"{ns}type", "quarter")
            voice = _get_text(note, f"{ns}voice", "1")

            prefix = "C:" if is_chord else "N:"
            note_tuples.append(f"{prefix}{step}{alter}:{octave}:{duration}:{note_type}:{voice}")

    content = "|".join(note_tuples)
    return hashlib.sha256(content.encode()).hexdigest()


def _get_text(parent: ET.Element, tag: str, default: str = "") -> str:
    """Get text content of a child element."""
    el = parent.find(tag)
    return el.text.strip() if el is not None and el.text else default


# ---------------------------------------------------------------------------
# Detailed diff for disagreements
# ---------------------------------------------------------------------------


def _detailed_diff(a: MeasureData, b: MeasureData) -> list[dict]:
    """Produce a human-readable list of differences between two measures."""
    diffs = []

    notes_a = _extract_note_list(a.xml_content)
    notes_b = _extract_note_list(b.xml_content)

    max_len = max(len(notes_a), len(notes_b))
    for i in range(max_len):
        na = notes_a[i] if i < len(notes_a) else None
        nb = notes_b[i] if i < len(notes_b) else None

        if na is None:
            diffs.append({"type": "extra_note", "engine": "b", "note": nb})
        elif nb is None:
            diffs.append({"type": "extra_note", "engine": "a", "note": na})
        elif na != nb:
            diffs.append({"type": "note_mismatch", "position": i + 1, "a": na, "b": nb})

    return diffs


def _extract_note_list(xml_str: str) -> list[str]:
    """Extract a simple note representation list from measure XML."""
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        return []

    notes = []
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"

    for note in root.iter(f"{ns}note"):
        if note.find(f"{ns}rest") is not None:
            dur = _get_text(note, f"{ns}type", "quarter")
            notes.append(f"rest-{dur}")
        else:
            pitch_el = note.find(f"{ns}pitch")
            if pitch_el is not None:
                step = _get_text(pitch_el, f"{ns}step", "?")
                octave = _get_text(pitch_el, f"{ns}octave", "?")
                alter = _get_text(pitch_el, f"{ns}alter", "")
                acc = ""
                if alter == "-1":
                    acc = "b"
                elif alter == "1":
                    acc = "#"
                dur = _get_text(note, f"{ns}type", "quarter")
                chord = "+" if note.find(f"{ns}chord") is not None else ""
                notes.append(f"{chord}{step}{acc}{octave}-{dur}")

    return notes


# ---------------------------------------------------------------------------
# CLI interface
# ---------------------------------------------------------------------------


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "extract":
        pdf_path = sys.argv[2]
        output_dir = sys.argv[3] if len(sys.argv) > 3 else None
        paths = extract_pages(pdf_path, output_dir)
        print(json.dumps(paths))

    elif cmd == "assemble":
        fragments_dir = sys.argv[2]
        output_path = sys.argv[3]
        assemble_from_claude_vision(fragments_dir, output_path)

    elif cmd == "diff":
        musicxml_a = sys.argv[2]
        musicxml_b = sys.argv[3]
        measures_a = parse_measures(musicxml_a)
        measures_b = parse_measures(musicxml_b)
        result = diff_measures(measures_a, measures_b)
        print(json.dumps(result.to_dict(), indent=2))

    elif cmd == "parse":
        musicxml_path = sys.argv[2]
        measures = parse_measures(musicxml_path)
        print(f"Parsed {len(measures)} measures:")
        for m in measures:
            print(f"  {m.part_id} m{m.measure_number}: {m.notes_hash[:12]}...")

    elif cmd == "patch":
        base = sys.argv[2]
        corrections_json = sys.argv[3]
        output_dir = sys.argv[4] if len(sys.argv) > 4 else OUTPUT_DIR
        with open(corrections_json) as f:
            corrections = json.load(f)
        output_path = os.path.join(output_dir, "corrected.xml")
        apply_corrections(base, corrections, output_path)

    elif cmd == "engrave":
        musicxml_path = sys.argv[2]
        output_dir = sys.argv[3] if len(sys.argv) > 3 else OUTPUT_DIR
        ly_path, pdf_path = engrave_pdf(musicxml_path, output_dir)
        print(json.dumps({"ly": ly_path, "pdf": pdf_path}))

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
