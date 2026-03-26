"""
LilyPond engraving module.
Converts MusicXML to LilyPond source and engraves to PDF.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)


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

    After conversion, injects a \\header block with title/composer metadata
    extracted from the MusicXML file.

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

    metadata = _extract_musicxml_metadata(musicxml_path)
    _inject_lilypond_header(ly_path, metadata)

    return ly_path


async def engrave_score(ly_path: str, output_dir: str) -> EngraveResult:
    """Run LilyPond on a .ly source file to produce a PDF."""
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
            logger.warning("Part extraction error for %s: %s", instrument_name, exc)

    return result


async def generate_full_pipeline(
    musicxml_path: str, output_dir: str
) -> EngraveResult:
    """Orchestrate the full MusicXML -> LilyPond -> PDF pipeline."""
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

    try:
        parts_dir = os.path.join(output_dir, "parts")
        parts_pdf_paths = await extract_parts(musicxml_path, parts_dir)
        result.parts_pdf_paths = parts_pdf_paths
    except Exception as exc:
        logger.warning("Part extraction failed (non-fatal): %s", exc)

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_musicxml_metadata(musicxml_path: str) -> dict:
    """Extract title, composer, and movement number from a MusicXML file."""
    try:
        tree = ET.parse(musicxml_path)
        root = tree.getroot()
        ns = _detect_namespace(root)

        metadata: dict = {}

        # Work title
        work_el = root.find(f"{ns}work") or root.find("work")
        if work_el is not None:
            title_el = work_el.find(f"{ns}work-title") or work_el.find("work-title")
            if title_el is not None and title_el.text:
                metadata["title"] = title_el.text.strip()
            number_el = work_el.find(f"{ns}work-number") or work_el.find("work-number")
            if number_el is not None and number_el.text:
                metadata["opus"] = number_el.text.strip()

        # Movement title (overrides work title if present)
        mv_el = root.find(f"{ns}movement-title") or root.find("movement-title")
        if mv_el is not None and mv_el.text:
            metadata["subtitle"] = mv_el.text.strip()

        # Identification block: composer, arranger, etc.
        id_el = root.find(f"{ns}identification") or root.find("identification")
        if id_el is not None:
            for creator in id_el.findall(f"{ns}creator") or id_el.findall("creator"):
                ctype = creator.get("type", "").lower()
                if ctype == "composer" and creator.text:
                    metadata["composer"] = creator.text.strip()
                elif ctype == "arranger" and creator.text:
                    metadata["arranger"] = creator.text.strip()

        return metadata
    except Exception as exc:
        logger.warning("Could not extract MusicXML metadata: %s", exc)
        return {}


def _inject_lilypond_header(ly_path: str, metadata: dict) -> None:
    """Inject a \\header block into a LilyPond source file.

    Inserts after the \\version statement (if present) or at the top.
    Skips injection if an existing \\header block is already present.
    """
    if not metadata:
        return

    try:
        with open(ly_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return

    # Don't overwrite an existing header
    if re.search(r"\\header\s*\{", content):
        return

    lines = []
    if "title" in metadata:
        title = metadata["title"].replace('"', '\\"')
        lines.append(f'  title = "{title}"')
    if "subtitle" in metadata:
        subtitle = metadata["subtitle"].replace('"', '\\"')
        lines.append(f'  subtitle = "{subtitle}"')
    if "composer" in metadata:
        composer = metadata["composer"].replace('"', '\\"')
        lines.append(f'  composer = "{composer}"')
    if "opus" in metadata:
        opus = metadata["opus"].replace('"', '\\"')
        lines.append(f'  opus = "{opus}"')
    if "arranger" in metadata:
        arranger = metadata["arranger"].replace('"', '\\"')
        lines.append(f'  arranger = "arr. {arranger}"')

    if not lines:
        return

    header_block = "\\header {\n" + "\n".join(lines) + "\n}\n\n"

    # Insert after the \version line, or at the start of the file
    version_match = re.search(r'\\version\s+"[^"]+"\s*\n', content)
    if version_match:
        pos = version_match.end()
        content = content[:pos] + "\n" + header_block + content[pos:]
    else:
        content = header_block + content

    try:
        with open(ly_path, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError as exc:
        logger.warning("Could not write LilyPond header to %s: %s", ly_path, exc)


def _detect_namespace(root: ET.Element) -> str:
    tag = root.tag
    if tag.startswith("{"):
        return tag[: tag.index("}") + 1]
    return ""


def _parse_parts(musicxml_path: str) -> dict[str, str]:
    """Return {part_id: instrument_name} from a MusicXML <part-list>."""
    try:
        tree = ET.parse(musicxml_path)
        root = tree.getroot()
        ns = _detect_namespace(root)

        parts: dict[str, str] = {}
        part_list = root.find(f"{ns}part-list") or root.find("part-list")

        if part_list is not None:
            for sp in part_list.findall(f"{ns}score-part") or part_list.findall("score-part"):
                part_id = sp.get("id", "")
                name_el = sp.find(f"{ns}part-name") or sp.find("part-name")
                instrument_name = (
                    name_el.text.strip()
                    if name_el is not None and name_el.text
                    else part_id
                )
                parts[part_id] = instrument_name

        return parts
    except Exception:
        return {}


def _extract_single_part(
    musicxml_path: str, part_id: str, instrument_name: str
) -> str:
    """Extract a single part from a MusicXML file and return as XML string.

    Handles both score-partwise and score-timewise formats.
    Preserves global directives from the first measure (time, key, clef).
    """
    tree = ET.parse(musicxml_path)
    root = tree.getroot()
    ns = _detect_namespace(root)

    root_tag = root.tag.lower().replace(ns.strip("{}"), "").strip("{}")
    is_timewise = "timewise" in root_tag

    if is_timewise:
        return _extract_part_timewise(root, ns, part_id)

    # score-partwise (default): remove all other <part> elements
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


def _extract_part_timewise(
    root: ET.Element, ns: str, part_id: str
) -> str:
    """Extract a single part from a score-timewise MusicXML document.

    Converts to score-partwise format for LilyPond compatibility:
    Collects all <note>/<direction>/etc. for the target part_id across
    all <measure> elements and builds a partwise structure.
    """
    # Build a new score-partwise root
    new_root_tag = f"{ns}score-partwise" if ns else "score-partwise"
    new_root = ET.Element(new_root_tag)
    if root.get("version"):
        new_root.set("version", root.get("version"))

    # Copy header elements (work, movement-title, identification, etc.)
    skip_tags = {f"{ns}measure", "measure", f"{ns}part-list", "part-list"}
    for child in root:
        if child.tag not in skip_tags:
            new_root.append(child)

    # Copy part-list, filtered to this part only
    part_list_src = root.find(f"{ns}part-list") or root.find("part-list")
    if part_list_src is not None:
        new_pl_tag = f"{ns}part-list" if ns else "part-list"
        new_pl = ET.SubElement(new_root, new_pl_tag)
        for sp in part_list_src.findall(f"{ns}score-part") or part_list_src.findall("score-part"):
            if sp.get("id") == part_id:
                new_pl.append(sp)

    # Build the single <part> by collecting measures
    new_part_tag = f"{ns}part" if ns else "part"
    new_part = ET.SubElement(new_root, new_part_tag)
    new_part.set("id", part_id)

    for measure_el in root.findall(f"{ns}measure") or root.findall("measure"):
        new_measure_tag = f"{ns}measure" if ns else "measure"
        new_measure = ET.SubElement(new_part, new_measure_tag)
        for attr_name, attr_val in measure_el.attrib.items():
            new_measure.set(attr_name, attr_val)

        for part_el in measure_el.findall(f"{ns}part") or measure_el.findall("part"):
            if part_el.get("id") == part_id:
                for child in part_el:
                    new_measure.append(child)

    return ET.tostring(new_root, encoding="unicode", xml_declaration=True)
