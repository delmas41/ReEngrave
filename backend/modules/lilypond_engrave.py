"""
LilyPond engraving module.
Converts MusicXML to LilyPond source and engraves to PDF.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class EngraveResult:
    full_score_pdf_path: str
    parts_pdf_paths: dict[str, str] = field(default_factory=dict)
    ly_source_path: str = ""
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def musicxml_to_lilypond(musicxml_path: str, output_dir: str) -> str:
    """Convert a MusicXML file to LilyPond source using musicxml2ly.

    musicxml2ly ships with LilyPond and is available on PATH after installation.
    Returns the path to the generated .ly file.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    stem = Path(musicxml_path).stem
    ly_path = os.path.join(output_dir, f"{stem}.ly")

    proc = await asyncio.create_subprocess_exec(
        "musicxml2ly",
        "--output", ly_path,
        musicxml_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        err = stderr.decode("utf-8", errors="replace")
        raise RuntimeError(
            f"musicxml2ly failed (code {proc.returncode}): {err[-500:]}"
        )

    if not os.path.isfile(ly_path):
        raise FileNotFoundError(
            f"musicxml2ly did not produce expected output at {ly_path}"
        )

    # TODO: Post-process .ly to add ReEngrave header with title/composer/era
    # and apply any style overrides (e.g., paper size, font, engraving settings).

    return ly_path


async def engrave_score(ly_path: str, output_dir: str) -> EngraveResult:
    """Run LilyPond on a .ly source file to produce a PDF.

    Command: lilypond --output={output_dir} {ly_path}
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    proc = await asyncio.create_subprocess_exec(
        "lilypond",
        f"--output={output_dir}",
        ly_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    stem = Path(ly_path).stem
    pdf_path = os.path.join(output_dir, f"{stem}.pdf")

    if proc.returncode != 0 or not os.path.isfile(pdf_path):
        err = stderr.decode("utf-8", errors="replace")
        return EngraveResult(
            full_score_pdf_path="",
            ly_source_path=ly_path,
            error_message=f"LilyPond failed (code {proc.returncode}): {err[-500:]}",
        )

    return EngraveResult(
        full_score_pdf_path=pdf_path,
        ly_source_path=ly_path,
        error_message=None,
    )


async def extract_parts(musicxml_path: str, output_dir: str) -> dict[str, str]:
    """Split a MusicXML score into individual instrument parts and engrave each.

    Parses the MusicXML <part-list> to find instrument names, writes a
    separate MusicXML file per part, converts each to .ly, and engraves.

    Returns a dict mapping instrument_name -> pdf_path.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    parts = _parse_parts(musicxml_path)
    result: dict[str, str] = {}

    for part_id, instrument_name in parts.items():
        part_xml = _extract_single_part(musicxml_path, part_id, instrument_name)
        safe_name = instrument_name.replace(" ", "_").replace("/", "-")
        part_xml_path = os.path.join(output_dir, f"{safe_name}.xml")

        with open(part_xml_path, "w", encoding="utf-8") as f:
            f.write(part_xml)

        try:
            ly_path = await musicxml_to_lilypond(part_xml_path, output_dir)
            engrave_result = await engrave_score(ly_path, output_dir)
            if engrave_result.full_score_pdf_path:
                result[instrument_name] = engrave_result.full_score_pdf_path
        except Exception as exc:
            # TODO: Log per-part errors without aborting entire extraction
            print(f"[extract_parts] Error for part {instrument_name}: {exc}")

    return result


async def generate_full_pipeline(
    musicxml_path: str, output_dir: str
) -> EngraveResult:
    """Orchestrate the full MusicXML -> LilyPond -> PDF pipeline.

    Steps:
    1. Convert MusicXML to .ly (musicxml2ly)
    2. Engrave full score to PDF (lilypond)
    3. Extract and engrave individual parts (optional)
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    try:
        ly_path = await musicxml_to_lilypond(musicxml_path, output_dir)
    except Exception as exc:
        return EngraveResult(
            full_score_pdf_path="",
            error_message=f"musicxml2ly error: {exc}",
        )

    result = await engrave_score(ly_path, output_dir)
    if result.error_message:
        return result

    # Extract parts in parallel with the main engrave
    try:
        parts_dir = os.path.join(output_dir, "parts")
        parts_pdf_paths = await extract_parts(musicxml_path, parts_dir)
        result.parts_pdf_paths = parts_pdf_paths
    except Exception as exc:
        # TODO: Partial failure – log but don't fail the whole pipeline
        print(f"[generate_full_pipeline] Part extraction failed: {exc}")

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_parts(musicxml_path: str) -> dict[str, str]:
    """Return {part_id: instrument_name} from a MusicXML <part-list>."""
    try:
        tree = ET.parse(musicxml_path)
        root = tree.getroot()
        ns = _detect_namespace(root)

        parts: dict[str, str] = {}
        part_list = root.find(f"{ns}part-list")
        if part_list is None:
            part_list = root.find("part-list")

        if part_list is not None:
            for score_part in part_list.findall(f"{ns}score-part") or part_list.findall("score-part"):
                part_id = score_part.get("id", "")
                name_el = score_part.find(f"{ns}part-name") or score_part.find("part-name")
                instrument_name = name_el.text.strip() if name_el is not None and name_el.text else part_id
                parts[part_id] = instrument_name

        return parts
    except Exception:
        return {}


def _detect_namespace(root: ET.Element) -> str:
    """Return XML namespace prefix like '{http://...}' or ''."""
    tag = root.tag
    if tag.startswith("{"):
        return tag[:tag.index("}") + 1]
    return ""


def _extract_single_part(
    musicxml_path: str, part_id: str, instrument_name: str
) -> str:
    """Extract a single part from a MusicXML file and return as XML string.

    TODO: Properly handle score-partwise vs score-timewise format.
    TODO: Preserve global directives (time, key, clef) in extracted part.
    """
    tree = ET.parse(musicxml_path)
    root = tree.getroot()
    ns = _detect_namespace(root)

    # Remove all other <part> elements
    parts_to_remove = [
        p for p in root.findall(f"{ns}part") or root.findall("part")
        if p.get("id") != part_id
    ]
    for p in parts_to_remove:
        root.remove(p)

    # Update part-list to only include this part
    part_list = root.find(f"{ns}part-list") or root.find("part-list")
    if part_list is not None:
        others = [
            sp for sp in
            (part_list.findall(f"{ns}score-part") or part_list.findall("score-part"))
            if sp.get("id") != part_id
        ]
        for sp in others:
            part_list.remove(sp)

    return ET.tostring(root, encoding="unicode", xml_declaration=True)
