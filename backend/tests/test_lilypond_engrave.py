"""Tests for lilypond_engrave module."""

import os
import textwrap
import pytest
from modules.lilypond_engrave import (
    _extract_musicxml_metadata,
    _inject_lilypond_header,
    _parse_parts,
    _extract_single_part,
    _detect_namespace,
)


PARTWISE_MUSICXML = textwrap.dedent("""\
    <?xml version='1.0' encoding='utf-8'?>
    <score-partwise version="4.0">
      <work>
        <work-title>Sonata in C</work-title>
        <work-number>Op. 1</work-number>
      </work>
      <movement-title>Allegro</movement-title>
      <identification>
        <creator type="composer">Ludwig van Beethoven</creator>
        <creator type="arranger">John Smith</creator>
      </identification>
      <part-list>
        <score-part id="P1"><part-name>Violin</part-name></score-part>
        <score-part id="P2"><part-name>Piano</part-name></score-part>
      </part-list>
      <part id="P1">
        <measure number="1"><note/></measure>
      </part>
      <part id="P2">
        <measure number="1"><note/></measure>
      </part>
    </score-partwise>
""")


@pytest.fixture
def musicxml_file(tmp_path):
    p = tmp_path / "score.xml"
    p.write_text(PARTWISE_MUSICXML, encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# _extract_musicxml_metadata
# ---------------------------------------------------------------------------

class TestExtractMusicxmlMetadata:
    def test_extracts_title(self, musicxml_file):
        meta = _extract_musicxml_metadata(musicxml_file)
        assert meta["title"] == "Sonata in C"

    def test_extracts_composer(self, musicxml_file):
        meta = _extract_musicxml_metadata(musicxml_file)
        assert meta["composer"] == "Ludwig van Beethoven"

    def test_extracts_subtitle_from_movement_title(self, musicxml_file):
        meta = _extract_musicxml_metadata(musicxml_file)
        assert meta["subtitle"] == "Allegro"

    def test_extracts_opus(self, musicxml_file):
        meta = _extract_musicxml_metadata(musicxml_file)
        assert meta["opus"] == "Op. 1"

    def test_extracts_arranger(self, musicxml_file):
        meta = _extract_musicxml_metadata(musicxml_file)
        assert meta["arranger"] == "John Smith"

    def test_missing_file_returns_empty(self):
        meta = _extract_musicxml_metadata("/nonexistent/path.xml")
        assert meta == {}


# ---------------------------------------------------------------------------
# _inject_lilypond_header
# ---------------------------------------------------------------------------

class TestInjectLilypondHeader:
    def _write_ly(self, tmp_path, content):
        p = tmp_path / "score.ly"
        p.write_text(content, encoding="utf-8")
        return str(p)

    def test_injects_after_version(self, tmp_path):
        ly = self._write_ly(tmp_path, '\\version "2.24.0"\n\\relative c { c4 d e f }\n')
        _inject_lilypond_header(ly, {"title": "My Sonata", "composer": "Bach"})
        content = open(ly).read()
        assert '\\header' in content
        assert 'My Sonata' in content
        assert 'Bach' in content
        # header should come after version
        assert content.index('\\version') < content.index('\\header')

    def test_injects_at_top_without_version(self, tmp_path):
        ly = self._write_ly(tmp_path, '\\relative c { c4 }\n')
        _inject_lilypond_header(ly, {"title": "Piece", "composer": "Vivaldi"})
        content = open(ly).read()
        assert content.startswith('\\header')

    def test_does_not_overwrite_existing_header(self, tmp_path):
        existing = '\\version "2.24.0"\n\\header { title = "Existing" }\n'
        ly = self._write_ly(tmp_path, existing)
        _inject_lilypond_header(ly, {"title": "New Title"})
        content = open(ly).read()
        assert content.count('\\header') == 1
        assert 'Existing' in content

    def test_escapes_quotes_in_metadata(self, tmp_path):
        ly = self._write_ly(tmp_path, '\\relative c { c4 }\n')
        _inject_lilypond_header(ly, {"title": 'Title "With" Quotes'})
        content = open(ly).read()
        assert '\\"With\\"' in content

    def test_no_op_for_empty_metadata(self, tmp_path):
        original = '\\relative c { c4 }\n'
        ly = self._write_ly(tmp_path, original)
        _inject_lilypond_header(ly, {})
        assert open(ly).read() == original


# ---------------------------------------------------------------------------
# _parse_parts
# ---------------------------------------------------------------------------

class TestParseParts:
    def test_returns_part_map(self, musicxml_file):
        parts = _parse_parts(musicxml_file)
        assert parts == {"P1": "Violin", "P2": "Piano"}

    def test_returns_empty_for_invalid_file(self):
        parts = _parse_parts("/nonexistent/file.xml")
        assert parts == {}


# ---------------------------------------------------------------------------
# _extract_single_part
# ---------------------------------------------------------------------------

class TestExtractSinglePart:
    def test_extracts_only_requested_part(self, musicxml_file):
        xml_str = _extract_single_part(musicxml_file, "P1", "Violin")
        from xml.etree import ElementTree as ET
        root = ET.fromstring(xml_str)
        parts = root.findall("part")
        assert len(parts) == 1
        assert parts[0].get("id") == "P1"

    def test_part_list_filtered(self, musicxml_file):
        xml_str = _extract_single_part(musicxml_file, "P2", "Piano")
        from xml.etree import ElementTree as ET
        root = ET.fromstring(xml_str)
        part_list = root.find("part-list")
        score_parts = part_list.findall("score-part")
        assert len(score_parts) == 1
        assert score_parts[0].get("id") == "P2"

    def test_output_is_valid_xml(self, musicxml_file):
        from xml.etree import ElementTree as ET
        xml_str = _extract_single_part(musicxml_file, "P1", "Violin")
        # Should not raise
        ET.fromstring(xml_str)
