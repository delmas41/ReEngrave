"""ROADMAP 2.248 r3 -- a far head whose ledger count ABSTAINED is written GUESSED (blue), STAGED (GATHER row, EVALUATE `restate_pitch`,
EXPORT `far_unread_guess_of`), flag `OMR_FARHEAD_UNREAD_GUESSED`, default OFF.

Page-facts (Sean 2026-10-28): a far head is placed by its ledger lines only; "no rungs either way is OUR failure: abstain and count it".
Before this, the abstention fell back PLAIN to the box centre (CLAUDE.md section 4 and rule 8: an uncertain pitch written unmarked).
The pitch value does not change; only its mark does.
"""
from __future__ import annotations

import os
import types
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401 -- registers decisions
from tools.omr.staged import consequences, export, gather, head_extent
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q
from tools.omr.types import MeasureCell

S = 40.0
LINES = (100.0, 140.0, 180.0, 220.0, 260.0)     # half step 20 px; position = (y - 100) / 20
ON = {head_extent.FAR_GUESS_ENV: "1"}
OFF = {head_extent.FAR_GUESS_ENV: "0"}


def _paper(h=400, w=400):
    img = np.full((h, w), 255, np.uint8)
    for y in LINES:
        img[int(y) - 1:int(y) + 2, 20:380] = 0
    return img


def _head(img, cx, cy, w=1.3 * S, h=1.0 * S):
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    img[((xx - cx) / (w / 2)) ** 2 + ((yy - cy) / (h / 2)) ** 2 <= 1.0] = 0


def _det(box):
    x0, y0, x1, y1 = box
    return types.SimpleNamespace(smufl_name="noteheadBlack", x_canonical=x0, y_canonical=y0, width_canonical=x1 - x0,
                                 height_canonical=y1 - y0, x_center=(x0 + x1) / 2.0, y_center=(y0 + y1) / 2.0)


def _cell(img):
    c = MeasureCell(page_index=0, system_index=0, staff_index=0, measure_index=0, image=img, image_no_staff=img,
                    bbox_page_px=(0, 0, img.shape[1], img.shape[0]), staff_line_ys_canonical=list(LINES), upscale_factor=1.0)
    c.__dict__["binary"] = img
    return c


def _geometry_row(img, box, env):
    pws = types.SimpleNamespace(page=types.SimpleNamespace(binary=img))
    log = Log()
    with mock.patch.dict(os.environ, env):
        gather.gather_notehead_positions(log, [_cell(img)], {0: (0, 0)}, {R.cell(0, 0, 0, 0).to_key(): [_det(box)]}, pws=pws)
    return log.rows(Q.NOTEHEAD_STAFF_POSITION, R.glyph(0, 0, 0, 0, 0))[-1]


class TestGatherFilesTheInkCentreAsACandidateOnly(unittest.TestCase):
    def _far(self):
        # a head centred at y=40 (position -3), with a detector box cut short: its bottom half only (centre y=50, position -2.5)
        img = _paper()
        _head(img, 200, 40)
        return img, (180.0, 40.0, 222.0, 60.0)

    def test_a_far_head_gets_an_ink_centre_candidate_and_the_row_value_stays_the_box_centres(self):
        img, box = self._far()
        row = _geometry_row(img, box, ON)
        self.assertAlmostEqual(row.value, (50.0 - 100.0) / 20.0, places=3)          # the BOX centre: untouched (rule: ledger only)
        self.assertIn("ink_centre_position_float", row.detail)
        self.assertLess(row.detail["ink_centre_position_float"], row.value)           # the ink centre is higher
        self.assertNotIn("from_head_ink", row.detail)                                 # r1's move is not made

    def test_control_flag_off_files_nothing(self):
        img, box = self._far()
        row = _geometry_row(img, box, OFF)
        self.assertNotIn("ink_centre_position_float", row.detail)
        self.assertNotIn("ink_centre_why", row.detail)

    def test_an_in_staff_head_is_unaffected(self):
        img = _paper()
        _head(img, 200, 140)                                                          # position 2, on the staff
        row = _geometry_row(img, (180.0, 130.0, 222.0, 150.0), ON)
        self.assertNotIn("ink_centre_position_float", row.detail)


def _evaluate(geom, ledger, env, ink=None, clef="treble"):
    """GATHER rows -> ADJUDICATE `notehead_position` -> EVALUATE `restate_pitch`. `ledger` an int (read) or None (abstained)."""
    log = Log()
    g = R.glyph(0, 0, 0, 0, 0)
    extra = {} if ink is None else {"ink_centre_position_float": float(ink)}
    log.observe(g, Q.NOTEHEAD_STAFF_POSITION, float(geom), reader="geometry", frame="cell:0", **extra)
    if ledger is not None:
        log.observe(g, Q.FAR_HEAD_LEDGER_POSITION, ledger, reader="ledger_farhead", frame="cell:0")
    else:
        log.abstain(g, Q.FAR_HEAD_LEDGER_POSITION, reader="ledger_farhead", frame="cell:0", reason="ledger_not_read",
                    ledger_reason="no_rungs")
    staff = R.staff(0, 0, 0)
    cv = consequences._verdict(log, staff, Q.CLEF, clef, decider="t", reason="t", basis=())
    log.freeze()
    adjudicate.adjudicate_one(log, adjudicate.REGISTRY[Q.NOTEHEAD_POSITION], g)
    with mock.patch.dict(os.environ, env):
        out = consequences.restate_pitch(log, staff, cv)
    return log, g, out


def _rec(log):
    return export.Record({"record": {"observations": [], "abstentions": [], "verdicts": log.to_json()["verdicts"]}})


