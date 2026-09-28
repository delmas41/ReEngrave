"""
Export module for ReEngrave.
Handles exporting corrected scores as MusicXML, LilyPond source, or engraved PDF.

When a score was produced by the local OMR pipeline (tools/omr), a
transcribe.py JSON is stashed at Score.metadata_json['omr_json_path'].
We prefer that path for LilyPond/PDF export because it skips a lossy
MusicXML → musicxml2ly hop. Falls back to the MusicXML→musicxml2ly
route when the JSON isn't available (e.g. for direct MusicXML uploads).
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
import zipfile
from enum import Enum
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import FlaggedDifference, Score
from modules.lilypond_engrave import (
    engrave_score,
    generate_full_pipeline,
    musicxml_to_lilypond,
)


logger = logging.getLogger(__name__)


# Make the `tools` package importable for tools.omr.export.to_lilypond.
# Two layouts to support:
#   * Docker:  /app/modules/export_module.py  → tools/ at /app/tools (parents[1])
#   * Dev:     <repo>/backend/modules/export_module.py  → tools/ at <repo>/tools (parents[2])
def _find_omr_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in (here.parents[1], here.parents[2]):
        if (candidate / "tools" / "omr").is_dir():
            return candidate
    return here.parents[2]


_REPO_ROOT = _find_omr_root()
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


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

    Preference order, each skipping the lossy musicxml2ly hop:
      1. ROADMAP 3.3/3.1 — a STAGED record (`omr_engine == "staged"`) via
         `tools.omr.staged.lilypond.to_lilypond`, the native staged
         exporter (see CLAUDE.md §3: STAGED is the product path).
      2. A LEGACY transcribe.py JSON via `tools.omr.export.to_lilypond`.
      3. Falls back to MusicXML → musicxml2ly when neither is on disk
         (e.g. direct MusicXML uploads).

    Returns the path to the .ly file.
    """
    score = await _get_score(score_id, db)
    record_path = _staged_record_path_for(score)

    if record_path and os.path.isfile(record_path):
        ly_path = os.path.join(output_dir, f"{score_id}_corrected.ly")
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        # lazy imports — same reasoning as the legacy `to_lilypond` import
        # below: a missing/heavy tools.omr dependency shouldn't break import
        # of this module.
        from tools.omr.staged import lilypond as staged_lilypond
        from tools.omr.staged import record_io
        omr_result = record_io.load_record(record_path)
        ly_str, _report = staged_lilypond.to_lilypond(omr_result)
        with open(ly_path, "w", encoding="utf-8") as fh:
            fh.write(ly_str)
        return ly_path

    omr_json_path = _omr_json_path_for(score)
    if omr_json_path and os.path.isfile(omr_json_path):
        ly_path = os.path.join(output_dir, f"{score_id}_corrected.ly")
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        from tools.omr.export import to_lilypond  # lazy import
        with open(omr_json_path, "r", encoding="utf-8") as fh:
            omr_result = json.load(fh)
        ly_str = to_lilypond(omr_result)
        with open(ly_path, "w", encoding="utf-8") as fh:
            fh.write(ly_str)
        return ly_path

    # Fallback path — MusicXML → musicxml2ly → .ly
    xml_path = await export_as_musicxml(score_id, output_dir, db)
    ly_path = await musicxml_to_lilypond(xml_path, output_dir)
    return ly_path


async def export_as_pdf(
    score_id: str, output_dir: str, db: AsyncSession
) -> str:
    """Run full LilyPond engrave pipeline and return PDF path.

    Same preference order as `export_as_lilypond`: a staged record, then a
    legacy OMR JSON, both via LilyPond → PDF, otherwise the MusicXML route.
    """
    score = await _get_score(score_id, db)
    record_path = _staged_record_path_for(score)
    omr_json_path = _omr_json_path_for(score)

    if ((record_path and os.path.isfile(record_path))
            or (omr_json_path and os.path.isfile(omr_json_path))):
        ly_path = await export_as_lilypond(score_id, output_dir, db)
        engrave_result = await engrave_score(ly_path, output_dir)
        if engrave_result.error_message:
            raise RuntimeError(f"Engraving failed: {engrave_result.error_message}")
        return engrave_result.full_score_pdf_path

    # Fallback path — MusicXML → musicxml2ly → LilyPond → PDF
    xml_path = await export_as_musicxml(score_id, output_dir, db)
    result = await generate_full_pipeline(xml_path, output_dir)
    if result.error_message:
        raise RuntimeError(f"Engraving failed: {result.error_message}")
    return result.full_score_pdf_path


def _omr_json_path_for(score: Score) -> str:
    """Return the path to the transcribe.py JSON for this score, or ""
    if not present. Stored on Score.metadata_json by the LEGACY OMR step.
    """
    meta = score.metadata_json or {}
    return str(meta.get("omr_json_path") or "")


def _staged_record_path_for(score: Score) -> str:
    """Return the path to the STAGED pipeline's pooled record for this
    score, or "" if not present. Stored on Score.metadata_json by
    `staged_omr.run_staged_omr` (ROADMAP 3.3) only when the score was
    processed with `omr_engine == "staged"` — a score reprocessed with
    `local` afterwards has no `omr_record_path` and falls through to the
    legacy branch below, as it should.
    """
    meta = score.metadata_json or {}
    if meta.get("omr_engine") != "staged":
        return ""
    return str(meta.get("omr_record_path") or "")


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
