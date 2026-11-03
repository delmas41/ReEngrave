"""ROADMAP 2.252 r4 -- a tie carries its accidental across the barline (STAGED EXPORT, flag `OMR_TIE_CARRIES_ACCIDENTAL`, default ON since 2026-11-03).

page-facts (Sean 2026-10-30, general): "A tie carries an accidental even across a bar line" -- the tied-to note keeps the start note's
pitch, printed accidental or not; `tie_spelling_differs` must not refuse it. Cause (2.252 r3/r4 census, Brahms p5 `5/1/5/4/9`): the stop
head of a cross-barline tie reads its pitch from the key and its own bar (Bb4 -> B4); EXPORT refused the tie as a spelling contradiction.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import export as SX
from tools.omr.staged.record import Q

from .test_staged_export import _vrd
from .test_staged_tie_pair import START, STOP, _tie_page

ON = {SX.TIE_CARRY_ENV: "1"}
OFF = {SX.TIE_CARRY_ENV: "0"}


def _page(stop_accidental=False):
    page = _tie_page(stop_pitch="F4")
    page["record"]["verdicts"].append(_vrd(5200, START, Q.PITCH, "F#4"))
    if stop_accidental:
        page["record"]["verdicts"].append(_vrd(5300, "glyph/0/0/0/1/77", Q.ACCIDENTAL_OWNER, STOP,
                                               reason="immediately_right_same_position"))
    return page


class TestTieCarriesTheAccidental(unittest.TestCase):
    def test_off_refuses_as_before(self):
        with mock.patch.dict(os.environ, OFF):
            xml, rep = SX.to_musicxml(_page())
        self.assertNotIn("<tie ", xml)
        self.assertEqual(rep["arcs_not_written"]["tie_spelling_differs"], 1)

    def test_on_ties_and_the_stop_keeps_the_start_pitch(self):
        with mock.patch.dict(os.environ, ON):
            xml, rep = SX.to_musicxml(_page())
        self.assertEqual(xml.count('<tie type="start"/>'), 1)
        self.assertEqual(xml.count('<tie type="stop"/>'), 1)
        self.assertEqual(xml.count("<alter>1</alter>"), 2)          # F#4 tied to F#4
        self.assertNotIn("tie_spelling_differs", rep["arcs_not_written"])

    def test_a_printed_accidental_on_the_stop_still_refuses(self):
        with mock.patch.dict(os.environ, ON):
            xml, rep = SX.to_musicxml(_page(stop_accidental=True))
        self.assertNotIn("<tie ", xml)
        self.assertEqual(rep["arcs_not_written"]["tie_spelling_differs"], 1)

    def test_a_different_step_is_never_carried(self):
        page = _tie_page(stop_pitch="G4")
        page["record"]["verdicts"].append(_vrd(5200, START, Q.PITCH, "F#4"))
        with mock.patch.dict(os.environ, ON):
            xml, rep = SX.to_musicxml(page)
        self.assertNotIn("<tie ", xml)
        self.assertEqual(rep["arcs_not_written"]["tie_pitch_contradiction"], 1)


if __name__ == "__main__":
    unittest.main()
