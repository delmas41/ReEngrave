"""
File import module.
Handles saving uploaded files, type detection, and basic validation.
"""

from __future__ import annotations

import io
import os
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

import aiofiles
from fastapi import UploadFile


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ImportResult:
    file_id: str
    original_filename: str
    file_type: str  # "pdf" or "musicxml"
    local_path: str
    size_bytes: int


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def save_uploaded_file(file: UploadFile, upload_dir: str) -> ImportResult:
    """Save a FastAPI UploadFile to disk.

    Detects file type by extension and magic bytes. Compressed MusicXML
    (.mxl) files are transparently decompressed before saving.

    Returns an ImportResult with metadata about the saved file.
    """
    Path(upload_dir).mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())
    original_filename = file.filename or f"upload_{file_id}"

    content = await file.read()

    # Decompress .mxl before type detection
    if _is_mxl(content, original_filename):
        content = _extract_mxl(content)

    file_type = detect_file_type(content, original_filename)

    ext_map = {"pdf": ".pdf", "musicxml": ".xml"}
    ext = ext_map.get(file_type, ".bin")
    safe_name = f"{file_id}{ext}"
    local_path = os.path.join(upload_dir, safe_name)

    async with aiofiles.open(local_path, "wb") as f:
        await f.write(content)

    return ImportResult(
        file_id=file_id,
        original_filename=original_filename,
        file_type=file_type,
        local_path=local_path,
        size_bytes=len(content),
    )


def detect_file_type(file_bytes: bytes, filename: str) -> str:
    """Detect whether file is PDF or MusicXML.

    Checks magic bytes first, then falls back to filename extension.
    Raises ValueError for unrecognized types.
    """
    # PDF magic bytes: %PDF
    if file_bytes[:4] == b"%PDF":
        return "pdf"

    # MusicXML: XML starting with <?xml or <score
    text_start = file_bytes[:200].decode("utf-8", errors="replace").lower()
    if "<?xml" in text_start or "<score-partwise" in text_start or "<score-timewise" in text_start:
        return "musicxml"

    # Fallback to extension
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return "pdf"
    if lower.endswith((".xml", ".musicxml", ".mxl")):
        return "musicxml"

    raise ValueError(
        f"Cannot determine file type for '{filename}'. "
        "Expected PDF or MusicXML."
    )


async def validate_pdf(path: str) -> bool:
    """Basic PDF validation: check %PDF header in first 4 bytes."""
    try:
        async with aiofiles.open(path, "rb") as f:
            header = await f.read(4)
        return header == b"%PDF"
    except OSError:
        return False


async def validate_musicxml(path: str) -> bool:
    """Check that file is valid XML with a MusicXML root element."""
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _check_musicxml_sync, path)
        return result
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_mxl(content: bytes, filename: str) -> bool:
    """Return True if the content is a compressed MusicXML (.mxl) ZIP archive."""
    # ZIP magic bytes: PK\x03\x04
    if content[:4] == b"PK\x03\x04":
        return True
    if filename.lower().endswith(".mxl"):
        return True
    return False


def _extract_mxl(content: bytes) -> bytes:
    """Extract MusicXML from a compressed .mxl file (ZIP container).

    The MXL format is a ZIP archive containing:
    - META-INF/container.xml  — points to the root MusicXML file
    - One or more .xml files  — the actual MusicXML content

    Returns the raw bytes of the MusicXML document.
    Raises ValueError if no MusicXML content can be found.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            # Preferred: use META-INF/container.xml to find the root file
            try:
                container_bytes = zf.read("META-INF/container.xml")
                container_root = ET.fromstring(container_bytes)
                for element in container_root.iter():
                    local_tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag
                    if local_tag.lower() == "rootfile":
                        full_path = element.get("full-path", "")
                        if full_path:
                            return zf.read(full_path)
            except (KeyError, ET.ParseError):
                pass

            # Fallback: find any .xml file that isn't in META-INF
            for name in sorted(zf.namelist()):
                if name.lower().endswith(".xml") and not name.startswith("META-INF"):
                    return zf.read(name)

    except zipfile.BadZipFile as exc:
        raise ValueError(f"File is not a valid ZIP/MXL archive: {exc}") from exc

    raise ValueError("Could not find MusicXML content in .mxl archive")


def _check_musicxml_sync(path: str) -> bool:
    """Synchronous MusicXML validation called in a thread pool."""
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        tag = root.tag.lower()
        if "}" in tag:
            tag = tag.split("}")[1]
        return tag in ("score-partwise", "score-timewise", "score")
    except ET.ParseError:
        return False
    except FileNotFoundError:
        return False
