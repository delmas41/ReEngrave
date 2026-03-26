"""Tests for export_module — specifically apply_corrections_to_musicxml."""

import os
import tempfile
from dataclasses import dataclass
from typing import Optional
from xml.etree import ElementTree as ET

import pytest

from modules.export_module import apply_corrections_to_musicxml


SIMPLE_MUSICXML = """\
<?xml version='1.0' encoding='utf-8'?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1">
      <part-name>Piano</part-name>
    </score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration></note>
    </measure>
    <measure number="2">
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>4</duration></note>
    </measure>
  </part>
</score-partwise>
"""


@dataclass
class FakeDiff:
    measure_number: int
    instrument: str
    difference_type: str
    description: str
    human_decision: str
    human_edit_value: Optional[str] = None


@pytest.fixture
def source_xml(tmp_path):
    p = tmp_path / "score.xml"
    p.write_text(SIMPLE_MUSICXML, encoding="utf-8")
    return str(p)


@pytest.fixture
def output_xml(tmp_path):
    return str(tmp_path / "output.xml")


@pytest.mark.asyncio
async def test_no_diffs_copies_file(source_xml, output_xml):
    await apply_corrections_to_musicxml(source_xml, [], output_xml)
    assert os.path.isfile(output_xml)
    tree = ET.parse(output_xml)
    assert tree.getroot().tag == "score-partwise"


@pytest.mark.asyncio
async def test_accept_only_no_patch(source_xml, output_xml):
    diff = FakeDiff(1, "Piano", "note", "missing note", "accept")
    await apply_corrections_to_musicxml(source_xml, [diff], output_xml)
    # accept diffs don't patch XML — output should be identical to source
    original = ET.parse(source_xml).getroot()
    result = ET.parse(output_xml).getroot()
    assert ET.tostring(original) == ET.tostring(result)


@pytest.mark.asyncio
async def test_edit_with_xml_fragment_replaces_measure(source_xml, output_xml):
    xml_frag = "<note><pitch><step>G</step><octave>5</octave></pitch><duration>4</duration></note>"
    diff = FakeDiff(1, "Piano", "note", "wrong note", "edit", human_edit_value=xml_frag)
    await apply_corrections_to_musicxml(source_xml, [diff], output_xml)

    tree = ET.parse(output_xml)
    root = tree.getroot()
    part = root.find("part")
    measure1 = next(m for m in part.findall("measure") if m.get("number") == "1")
    notes = measure1.findall("note")
    assert len(notes) == 1
    assert notes[0].find("pitch/step").text == "G"


@pytest.mark.asyncio
async def test_edit_with_plain_text_adds_comment(source_xml, output_xml):
    diff = FakeDiff(2, "Piano", "dynamic", "missing forte", "edit", human_edit_value="add forte here")
    await apply_corrections_to_musicxml(source_xml, [diff], output_xml)
    content = open(output_xml).read()
    assert "add forte here" in content


@pytest.mark.asyncio
async def test_edit_preserves_measure_number_attribute(source_xml, output_xml):
    xml_frag = "<rest/>"
    diff = FakeDiff(2, "Piano", "note", "should be rest", "edit", human_edit_value=xml_frag)
    await apply_corrections_to_musicxml(source_xml, [diff], output_xml)
    tree = ET.parse(output_xml)
    root = tree.getroot()
    part = root.find("part")
    measure2 = next(m for m in part.findall("measure") if m.get("number") == "2")
    assert measure2.get("number") == "2"
