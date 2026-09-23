"""The staged LilyPond exporter — ROADMAP 3.1.

⚠️ These reuse the SAME fixture helpers `test_staged_export.py` uses, on
purpose: `tools.omr.staged.lilypond` reads no `Q.*` quantity of its own, it
calls `staged.export.build()`/`_pair_arcs`/`_place_wedges`/`_events`/
`_voice_split` — the SAME functions the MusicXML tests exercise — so a
fixture built for one exporter is, by construction, a fixture for the other.
Importing rather than duplicating is what stops the two suites drifting the
way `_document_bar_offsets`'s own docstring warns a restated rule always
does.

Run RED first (`git mv tools/omr/staged/lilypond.py /tmp && pytest
tools/omr/tests/test_staged_lilypond.py`, restore after): every test here
raised `ModuleNotFoundError` against the unbuilt module.
"""

import re
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from tools.omr.staged import export as SX
from tools.omr.staged import lilypond as LY
from tools.omr.staged.record import Q
from tools.omr.tests.test_staged_export import (
    QUARTER,
    _add_fermata,
    _add_rest,
    _condensed_cello_bass_page,
    _log_json,
    _obs,
    _one_staff_page,
    _tacet_page,
    _two_voice_page,
    _vrd,
)

_HAS_LILYPOND = shutil.which("lilypond") is not None


def _compile(text: str) -> subprocess.CompletedProcess:
    """Compile a `.ly` string in a scratch directory; the caller reads
    `.returncode` and `.stderr`. Never called unless `_HAS_LILYPOND`."""
    with tempfile.TemporaryDirectory() as d:
        ly = Path(d) / "score.ly"
        ly.write_text(text)
        return subprocess.run(
            ["lilypond", "-s", "--output", d, str(ly)],
            capture_output=True, text=True, timeout=60)


def _add_ornament(page, gi, *, owner_gi, kind="tremolo", strokes=2,
                  outcome="decided", reason="contains_the_mark"):
    """An ornament mark plus its owner verdict, in the shape gather emits —
    the same pattern `test_staged_export._add_fermata` uses for fermatas."""
    sub = f"glyph/0/0/0/0/{gi}"
    page["record"]["observations"].append(
        _obs(400 + gi, sub, Q.ORNAMENT_MARK, kind, x0=0, x1=10, y0=0, y1=10))
    v = _vrd(450 + gi, sub, Q.ORNAMENT_OWNER, f"glyph/0/0/0/0/{owner_gi}",
             outcome=outcome, reason=reason)
    v["detail"] = {"ornament": kind, "strokes": strokes}
    page["record"]["verdicts"].append(v)
    return page


