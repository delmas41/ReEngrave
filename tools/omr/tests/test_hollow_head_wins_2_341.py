"""ROADMAP 2.341 -- a hollow head is a half note; a flag hanging from the stem's tip makes an eighth (STAGED ADJUDICATE, `rhythm`).

A (`OMR_HOLLOW_HEAD_WINS`, default OFF). "A head whose middle is open paper is a half note (with a stem) -- never a quarter. NEVER call
hollow a head whose opening is a staff-line gap, a ledger-line gap, or the gap between two fused heads; where the two reads disagree and
neither is sure the note is held (blue), never written plain." Cause: on Litolff the detector box sits on the head's upper rim, so 2.148's
read of the BOX's middle rows misses the half's diagonal slit (box share 0.00) and is written plain black; the head's own trimmed ink
(`Q.HEAD_INK`) finds the slit -- and also finds the paper between a black head and its beam. So the two reads disagreeing NARROW
quarter-or-half (the bar settles it, blue), only on a stem with nothing read on it.

Every case's readings are the 20261122-night record's own (`fixtures/hollow_head_wins_2_341.json`): halves and black heads by the lane
agent's look at the 600-dpi crops (not Sean's answers), and Sean's judged marks (Litolff p11 `glyph/11/0/1/9/2` a half, p2
`glyph/2/1/10/0/14` a beamed eighth, p6 `glyph/6/1/11/11/1` m169 a half). Each positive has a control that fails with the flag off.
"""
from __future__ import annotations

import json
import os
import pathlib
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import READERS, Log, Outcome, Q
from tools.omr.tests.stroke_map_fixture import file_note_ink
from tools.omr.tests.test_staged_head_fill_first_2_148 import _head

FIX = json.loads((pathlib.Path(__file__).parent / "fixtures" / "hollow_head_wins_2_341.json").read_text())["cases"]
FLAG = rhythm.HOLLOW_HEAD_WINS_ENV


def _group(name):
    return {k: c for k, c in FIX.items() if c["group"] == name}


def _reads(c):
    """The record's two reads of one head, as `adjudicate_duration` sees them (`_head_reads_hollow_first` / `_head_ink`)."""
    br, oi = c["box_read"], c["own_ink"]
    hf = {"fill": br["fill"], "rows_share": br["rows_share"], "row": "obs:1"}
    if br.get("not_head_sized"):
        hf["not_head_sized"] = True
    hi = {"value": oi["value"], "why": oi["why"], "row": "obs:2", "slit": oi["slit"], "extent_sp": oi["extent_sp"],
          "not_one_head": oi["not_one_head"], "margin": oi["margin"]}
    return hf, hi


def _replay(c, on, beam=False):
    """A head-sized black head on its own stem carrying the record's two reads, through ADJUDICATE."""
    log = Log()
    g = _head(log, share=c["box_read"]["rows_share"])
    file_note_ink(log, (100, 90, 20, 16), sp=16, side="up", beams=1 if beam else 0)     # the stem the one beam count reads (2.319)
    oi = c["own_ink"]
    if oi["value"] is not None:
        log.observe(g, Q.HEAD_INK, oi["value"], reader=READERS.CV_HEAD_INK, frame="cell:0", margin=oi["margin"], slit=oi["slit"],
                    extent_sp=oi["extent_sp"])
    else:
        log.abstain(g, Q.HEAD_INK, reader=READERS.CV_HEAD_INK, frame="cell:0", reason=oi["why"], not_one_head=oi["not_one_head"],
                    slit=oi["slit"], extent_sp=oi["extent_sp"])
    with mock.patch.dict(os.environ, {FLAG: "1" if on else "0"}):
        adjudicate.run(log)
    return log.verdict(Q.DURATION, g)


def _values(v):
    if v.outcome is Outcome.DECIDED:
        return {v.value["written"]}
    return {c.value["written"] for c in v.candidates}


def _guess(v):
    return (v.detail or {}).get(rhythm.HEAD_INK_GUESS_KEY)


