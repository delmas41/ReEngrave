"""
Export module for ReEngrave.
Handles exporting corrected scores as MusicXML, LilyPond source, or engraved PDF.
"""

from __future__ import annotations

import os
import shutil
import zipfile
from enum import Enum
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import FlaggedDifference, Score
from modules.lilypond_engrave import generate_full_pipeline, musicxml_to_lilypond


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
    """Fetch score, apply accepted corrections, write corrected MusicXML.

    Returns the path to the output MusicXML file.
    """
    score = await _get_score(score_id, db)
    accepted_diffs = await _get_accepted_diffs(score_id, db)

    if not score.musicxml_path or not os.path.isfile(score.musicxml_path):
        raise FileNotFoundError(
            f"MusicXML source not found for score {score_id}"
        )

    # Decompress .mxl (ZIP-compressed MusicXML) to plain XML if needed
    source_xml_path = _ensure_plain_xml(score.musicxml_path, output_dir)

    out_path = os.path.join(output_dir, f"{score_id}_corrected.xml")
    await apply_corrections_to_musicxml(source_xml_path, accepted_diffs, out_path)
    return out_path


async def export_as_lilypond(
    score_id: str, output_dir: str, db: AsyncSession
) -> str:
    """Export corrected score as a LilyPond .ly source file.

    Returns the path to the .ly file.
    """
    # First produce corrected MusicXML
    xml_path = await export_as_musicxml(score_id, output_dir, db)

    # Convert to LilyPond
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

    Writes the corrected XML to *output_path*.

    TODO: Implement XML patching logic:
    1. Parse original MusicXML with ElementTree.
    2. For each accepted diff that has a human_edit_value, locate the
       corresponding <measure> by measure_number and instrument (part id).
    3. Replace the affected element(s) with the corrected fragment.
    4. For accept-without-edit diffs, keep the original OMR output as-is
       (the OMR is considered correct).
    5. Serialize back to XML with proper indentation and encoding.
    """
    # Stub: copy original file and note corrections as XML comments
    shutil.copy2(original_xml_path, output_path)

    if not accepted_diffs:
        return

    tree = ET.parse(output_path)
    root = tree.getroot()

    # TODO: Replace this comment-injection stub with real measure patching
    comment_lines = [
        f"Measure {d.measure_number} [{d.instrument}]: {d.difference_type} – {d.description}"
        for d in accepted_diffs
        if d.human_decision in ("accept", "edit")
    ]
    if comment_lines:
        header_comment = ET.Comment(
            " ReEngrave corrections applied:\n  "
            + "\n  ".join(comment_lines)
            + "\n"
        )
        root.insert(0, header_comment)

    tree.write(output_path, encoding="unicode", xml_declaration=True)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ensure_plain_xml(musicxml_path: str, output_dir: str) -> str:
    """If *musicxml_path* is a .mxl ZIP archive, extract the rootfile XML and
    return the path to the extracted plain-XML file. Otherwise return as-is."""
    if not musicxml_path.lower().endswith(".mxl"):
        return musicxml_path

    with zipfile.ZipFile(musicxml_path, "r") as zf:
        # The META-INF/container.xml lists the rootfile
        rootfile_name: str | None = None
        if "META-INF/container.xml" in zf.namelist():
            container = ET.fromstring(zf.read("META-INF/container.xml"))
            ns = {"oc": "urn:oasis:names:tc:opendocument:xmlns:container"}
            rf = container.find(".//oc:rootfile", ns) or container.find(".//rootfile")
            if rf is not None:
                rootfile_name = rf.get("full-path")

        if rootfile_name is None:
            # Fallback: pick the first .xml / .musicxml entry
            for name in zf.namelist():
                if name.lower().endswith((".xml", ".musicxml")) and not name.startswith("__"):
                    rootfile_name = name
                    break

        if rootfile_name is None:
            raise ValueError(f"Cannot locate rootfile XML inside {musicxml_path}")

        dest = os.path.join(output_dir, Path(rootfile_name).name)
        with zf.open(rootfile_name) as src, open(dest, "wb") as dst:
            shutil.copyfileobj(src, dst)

    return dest


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
