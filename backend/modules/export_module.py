"""
Export module for ReEngrave.
Handles exporting corrected scores as MusicXML, LilyPond source, or engraved PDF.
"""

from __future__ import annotations

import logging
import os
import shutil
from enum import Enum
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import FlaggedDifference, Score
from modules.lilypond_engrave import generate_full_pipeline, musicxml_to_lilypond

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ExportFormat(str, Enum):
    PDF = "pdf"
    MUSICXML = "musicxml"
    LILYPOND = "lilypond"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def export_score(
    score_id: str,
    format: ExportFormat,
    output_dir: str,
    db: AsyncSession,
) -> str:
    """Main export dispatcher. Returns the path to the exported file."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    dispatch = {
        ExportFormat.MUSICXML: export_as_musicxml,
        ExportFormat.LILYPOND: export_as_lilypond,
        ExportFormat.PDF: export_as_pdf,
    }
    handler = dispatch[format]
    return await handler(score_id, output_dir, db)


async def export_as_musicxml(
    score_id: str, output_dir: str, db: AsyncSession
) -> str:
    """Fetch score, apply accepted corrections, write corrected MusicXML."""
    score = await _get_score(score_id, db)
    accepted_diffs = await _get_accepted_diffs(score_id, db)

    if not score.musicxml_path or not os.path.isfile(score.musicxml_path):
        raise FileNotFoundError(
            f"MusicXML source not found for score {score_id}"
        )

    out_path = os.path.join(output_dir, f"{score_id}_corrected.xml")
    await apply_corrections_to_musicxml(score.musicxml_path, accepted_diffs, out_path)
    return out_path


async def export_as_lilypond(
    score_id: str, output_dir: str, db: AsyncSession
) -> str:
    """Export corrected score as a LilyPond .ly source file."""
    xml_path = await export_as_musicxml(score_id, output_dir, db)
    ly_path = await musicxml_to_lilypond(xml_path, output_dir)
    return ly_path


async def export_as_pdf(
    score_id: str, output_dir: str, db: AsyncSession
) -> str:
    """Run full LilyPond engrave pipeline and return PDF path."""
    xml_path = await export_as_musicxml(score_id, output_dir, db)

    result = await generate_full_pipeline(xml_path, output_dir)
    if result.error_message:
        raise RuntimeError(f"Engraving failed: {result.error_message}")

    return result.full_score_pdf_path


async def apply_corrections_to_musicxml(
    original_xml_path: str,
    accepted_diffs: list[Any],
    output_path: str,
) -> None:
    """Apply human-accepted corrections to a MusicXML file.

    For diffs with human_decision == "accept": the OMR output is correct,
    no changes needed.

    For diffs with human_decision == "edit" and human_edit_value set:
    - If the value is a valid XML fragment, replace the matching measure's
      content with it.
    - Otherwise, annotate the measure with a comment containing the edit value.

    Writes the corrected XML to output_path.
    """
    shutil.copy2(original_xml_path, output_path)

    # Only edits require patching; accepts keep the OMR output as-is
    edit_diffs = [
        d for d in accepted_diffs
        if d.human_decision == "edit" and d.human_edit_value
    ]
    if not edit_diffs:
        return

    try:
        tree = ET.parse(output_path)
    except ET.ParseError as exc:
        logger.error("Failed to parse MusicXML for patching: %s", exc)
        return

    root = tree.getroot()
    ns = _detect_namespace(root)

    for diff in edit_diffs:
        measure_num = str(diff.measure_number)

        part = _find_part_for_instrument(root, ns, diff.instrument)
        if part is None:
            all_parts = root.findall(f"{ns}part") or root.findall("part")
            part = all_parts[0] if all_parts else None

        if part is None:
            logger.warning("No part found for instrument %s", diff.instrument)
            continue

        measure = _find_measure(part, ns, measure_num)
        if measure is None:
            logger.warning(
                "Measure %s not found for instrument %s", measure_num, diff.instrument
            )
            continue

        edit_val = diff.human_edit_value.strip()
        _apply_edit_to_measure(measure, ns, measure_num, edit_val)

    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="unicode", xml_declaration=True)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _detect_namespace(root: ET.Element) -> str:
    tag = root.tag
    if tag.startswith("{"):
        return tag[: tag.index("}") + 1]
    return ""


def _find_part_for_instrument(
    root: ET.Element, ns: str, instrument: str
) -> ET.Element | None:
    """Find the <part> element whose part-name matches instrument."""
    part_list = root.find(f"{ns}part-list") or root.find("part-list")
    if part_list is None:
        return None

    score_parts = part_list.findall(f"{ns}score-part") or part_list.findall("score-part")
    for sp in score_parts:
        name_el = sp.find(f"{ns}part-name") or sp.find("part-name")
        if name_el is not None and name_el.text:
            if instrument.lower() in name_el.text.lower():
                part_id = sp.get("id", "")
                for part in root.findall(f"{ns}part") or root.findall("part"):
                    if part.get("id") == part_id:
                        return part
    return None


def _find_measure(part: ET.Element, ns: str, measure_num: str) -> ET.Element | None:
    """Find a <measure number="N"> inside a part."""
    for m in part.findall(f"{ns}measure") or part.findall("measure"):
        if m.get("number") == measure_num:
            return m
    return None


def _apply_edit_to_measure(
    measure: ET.Element, ns: str, measure_num: str, edit_val: str
) -> None:
    """Apply a human edit value to a measure element.

    If edit_val is a valid XML fragment, replace the measure's children.
    Otherwise, append it as a comment.
    """
    if edit_val.startswith("<") and edit_val.endswith(">"):
        try:
            fragment = ET.fromstring(f"<_root>{edit_val}</_root>")
            # Preserve the measure's attributes, clear and replace children
            attribs = dict(measure.attrib)
            measure.clear()
            for key, val in attribs.items():
                measure.set(key, val)
            for child in fragment:
                measure.append(child)
            return
        except ET.ParseError:
            pass

    # Plain-text or unparseable XML: annotate with a comment
    measure.append(ET.Comment(f" ReEngrave edit: {edit_val} "))


async def _get_score(score_id: str, db: AsyncSession) -> Score:
    result = await db.execute(select(Score).where(Score.id == score_id))
    score = result.scalar_one_or_none()
    if score is None:
        raise ValueError(f"Score {score_id} not found")
    return score


async def _get_accepted_diffs(
    score_id: str, db: AsyncSession
) -> list[FlaggedDifference]:
    result = await db.execute(
        select(FlaggedDifference).where(
            FlaggedDifference.score_id == score_id,
            FlaggedDifference.human_decision.in_(["accept", "edit"]),
        )
    )
    return list(result.scalars().all())
