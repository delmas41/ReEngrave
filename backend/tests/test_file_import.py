"""Tests for file_import module."""

import io
import zipfile
import pytest

from modules.file_import import detect_file_type, _is_mxl, _extract_mxl


MINIMAL_MUSICXML = b"""<?xml version='1.0' encoding='utf-8'?>
<score-partwise version="4.0">
  <part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list>
  <part id="P1"><measure number="1"/></part>
</score-partwise>"""

PDF_MAGIC = b"%PDF-1.4 fake pdf content"


def _make_mxl(xml_content: bytes, use_container: bool = True) -> bytes:
    """Build a minimal .mxl ZIP archive."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        if use_container:
            container = b"""<?xml version="1.0"?>
<container>
  <rootfiles>
    <rootfile full-path="score.xml" media-type="application/vnd.recordare.musicxml+xml"/>
  </rootfiles>
</container>"""
            zf.writestr("META-INF/container.xml", container)
        zf.writestr("score.xml", xml_content)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# detect_file_type
# ---------------------------------------------------------------------------

class TestDetectFileType:
    def test_detects_pdf_by_magic(self):
        assert detect_file_type(PDF_MAGIC, "file.bin") == "pdf"

    def test_detects_musicxml_by_xml_declaration(self):
        assert detect_file_type(MINIMAL_MUSICXML, "file.bin") == "musicxml"

    def test_detects_musicxml_by_score_partwise_tag(self):
        content = b"<score-partwise>...</score-partwise>"
        assert detect_file_type(content, "file.bin") == "musicxml"

    def test_fallback_pdf_extension(self):
        assert detect_file_type(b"random bytes", "score.pdf") == "pdf"

    def test_fallback_xml_extension(self):
        assert detect_file_type(b"random bytes", "score.xml") == "musicxml"

    def test_fallback_mxl_extension(self):
        assert detect_file_type(b"random bytes", "score.mxl") == "musicxml"

    def test_fallback_musicxml_extension(self):
        assert detect_file_type(b"random bytes", "score.musicxml") == "musicxml"

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Cannot determine file type"):
            detect_file_type(b"random bytes", "file.docx")


# ---------------------------------------------------------------------------
# _is_mxl
# ---------------------------------------------------------------------------

class TestIsMxl:
    def test_detects_zip_magic_bytes(self):
        assert _is_mxl(b"PK\x03\x04rest", "file.bin") is True

    def test_detects_mxl_extension(self):
        assert _is_mxl(b"other", "score.mxl") is True

    def test_returns_false_for_pdf(self):
        assert _is_mxl(PDF_MAGIC, "score.pdf") is False

    def test_returns_false_for_plain_xml(self):
        assert _is_mxl(MINIMAL_MUSICXML, "score.xml") is False


# ---------------------------------------------------------------------------
# _extract_mxl
# ---------------------------------------------------------------------------

class TestExtractMxl:
    def test_extracts_via_container_xml(self):
        mxl = _make_mxl(MINIMAL_MUSICXML, use_container=True)
        result = _extract_mxl(mxl)
        assert b"score-partwise" in result

    def test_extracts_fallback_without_container(self):
        mxl = _make_mxl(MINIMAL_MUSICXML, use_container=False)
        result = _extract_mxl(mxl)
        assert b"score-partwise" in result

    def test_raises_on_invalid_zip(self):
        with pytest.raises(ValueError, match="not a valid ZIP"):
            _extract_mxl(b"this is not a zip file")

    def test_raises_when_no_xml_found(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("README.txt", "no xml here")
        with pytest.raises(ValueError, match="Could not find MusicXML"):
            _extract_mxl(buf.getvalue())