class TestRestatePitchMarksTheUnreadFarHead(unittest.TestCase):
    def test_ledger_count_read_stays_plain(self):
        log, g, out = _evaluate(-3, -4, ON, ink=-3.4)
        self.assertEqual([v.value for v in out], ["C6"])                              # the ledger reading, as before
        self.assertEqual(out[0].reason, "position_and_clef")
        self.assertIsNone(export.far_unread_guess_of(_rec(log), g.to_key()))
        self.assertNotIn("guess", export._guess_fields(_rec(log), g.to_key()))

    def test_ledger_count_abstained_is_blue_with_both_candidates(self):
        log, g, out = _evaluate(-3, None, ON, ink=-4.2)
        self.assertEqual(len(out), 1)
        v = out[0]
        self.assertEqual(v.reason, head_extent.FAR_GUESS_PITCH_REASON)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        # the written value is the box centre's step (position -3 on a treble staff) -- nothing moved
        _, _, plain = _evaluate(-3, None, OFF)
        self.assertEqual(v.value, plain[0].value)
        gs = export.far_unread_guess_of(_rec(log), g.to_key())
        self.assertIsNotNone(gs)
        self.assertEqual(gs["rule"], head_extent.FAR_GUESS_REASON)
        self.assertEqual([c["source"] for c in gs["candidates"]], ["box_centre", "ink_centre"])
        self.assertEqual(len({c["value"] for c in gs["candidates"]}), 2)              # the two differ: still blue, never plain
        self.assertEqual(gs["chosen"]["value"], v.value)
        self.assertEqual(export._guess_fields(_rec(log), g.to_key())["guess"]["rule"], head_extent.FAR_GUESS_REASON)

    def test_where_both_centres_agree_it_is_still_blue(self):
        log, g, out = _evaluate(-3, None, ON, ink=-3.1)
        gs = export.far_unread_guess_of(_rec(log), g.to_key())
        self.assertIsNotNone(gs)
        self.assertEqual(len(gs["candidates"]), 2)

    def test_no_ink_centre_is_blue_with_the_box_candidate_alone(self):
        log, g, out = _evaluate(-3, None, ON, ink=None)
        gs = export.far_unread_guess_of(_rec(log), g.to_key())
        self.assertEqual([c["source"] for c in gs["candidates"]], ["box_centre"])

    def test_control_flag_off_is_plain_exactly_as_before(self):
        log, g, out = _evaluate(-3, None, OFF, ink=-4.2)
        self.assertEqual(out[0].reason, "position_and_clef")
        self.assertIsNone(export.far_unread_guess_of(_rec(log), g.to_key()))

    def test_an_in_staff_head_is_unaffected(self):
        # an on-staff head has no ledger reading at all: no NOTEHEAD_POSITION verdict, so no far abstention to mark
        log = Log()
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, 3.0, reader="geometry", frame="cell:0")
        staff = R.staff(0, 0, 0)
        cv = consequences._verdict(log, staff, Q.CLEF, "treble", decider="t", reason="t", basis=())
        log.freeze()
        with mock.patch.dict(os.environ, ON):
            out = consequences.restate_pitch(log, staff, cv)
        self.assertEqual(out[0].reason, "position_and_clef")
        self.assertIsNone(export.far_unread_guess_of(_rec(log), g.to_key()))

    def test_default_is_off(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(head_extent.FAR_GUESS_ENV, None)
            self.assertFalse(head_extent.far_guess_enabled())


class TestMoveGlyphReowned(unittest.TestCase):
    """`move_glyph`'s `reowned` branch writes the band-distance geometry step on the NEW staff: the same plain fallback when that step is far."""

    def _moved(self, pos, ledger, env):
        log = Log()
        g = R.glyph(0, 0, 0, 0, 0)
        other = R.staff(0, 0, 1)
        log.observe(g, Q.GLYPH_BAND_DISTANCE, 1.0, reader="geometry", frame="cell:0", candidate=other.to_key(), position_in_candidate=pos)
        if ledger is not None:
            log.observe(g, Q.FAR_HEAD_OWNER_LEDGER, ledger, reader=R.READERS.LEDGER_OWNER_NOTE_FIRST, frame="cell:0", candidate=other.to_key())
        cv = consequences._verdict(log, other, Q.CLEF, "treble", decider="t", reason="t", basis=())
        ov = consequences._verdict(log, g, Q.GLYPH_OWNER, other.to_key(), decider="t", reason="t", basis=())
        log.freeze()
        with mock.patch.dict(os.environ, env):
            out = consequences.move_glyph(log, g, ov)
        return log, g, out

    def test_far_on_the_new_staff_with_no_ledger_reading_is_blue(self):
        log, g, out = self._moved(-4, None, ON)
        self.assertEqual(out[0].reason, head_extent.FAR_GUESS_PITCH_REASON)
        self.assertIsNotNone(export.far_unread_guess_of(_rec(log), g.to_key()))

    def test_a_ledger_reading_that_agrees_stays_plain(self):
        log, g, out = self._moved(-4, -4, ON)
        self.assertEqual(out[0].reason, "reowned")
        self.assertIsNone(export.far_unread_guess_of(_rec(log), g.to_key()))

    def test_a_ledger_reading_that_disagrees_is_blue_with_both(self):
        log, g, out = self._moved(-4, -5, ON)
        gs = export.far_unread_guess_of(_rec(log), g.to_key())
        self.assertEqual([c["source"] for c in gs["candidates"]], ["box_centre", "ledger_toward_owner"])
        self.assertEqual(len({c["value"] for c in gs["candidates"]}), 2)

    def test_in_staff_on_the_new_staff_and_flag_off_are_plain(self):
        self.assertEqual(self._moved(4, None, ON)[2][0].reason, "reowned")
        self.assertEqual(self._moved(-4, None, OFF)[2][0].reason, "reowned")


if __name__ == "__main__":
    unittest.main()
