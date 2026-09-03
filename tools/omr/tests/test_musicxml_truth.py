"""The stdlib MusicXML reader behind the pre-fill: onsets through chords,
backup and forward; pitch spelling as the pipeline spells it; .mxl."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from tools.omr.training.musicxml_truth import load_truth

pytestmark = pytest.mark.omr_training


TWO_PARTS = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1"><part-name>Flute 1</part-name></score-part>
    <score-part id="P2"><part-name>Viola</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="0" implicit="yes">
      <attributes><divisions>2</divisions><clef><sign>G</sign><line>2</line></clef></attributes>
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type></note>
    </measure>
    <measure number="1">
      <note><pitch><step>F</step><alter>1</alter><octave>4</octave></pitch><duration>4</duration><type>half</type></note>
      <note><pitch><step>B</step><alter>-1</alter><octave>3</octave></pitch><duration>2</duration><type>quarter</type><dot/></note>
      <note><grace/><pitch><step>C</step><octave>5</octave></pitch><type>16th</type></note>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>1</duration><type>eighth</type>
        <time-modification><actual-notes>3</actual-notes><normal-notes>2</normal-notes></time-modification>
        <tie type="start"/></note>
      <note><rest/><duration>1</duration><type>eighth</type></note>
    </measure>
    <measure number="2">
      <note><rest measure="yes"/><duration>8</duration></note>
    </measure>
  </part>
  <part id="P2">
    <measure number="0" implicit="yes">
      <attributes><divisions>4</divisions><clef><sign>F</sign><line>4</line></clef></attributes>
      <note><rest/><duration>4</duration><type>quarter</type></note>
    </measure>
    <measure number="1">
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>8</duration><type>half</type><voice>1</voice></note>
      <note><chord/><pitch><step>E</step><octave>4</octave></pitch><duration>8</duration><type>half</type><voice>1</voice></note>
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>8</duration><type>half</type><voice>1</voice></note>
      <backup><duration>16</duration></backup>
      <note><pitch><step>A</step><octave>3</octave></pitch><duration>16</duration><type>whole</type><voice>2</voice></note>
    </measure>
    <measure number="2">
      <attributes><clef><sign>C</sign><line>4</line><clef-octave-change>-1</clef-octave-change></clef></attributes>
      <forward><duration>8</duration></forward>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>8</duration><type>half</type></note>
    </measure>
  </part>
</score-partwise>
"""


@pytest.fixture
def score_path(tmp_path: Path) -> Path:
    p = tmp_path / "two.musicxml"
    p.write_text(TWO_PARTS)
    return p


def test_parts_and_names(score_path: Path) -> None:
    s = load_truth(score_path)
    assert [p.name for p in s.parts] == ["Flute 1", "Viola"]
    assert [p.part_id for p in s.parts] == ["P1", "P2"]


def test_measure_numbers_and_pickup(score_path: Path) -> None:
    s = load_truth(score_path)
    fl = s.part(0)
    assert [m.number for m in fl.measures] == [0, 1, 2]
    assert fl.measures[0].implicit is True
    assert set(fl.by_number()) == {0, 1, 2}


def test_pitch_spelling_matches_the_pipeline(score_path: Path) -> None:
    m1 = load_truth(score_path).part(0).by_number()[1]
    spelled = [n.pitch for n in m1.notes if not n.rest]
    assert spelled == ["F#4", "Bb3", "C5", "C5"]
    assert [n.step_key for n in m1.notes] == ["F4", "B3", "C5", "C5", "R"]


def test_onsets_durations_dots_tuplets_ties_grace(score_path: Path) -> None:
    m1 = load_truth(score_path).part(0).by_number()[1]
    by_pitch = {(n.pitch, n.grace): n for n in m1.notes if not n.rest}
    f = by_pitch[("F#4", False)]
    assert (f.onset_ql, f.duration_ql, f.type, f.dots) == (0.0, 2.0, "half", 0)
    b = by_pitch[("Bb3", False)]
    assert (b.onset_ql, b.duration_ql, b.dots) == (2.0, 1.0, 1)
    g = by_pitch[("C5", True)]
    assert g.grace and g.duration_ql == 0.0 and g.onset_ql == 3.0
    c = by_pitch[("C5", False)]
    assert (c.tuplet_actual, c.tuplet_normal, c.tie_start) == (3, 2, True)
    assert c.onset_ql == 3.0
    rest = [n for n in m1.notes if n.rest][0]
    assert (rest.onset_ql, rest.duration_ql) == (3.5, 0.5)


def test_whole_measure_rest(score_path: Path) -> None:
    m2 = load_truth(score_path).part(0).by_number()[2]
    assert len(m2.notes) == 1 and m2.notes[0].rest and m2.notes[0].measure_rest
    assert m2.notes[0].duration_ql == 4.0
    assert m2.sounding == []


def test_chord_backup_forward_and_voices(score_path: Path) -> None:
    va = load_truth(score_path).part(1)
    m1 = va.by_number()[1]
    # onset order, then pitch within an onset: the whole-note A3 (voice 2,
    # written after a backup) sits at onset 0 with the C4/E4 chord.
    assert [(n.pitch, n.onset_ql) for n in m1.notes] == [
        ("A3", 0.0), ("C4", 0.0), ("E4", 0.0), ("G4", 2.0)]
    chord_flags = {n.pitch: n.chord for n in m1.notes}
    assert chord_flags["E4"] is True and chord_flags["C4"] is False
    assert {n.pitch: n.voice for n in m1.notes}["A3"] == "2"
    m2 = va.by_number()[2]
    assert [(n.pitch, n.onset_ql) for n in m2.notes] == [("D4", 2.0)]


def test_mxl_archive_round_trip(score_path: Path, tmp_path: Path) -> None:
    mxl = tmp_path / "two.mxl"
    with zipfile.ZipFile(mxl, "w") as zf:
        zf.writestr("META-INF/container.xml",
                    '<?xml version="1.0"?><container><rootfiles>'
                    '<rootfile full-path="score.xml"/></rootfiles></container>')
        zf.writestr("score.xml", TWO_PARTS)
    a = load_truth(score_path)
    b = load_truth(mxl)
    assert [n.pitch for n in a.part(1).by_number()[1].notes] == \
        [n.pitch for n in b.part(1).by_number()[1].notes]


def test_timewise_is_refused(tmp_path: Path) -> None:
    p = tmp_path / "tw.xml"
    p.write_text('<?xml version="1.0"?><score-timewise/>')
    with pytest.raises(ValueError):
        load_truth(p)


def test_written_clef_is_carried_onto_every_note(score_path: Path) -> None:
    s = load_truth(score_path)
    assert {n.clef for m in s.part(0).measures for n in m.notes} == {"treble"}
    va = s.part(1)
    assert {n.clef for n in va.by_number()[1].notes} == {"bass"}       # persists from m0
    assert {n.clef for n in va.by_number()[2].notes} == {"tenor_8vb"}  # changed mid-part


def test_clef_name_table() -> None:
    from tools.omr.training.musicxml_truth import clef_name
    assert clef_name("G", 2) == "treble" and clef_name("F", 4) == "bass"
    assert clef_name("C", 3) == "alto" and clef_name("C", None) == "alto"
    assert clef_name("G", 2, -1) == "treble_8vb"
    assert clef_name("percussion", None) is None and clef_name(None, None) is None
