"""
Audiveris OMR (Optical Music Recognition) integration.
Runs Audiveris as a subprocess and parses its output.
"""

from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET


AUDIVERIS_HOME: str = os.getenv("AUDIVERIS_HOME", "/opt/Audiveris")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class AudiverisResult:
    musicxml_path: str
    book_path: str
    confidence_score: float
    measures_count: int
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def run_audiveris(pdf_path: str, output_dir: str) -> AudiverisResult:
    """Run Audiveris OMR on a PDF and return a structured result.

    Command:
        $AUDIVERIS_HOME/bin/Audiveris -batch -export -output {output_dir} {pdf_path}

    Audiveris writes a .omr book file and exports MusicXML to *output_dir*.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    audiveris_bin = os.path.join(AUDIVERIS_HOME, "bin", "Audiveris")
    if not os.path.isfile(audiveris_bin):
        # TODO: Add fallback to PATH-based audiveris command
        raise FileNotFoundError(
            f"Audiveris binary not found at {audiveris_bin}. "
            "Set AUDIVERIS_HOME environment variable."
        )

    cmd = [
        audiveris_bin,
        "-batch",
        "-export",
        "-output", output_dir,
        pdf_path,
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout_bytes, _ = await proc.communicate()
    stdout = stdout_bytes.decode("utf-8", errors="replace")

    if proc.returncode != 0:
        return AudiverisResult(
            musicxml_path="",
            book_path="",
            confidence_score=0.0,
            measures_count=0,
            error_message=f"Audiveris exited with code {proc.returncode}: {stdout[-500:]}",
        )

    confidence = parse_audiveris_confidence(stdout)

    # Locate the exported MusicXML file (Audiveris names it after the PDF stem)
    # Audiveris v5.4 exports .mxl (compressed MusicXML); older versions export .xml
    pdf_stem = Path(pdf_path).stem
    book_path = os.path.join(output_dir, f"{pdf_stem}.omr")

    musicxml_path = ""
    for ext in (".xml", ".mxl", ".musicxml"):
        candidate = os.path.join(output_dir, f"{pdf_stem}{ext}")
        if os.path.isfile(candidate):
            musicxml_path = candidate
            break

    measures_count = 0
    if musicxml_path and validate_musicxml(musicxml_path):
        measures_count = _count_measures(musicxml_path)

    return AudiverisResult(
        musicxml_path=musicxml_path,
        book_path=book_path if os.path.isfile(book_path) else "",
        confidence_score=confidence,
        measures_count=measures_count,
        error_message=None,
    )


def parse_audiveris_confidence(stdout: str) -> float:
    """Parse Audiveris stdout for an overall confidence score (0.0-1.0).

    Audiveris logs lines like:
        "Grade: 0.87" or "recognition: 87%"

    TODO: Update this regex when targeting a specific Audiveris version,
    as the log format varies between releases.
    """
    # Pattern 1: "Grade: 0.87"
    match = re.search(r"Grade[:\s]+([0-9]+\.?[0-9]*)", stdout, re.IGNORECASE)
    if match:
        raw = float(match.group(1))
        return min(max(raw, 0.0), 1.0)

    # Pattern 2: percentage like "87%"
    match = re.search(r"recognition[:\s]+([0-9]+)%", stdout, re.IGNORECASE)
    if match:
        return float(match.group(1)) / 100.0

    # Default: no confidence info found
    return 0.5


def validate_musicxml(xml_path: str) -> bool:
    """Check that *xml_path* is parseable XML with a MusicXML root element."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        # MusicXML root tags: <score-partwise> or <score-timewise>
        tag = root.tag.lower()
        return "score" in tag
    except ET.ParseError:
        return False
    except FileNotFoundError:
        return False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _count_measures(xml_path: str) -> int:
    """Count the number of <measure> elements in a MusicXML file."""
    try:
        tree = ET.parse(xml_path)
        # TODO: Handle timewise vs partwise MusicXML differently
        return len(tree.findall(".//{http://www.musicxml.org/musicxml}measure") or
                   tree.findall(".//measure"))
    except Exception:
        return 0