class TheTwoReadsDisagree(unittest.TestCase):

    def test_the_controls_are_enough(self):
        self.assertGreaterEqual(len(_group("half_by_look")), 16)
        self.assertGreaterEqual(len(_group("black_by_look")) + len(_group("beamed_eighth_by_look")), 8)

    def test_every_half_looked_at_is_a_disagreement(self):
        for k, c in _group("half_by_look").items():
            hf, hi = _reads(c)
            self.assertIn(hf["fill"], ("black", None), k)
            self.assertIsNotNone(rhythm._head_reads_disagree(_Ev(), hi, hf, False), k)

    def test_RED_flag_off_each_half_is_written_a_plain_quarter(self):
        for k, c in _group("half_by_look").items():
            v = _replay(c, on=False)
            self.assertEqual((v.outcome, _values(v)), (Outcome.DECIDED, {1.0}), k)

    def test_on_each_half_is_held_blue_with_quarter_and_half_never_plain(self):
        for k, c in _group("half_by_look").items():
            v = _replay(c, on=True)
            self.assertEqual((v.outcome, v.reason), (Outcome.DECIDED, "head_reads_disagree"), k)
            g = _guess(v)
            self.assertTrue(g and g["marks_blue"], k)
            self.assertEqual(sorted(x["written"] for x in g["candidates"]), [1.0, 2.0], k)
            # the box read NOTHING -> the half; the box read BLACK -> the quarter stays (Sean 2026-10-28: a black read is never overturned)
            self.assertEqual(v.value["written"], 2.0 if c["box_read"]["fill"] is None else 1.0, k)

    def test_NEVER_a_black_head_looked_at_is_written_a_plain_half(self):
        """The own-ink read's false openings (a black head's paper against a line or a fused head): never a PLAIN half (blue at most)."""
        for k, c in _group("black_by_look").items():
            v = _replay(c, on=True)
            if v.outcome is Outcome.DECIDED and v.value["written"] == 2.0:
                self.assertTrue((_guess(v) or {}).get("marks_blue"), k)

    def test_NEVER_a_head_with_a_beam_read_on_its_stem(self):
        """An open head is never beamed (2.43): a beam on the stem says the head is black, the own-ink opening is the beam's paper."""
        for k, c in list(_group("beamed_eighth_by_look").items()) + [("2/1/10/0/14", FIX["2/1/10/0/14"])]:
            v_on, v_off = _replay(c, on=True, beam=True), _replay(c, on=False, beam=True)
            self.assertEqual((v_on.outcome, v_on.reason, v_on.value), (v_off.outcome, v_off.reason, v_off.value), k)
            self.assertNotEqual(v_on.reason, "head_reads_disagree", k)


class TheBoundary(unittest.TestCase):

    def test_seans_m169_own_ink_is_not_one_head_so_nothing_changes(self):
        """NOT FIXED HERE, named: Sean's m169 half (p6 glyph/6/1/11/11/1) -- the detector box sits a whole space ABOVE the head, so
        neither read measures the head (own ink too_small). A GATHER head-position fault, outside this lane's fence."""
        c = FIX["6/1/11/11/1"]
        v_on, v_off = _replay(c, on=True), _replay(c, on=False)
        self.assertEqual((v_on.outcome, v_on.value), (v_off.outcome, v_off.value))

    def test_a_head_the_box_read_hollow_is_untouched(self):
        """2.148 READ hollow: the half is decided there, as today."""
        c = dict(FIX["16/0/0/6/3"], box_read={"fill": "hollow", "rows_share": 0.4, "not_head_sized": None})
        v = _replay(c, on=True)
        self.assertEqual((v.outcome, _values(v)), (Outcome.DECIDED, {2.0}))

    def test_own_ink_filled_agrees_with_the_box_and_nothing_changes(self):
        c = dict(FIX["16/0/0/6/3"], own_ink={"value": "filled", "why": None, "slit": 0.0, "extent_sp": [1.4, 1.2],
                                             "not_one_head": None, "margin": 0.06})
        v_on, v_off = _replay(c, on=True), _replay(c, on=False)
        self.assertEqual((v_on.outcome, v_on.value), (v_off.outcome, v_off.value))


class _Ev:
    """The two guards' inputs, empty: no dynamic letter on the head, no slash verdict."""

    def rows(self, *_a, **_k):
        return []


if __name__ == "__main__":
    unittest.main()
