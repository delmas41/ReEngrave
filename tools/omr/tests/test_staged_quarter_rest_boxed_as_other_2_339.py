"""ROADMAP 2.339 -- a quarter rest hidden under another box is still a rest (STAGED ADJUDICATE, `OMR_QUARTER_REST_BOXED_AS_OTHER`
under `OMR_REST_BOXED_AS_OTHER`).

A mark with a quarter rest's shape, standing alone in the staff where a rest stands, is a quarter rest whatever the detector called it.
NEVER a real arpeggio (a wavy line immediately left of a chord), a stem with its flag (a flag box never steps aside), or ledger lines.
Written GUESSED (blue): one real sharp's ink on Brahms (p19, boxed as a flag) passes the quarter windows.

Every control is REAL: the GATHER rows filed on the 20261122-night records (`gather_unboxed_rest_ink`'s measure of the printed ink and
the detector boxes on it). Missed quarter rests boxed `arpeggiato` are not read OFF (the controls fail before the change) and are read ON;
standing restQuarter boxes keep their one rest; real accidentals boxed `arpeggiato` keep that box and no rest is read.
"""
from __future__ import annotations

import json
import os
import pathlib
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged.record import Log, Outcome, Q, READERS, Subject

FIX = json.loads((pathlib.Path(__file__).parent / "fixtures" / "quarter_rest_boxed_as_other_2_339.json").read_text())["cases"]
ORDER = (Q.ACCIDENTAL_IS_NOT_AN_ACCIDENTAL, Q.ARPEGGIATO_IS_NOT_AN_ARPEGGIATO, Q.UNBOXED_INK_IS_A_REST)


def _run(case, on: bool):
    env = {"OMR_REST_BOXED_AS_OTHER": "1", "OMR_QUARTER_REST_BOXED_AS_OTHER": "1" if on else "0"}
    with mock.patch.dict(os.environ, env):
        log = Log()
        for b in case["boxes"]:
            d = b["detail"]
            log.observe(Subject.from_key(b["subject"]), Q.GLYPH_BOX, tuple(b["value"]), reader=READERS.DETECTOR, frame="cell:0",
                        score=b.get("score"), category=d.get("category"), bbox_page_px=d.get("bbox_page_px"))
        sh = case["shape"]
        log.observe(Subject.from_key(case["subject"]), Q.UNBOXED_REST_SHAPE, sh["value"], reader=READERS.CV_UNBOXED_REST_SHAPE,
                    frame="cell:0", **sh["detail"])
        log.freeze()
        adjudicate._ensure_decisions()
        adjudicate.run(log, order=ORDER)
        rest = log.verdict(Q.UNBOXED_INK_IS_A_REST, Subject.from_key(case["subject"]))
        arps = {b["subject"]: log.verdict(Q.ARPEGGIATO_IS_NOT_AN_ARPEGGIATO, Subject.from_key(b["subject"]))
                for b in case["boxes"] if str(b["value"][0]).startswith("arpeggi")}
        return rest, arps


def _group(name):
    return [c for c in FIX.values() if c["group"] == name]


def _read(v, value="quarter"):
    return v is not None and v.outcome is Outcome.DECIDED and v.value == value


class TestMissedQuarterRests(unittest.TestCase):

    def test_enough_controls(self):
        self.assertGreaterEqual(len(_group("missed_arpeggiato")), 6)
        self.assertGreaterEqual(len(_group("read")), 3)

    def test_off_they_stay_unread_RED(self):
        for c in _group("missed_arpeggiato"):
            rest, arps = _run(c, on=False)
            self.assertFalse(_read(rest), c["subject"])
            for s, v in arps.items():
                self.assertIs(v.value, False, s)

    def test_on_the_arpeggiato_box_gives_way_and_the_rest_is_read_guessed(self):
        for c in _group("missed_arpeggiato"):
            rest, arps = _run(c, on=True)
            self.assertTrue(_read(rest), (c["subject"], rest and rest.reason))
            self.assertTrue(rest.detail["boxed_as_other"]["guessed"])
            for s, v in arps.items():
                self.assertEqual((v.value, v.reason), (True, "quarter_rest_shaped_ink"), s)


class TestNever(unittest.TestCase):

    def test_a_standing_rest_box_is_never_doubled(self):
        for c in _group("read"):
            for on in (False, True):
                rest, _ = _run(c, on=on)
                self.assertEqual(rest.reason, "already_read_as_a_glyph", (c["subject"], on))

    def test_real_accidentals_boxed_arpeggiato_keep_their_box(self):
        for c in _group("arpeggiato_on_accidental"):
            rest, arps = _run(c, on=True)
            self.assertFalse(_read(rest), c["subject"])
            for s, v in arps.items():
                self.assertIs(v.value, False, (s, v.reason))

    def test_the_boundary_a_head_immediately_right_keeps_the_box(self):
        """Quarter-rest ink standing immediately left of a head at its height is where an arpeggio stands: both readings fit, so
        the box keeps its kind and no rest is read (abstain, counted) -- never a guess between them."""
        for c in _group("boundary_head_beside"):
            rest, arps = _run(c, on=True)
            self.assertFalse(_read(rest), c["subject"])
            for s, v in arps.items():
                self.assertIs(v.value, False, s)

    def test_a_flag_box_never_steps_aside(self):
        """The one real sharp whose ink passes the quarter windows (boxed as a flag): no rest is read."""
        for c in _group("sharp_boxed_flag"):
            rest, _ = _run(c, on=True)
            self.assertFalse(_read(rest), c["subject"])


if __name__ == "__main__":
    unittest.main()