class TestItWritesAFile(unittest.TestCase):
    def test_a_one_part_page_has_the_paid_for_shape(self):
        text, report = LY.to_lilypond(_one_staff_page(notes=[("C4", QUARTER)]))
        self.assertTrue(text.startswith('\\version "'))
        self.assertIn("\\new Staff", text)
        self.assertIn("c'4", text)
        self.assertEqual(text.count("\\new Staff"), 1)
        self.assertEqual(report["written"]["parts"], 1)

    def test_out_writes_the_same_text_to_disk(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "score.ly"
            text, _report = LY.to_lilypond(
                _one_staff_page(notes=[("C4", QUARTER)]), out=str(path))
            self.assertEqual(path.read_text(), text)

    @unittest.skipUnless(_HAS_LILYPOND, "lilypond not on PATH")
    def test_a_one_part_page_COMPILES(self):
        text, _report = LY.to_lilypond(_one_staff_page(notes=[("C4", QUARTER)]))
        proc = _compile(text)
        self.assertEqual(proc.returncode, 0, proc.stderr)


class TestTheNoteSequenceAgreesWithMusicXML(unittest.TestCase):
    """⚠️ THE GATE ITEM'S OWN REQUIREMENT: the two exporters read the SAME
    `build()` positions, so a pitch that reaches one must reach the other,
    in the same voice, in the same order."""

    @staticmethod
    def _lily_voice_pitches(text: str, voice_index: int) -> list:
        """The note letters+octaves LilyPond will sound, read out of the
        `<< {v1} \\\\ {v2} >>` block by TEXT rather than by re-parsing
        LilyPond -- this test asks what reached the FILE, the same
        `FAMILIES` rule `staged.export`'s own tests apply to MusicXML."""
        m = re.search(r"<< \{ (.*?) \} \\\\ \{ (.*?) \} >>", text)
        assert m, text
        voice_text = m.group(voice_index + 1)
        return re.findall(r"\b([a-g](?:is|es)*[',]*)\d", voice_text)

    @staticmethod
    def _mxl_voice_pitches(xml: str, voice: str) -> list:
        root = ET.fromstring(xml)
        out = []
        for note in root.findall(".//note"):
            v = note.find("voice")
            if v is not None and v.text == voice and note.find("rest") is None:
                pitch = note.find("pitch")
                out.append((pitch.find("step").text, pitch.find("octave").text))
        return out

    def test_two_voices_carry_the_same_pitches_in_the_same_order(self):
        page = _two_voice_page(rest_gi=7)
        xml, _mxl_report = SX.to_musicxml(page)
        text, _ly_report = LY.to_lilypond(page)

        mxl_v1 = self._mxl_voice_pitches(xml, "1")
        mxl_v2 = self._mxl_voice_pitches(xml, "2")
        ly_v1 = self._lily_voice_pitches(text, 0)
        ly_v2 = self._lily_voice_pitches(text, 1)

        # C4 -> MusicXML ("C", "4") <-> LilyPond "c'" (one apostrophe = C4).
        self.assertEqual(mxl_v1, [("C", "4")])
        self.assertEqual(ly_v1, ["c'"])
        self.assertEqual(mxl_v2, [("E", "4")])
        self.assertEqual(ly_v2, ["e'"])

    def test_a_single_voice_bar_agrees_too(self):
        page = _one_staff_page(notes=[("C4", QUARTER), ("D4", QUARTER),
                                      ("E4", QUARTER)])
        xml, _ = SX.to_musicxml(page)
        text, _ = LY.to_lilypond(page)
        mxl_pitches = self._mxl_voice_pitches(xml, "1")
        self.assertEqual(mxl_pitches, [("C", "4"), ("D", "4"), ("E", "4")])
        self.assertEqual(re.findall(r"\b([a-g](?:is|es)*[',]*)\d", text),
                         ["c'", "d'", "e'"])


class TestACondensedStaffGetsTheTransposition(unittest.TestCase):
    """ROADMAP 2.1b, same rule as MusicXML's `<transpose>`: the Cello copy
    carries no transposition, the Contrabass copy does, and both carry the
    identical WRITTEN pitch."""

    def test_two_staves_one_transposed(self):
        text, report = LY.to_lilypond(_condensed_cello_bass_page())
        self.assertEqual(text.count("\\new Staff"), 2)
        self.assertEqual(text.count("\\transposition c,"), 1)
        blocks = text.split("\\new Staff")[1:]
        self.assertNotIn("\\transposition", blocks[0])
        self.assertIn("\\transposition c,", blocks[1])
        self.assertEqual(report["written"]["parts"], 2)

    def test_the_written_pitch_is_identical_on_both_staves(self):
        text, _ = LY.to_lilypond(_condensed_cello_bass_page())
        pitches = re.findall(r"\b([a-g](?:is|es)*[',]*)\d", text)
        self.assertEqual(len(pitches), 2)
        self.assertEqual(pitches[0], pitches[1])

    def test_agrees_with_the_musicxml_transpose_block(self):
        page = _condensed_cello_bass_page()
        xml, _ = SX.to_musicxml(page)
        text, _ = LY.to_lilypond(page)
        root = ET.fromstring(xml)
        p1, p2 = root.findall("part")
        self.assertIsNone(p1.find(".//transpose"))
        self.assertIsNotNone(p2.find(".//transpose"))
        self.assertEqual(text.count("\\transposition"), 1)


class TestAnUnreadBarIsAMeasureRestNeverInventedNotes(unittest.TestCase):
    def test_two_empty_bars_become_two_rests(self):
        text, report = LY.to_lilypond(_one_staff_page(notes=[], n_measures=2))
        self.assertEqual(report["written"]["empty_bars_padded"], 2)
        self.assertEqual(text.count("r1"), 2)
        # ⚠️ NEVER INVENTED NOTES -- the one thing this test exists to
        # refuse. A bar with no decided events must not contain a pitch.
        self.assertEqual(re.findall(r"[a-g](?:is|es)*[',]*\d", text), [])

    def test_the_bar_count_matches_musicxml_for_a_tacet_span(self):
        """The two exporters share `_document_bar_offsets`/`_tacet_walk`, so
        a part missing a system's meter must come out the SAME length in
        both files."""
        page = _tacet_page()
        _xml, mxl_report = SX.to_musicxml(page)
        _text, ly_report = LY.to_lilypond(page)
        self.assertEqual(
            mxl_report["written"]["empty_bars_padded"],
            ly_report["written"]["empty_bars_padded"])
        self.assertEqual(
            mxl_report["tacet_padding"]["bars_not_padded_without_meter"],
            ly_report["written"]["tacet_bars_not_padded_without_meter"])

    @unittest.skipUnless(_HAS_LILYPOND, "lilypond not on PATH")
    def test_it_still_compiles(self):
        text, _report = LY.to_lilypond(_one_staff_page(notes=[], n_measures=2))
        proc = _compile(text)
        self.assertEqual(proc.returncode, 0, proc.stderr)


class TestAFermataOverAMeasureRestReachesTheFile(unittest.TestCase):
    """⚠️ FOUND MEASURING THE ENGRAVED ACCEPTANCE RECORD, NOT BY REVIEW:
    `written['fermatas']` read 77 on the MusicXML side and 52 here, a
    25-fermata gap that is exactly the bars whose only event is a
    whole-rest `measure_rest`. `_lily_measure_rest` sizes a bare rest off
    the METER alone and has no way to carry a mark the original event held —
    `_render_bar` now appends `\\fermata` itself for that one case, the
    LilyPond equivalent of `_rest_xml` taking `fermata=` directly."""

    def _page(self):
        page = _one_staff_page(notes=[], n_measures=1, meter=None)
        _add_rest(page, gi=5, cls="restWhole",
                 dur={"measure_rest": True, "beats": 2.0, "written": 2.0})
        _add_fermata(page, gi=9, x=100, owner_gi=5)
        return page

    def test_the_fermata_is_written_on_the_rest(self):
        text, report = LY.to_lilypond(self._page())
        flat = text.replace(" ", "").replace("\n", "")
        self.assertRegex(flat, r"r\d\.*\\fermata")
        self.assertEqual(report["written"]["measure_rests_read"], 1)
        self.assertEqual(report["written"]["fermatas"], 1)

    def test_agrees_with_the_musicxml_fermata_count(self):
        page = self._page()
        _xml, mxl_report = SX.to_musicxml(page)
        _text, ly_report = LY.to_lilypond(page)
        self.assertEqual(mxl_report["written"]["fermatas"],
                         ly_report["written"]["fermatas"])
        self.assertEqual(mxl_report["written"]["fermatas"], 1)

    @unittest.skipUnless(_HAS_LILYPOND, "lilypond not on PATH")
    def test_it_still_compiles(self):
        text, _report = LY.to_lilypond(self._page())
        proc = _compile(text)
        self.assertEqual(proc.returncode, 0, proc.stderr)


class TestADocumentedDropIsCountedInTheLilypondBlock(unittest.TestCase):
    """⚠️ TREMOLO IS A DOCUMENTED DROP IN THE LEGACY EXPORTER TOO
    (`_LILY_ORNAMENT` excludes it — see that table's own comment: it "carries
    its stroke count as well as a name", the one mark `_lily_event` has no
    syntax for). This is the FIRST time it is counted rather than merely
    true."""

    def test_a_tremolo_reaches_the_note_and_not_the_text(self):
        page = _one_staff_page(notes=[("C4", QUARTER)])
        _add_ornament(page, gi=5, owner_gi=0)
        text, report = LY.to_lilypond(page)
        self.assertNotIn("tremolo", text.lower())
        self.assertEqual(report["lilypond"]["ornaments_not_renderable"], 1)
        # ⚠️ `ornaments_not_written` (from `build()`) is 0 -- the OWNER was
        # found and the mark WAS attached to the notehead; it is LilyPond's
        # own renderer, not the staged join, that has nowhere to put it.
        self.assertEqual(sum(report["ornaments_not_written"].values()), 0)

    def test_a_renderable_ornament_is_written(self):
        page = _one_staff_page(notes=[("C4", QUARTER)])
        _add_ornament(page, gi=5, owner_gi=0, kind="trill", strokes=None)
        text, report = LY.to_lilypond(page)
        self.assertIn("\\trill", text)
        self.assertEqual(report["written"]["ornaments"], 1)
        self.assertEqual(report["lilypond"]["ornaments_not_renderable"], 0)


class TestPartsSpanTheWholeDocumentNotOneSystem(unittest.TestCase):
    """⚠️ THE STRUCTURAL DEPARTURE FROM `tools.omr.export.to_lilypond`,
    which emits one `\\new Staff` per SYSTEM. Here one `\\new Staff` covers
    every system a part appears on, so a two-system document with one part
    produces exactly ONE staff block holding both systems' bars."""

    def test_one_part_two_systems_one_staff_block(self):
        page = _log_json(
            [_obs(0, "glyph/0/0/0/0/0", Q.GLYPH_BOX,
                 ["noteheadBlackOnLine", 0, 50, 40, 40], category="notehead"),
             _obs(1, "glyph/0/0/0/0/0", Q.NOTEHEAD_CLASS,
                 "noteheadBlackOnLine")],
            [_vrd(2, "glyph/0/0/0/0/0", Q.PITCH, "C4"),
             _vrd(3, "glyph/0/0/0/0/0", Q.DURATION, QUARTER),
             _vrd(10, "staff/0/0/0", Q.MEASURE_PARTITION, 1),
             _vrd(11, "staff/0/0/0", Q.CLEF, "treble"),
             _vrd(12, "staff/1/0/0", Q.MEASURE_PARTITION, 1),
             _vrd(13, "staff/1/0/0", Q.CLEF, "treble"),
             _vrd(14, "system/0/0", Q.SYSTEM_STAFF_COUNT, 1),
             _vrd(15, "system/1/0", Q.SYSTEM_STAFF_COUNT, 1),
             _vrd(16, "document", Q.PART_PARTITION,
                 {"join": "ordinal", "staves_per_system": 1},
                 reason="ordinal")])
        text, report = LY.to_lilypond(page)
        self.assertEqual(text.count("\\new Staff"), 1)
        self.assertEqual(report["written"]["parts"], 1)
        # both systems' bars land in the one staff block: one real note
        # (system 0) and one padded rest (system 1, no events decided there)
        self.assertEqual(report["written"].get("empty_bars_padded", 0), 1)


if __name__ == "__main__":
    unittest.main()
