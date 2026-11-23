"""lane-dot-by-ink (`OMR_DOT_BY_HEAD_INK`, default OFF): an augmentation dot is placed against its head's OWN oval of ink
where the detector box holds only part of the head.

Every control is a REAL cell: the GATHER rows of the 2026-11-21 frozen-sample record (`lr-r7-frozen`, the arm with main's
2.324 clef reader), copied verbatim with every row they name (`fixtures/dot_by_head_ink/*.json`), rebuilt and
re-adjudicated with the flag off and on. Nothing is drawn.
"""
from __future__ import annotations

import json
import os
import pathlib
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged.adjudicators import aug_dot_join as AJ
from tools.omr.staged.record import Outcome, Q, Scope, Subject
from tools.omr.staged.review import rerun as RR

FIX = pathlib.Path(__file__).parent / "fixtures" / "dot_by_head_ink"
_CACHE = {}


def _run(name, flag):
    if (name, flag) not in _CACHE:
        rec = json.loads((FIX / (name + ".json")).read_text())
        with mock.patch.dict(os.environ, {AJ.DOT_BY_HEAD_INK_ENV: flag}):
            log, _ = RR.rebuild_gather(rec)
            adjudicate.run(log)
        _CACHE[(name, flag)] = log
    return _CACHE[(name, flag)]


def _role(log, key):
    return log.verdict(Q.DOT_ROLE, Subject.from_key(key))


def _dur(log, key):
    return log.verdict(Q.DURATION, Subject.from_key(key))


def _brief(v):
    return None if v is None else (v.outcome, json.dumps(v.value, sort_keys=True))


class TestTheLedgerLineHalf(unittest.TestCase):
    """Brahms p0 staff 4 bar 3 (`glyph/0/0/4/2/5`): a hollow half on the second ledger line below, its detector box over
    the lower two-thirds of the head (Sean re-drew that box on his labelled page). Its dot `glyph/0/0/4/2/2` stands 0.80
    sp above the box centre (past the 0.75 window) and 0.57 above the head's own ink."""

    def test_FLAG_OFF_the_dot_is_unplaced_and_the_note_half_or_dotted_half(self):
        log = _run("brahms_p0_ledger_half", "0")
        self.assertEqual(_role(log, "glyph/0/0/4/2/2").outcome, Outcome.ABSTAINED)
        d = _dur(log, "glyph/0/0/4/2/5")
        self.assertEqual(d.outcome, Outcome.NARROWED)
        self.assertEqual(sorted(c.value["beats"] for c in d.candidates), [2.0, 3.0])

    def test_FLAG_ON_it_is_the_halfs_dot_and_the_note_a_dotted_half(self):
        log = _run("brahms_p0_ledger_half", "1")
        r = _role(log, "glyph/0/0/4/2/2")
        self.assertEqual((r.outcome, r.value, r.detail.get("head")),
                         (Outcome.DECIDED, "augmentation", "glyph/0/0/4/2/5"))
        d = _dur(log, "glyph/0/0/4/2/5")
        self.assertEqual((d.outcome, d.value["beats"], d.value["dots"]), (Outcome.DECIDED, 3.0, 1))


class TestNeverSide(unittest.TestCase):
    def _same(self, name, keys):
        off, on = _run(name, "0"), _run(name, "1")
        for k in keys:
            for get in (_role, _dur):
                self.assertEqual(_brief(get(off, k)), _brief(get(on, k)), (k, get.__name__))
        return off, on

    def test_a_chord_keeps_each_heads_own_dot(self):
        """Brahms p25 `glyph/25/1/0/8`: two hollow heads a third apart, each with its own dot. The lower head's ink trim
        runs up into the upper head's box; read as the lower head's oval it took the upper dot and left the lower one
        unplaced (the control failed before the chord-mate guard)."""
        off, on = self._same("brahms_p25_chord_two_dots",
                             ["glyph/25/1/0/8/3", "glyph/25/1/0/8/5", "glyph/25/1/0/8/11"])
        self.assertEqual(_role(on, "glyph/25/1/0/8/3").detail.get("head"), "glyph/25/1/0/8/11")
        self.assertEqual(_role(on, "glyph/25/1/0/8/5").detail.get("head"), "glyph/25/1/0/8/9")

    def test_one_head_boxed_twice_keeps_its_dot_below_the_line(self):
        """Brahms p8 `glyph/8/0/2/0/12`: a dotted half on a line, dot in the space below, the head boxed whole (`/10`) and
        in part (`/12`). The part box's ink grows into the whole box: that ink is the same head, the box is kept."""
        off, on = self._same("brahms_p8_twin_boxes_dot_below", ["glyph/8/0/2/0/5", "glyph/8/0/2/0/12"])
        self.assertEqual(_dur(on, "glyph/8/0/2/0/12").value["dots"], 1)

    def test_a_staccato_stays_a_staccato(self):
        """Brahms p4 `glyph/4/0/7/1/12`, a staccato under a staff-6 note whose cut-off piece the staff-7 cell also boxed
        (`glyph/4/0/7/1/13`). ON it is still a staccato; its owner becomes the real note `glyph/4/0/6/1/0`, as the
        piece's oval is read from its ink (the export then writes the staccato it lost OFF)."""
        off, on = _run("brahms_p4_staccato_under_a_twin", "0"), _run("brahms_p4_staccato_under_a_twin", "1")
        for log in (off, on):
            self.assertEqual(_role(log, "glyph/4/0/7/1/12").value, "staccato")
        self.assertEqual(_role(off, "glyph/4/0/7/1/12").detail.get("owner"), "glyph/4/0/7/1/13")
        self.assertEqual(_role(on, "glyph/4/0/7/1/12").detail.get("owner"), "glyph/4/0/6/1/0")

    def test_an_undotted_note_beside_dotted_ones_takes_no_dot(self):
        """Brahms p12 `glyph/12/1/0/0/14`, a plain quarter whose oval the flag re-reads, in a bar of dotted quarters."""
        off, on = self._same("brahms_p12_undotted_beside_dotted",
                             ["glyph/12/1/0/0/14", "glyph/12/1/0/0/6", "glyph/12/1/0/0/15"])
        self.assertEqual(_dur(on, "glyph/12/1/0/0/14").value["dots"], 0)

    def test_the_two_voice_b_flat_has_no_dot_box_to_place(self):
        """Brahms p5 `glyph/5/1/5/4/9` (two-voice lane tile 11): its printed dot was never boxed -- the cell holds no
        `Q.AUG_DOT` -- so placing dots by ink cannot reach it; the B-flat stays a plain quarter both ways (ROADMAP 2.329)."""
        off, on = self._same("brahms_p5_bflat_unboxed_dot", ["glyph/5/1/5/4/9"])
        self.assertFalse(on.rows(Q.AUG_DOT, Subject.from_key("cell/5/1/5/4"), scope=Scope.SELF_AND_DESCENDANTS))
        self.assertEqual(_dur(on, "glyph/5/1/5/4/9").value["dots"], 0)


class TestHeadOvalFromInk(unittest.TestCase):
    """The two numbers' boundaries, on the case head's own filed values (`glyph/0/0/4/2/5`)."""
    BOX, PAGE, SPACE = (122.0, 997.0, 124.0, 68.0), [2710.65, 3264.03, 2750.95, 3286.12], 100.0

    def _row(self, trimmed):
        from tools.omr.staged.record import Log, READERS
        log = Log()
        g = Subject.from_key("glyph/0/0/4/2/5")
        log.observe(g, Q.HEAD_INK, "hollow", reader=READERS.CV_HEAD_INK, frame="cell:2", trimmed=trimmed)
        return log.rows(Q.HEAD_INK, g)[-1]

    def test_the_real_trim_is_the_oval(self):
        oval = AJ.head_oval_from_ink(self.BOX, self.PAGE, self._row([2713, 3249, 2756, 3285]), self.SPACE)
        self.assertIsNotNone(oval)
        self.assertLess(oval[1], self.BOX[1])

    def test_ink_taller_than_one_head_keeps_the_box(self):
        self.assertIsNone(AJ.head_oval_from_ink(self.BOX, self.PAGE, self._row([2713, 3240, 2756, 3290]), self.SPACE))

    def test_ink_barely_past_the_box_keeps_the_box(self):
        self.assertIsNone(AJ.head_oval_from_ink(self.BOX, self.PAGE, self._row([2713, 3260, 2756, 3285]), self.SPACE))

    def test_no_filed_ink_keeps_the_box(self):
        self.assertIsNone(AJ.head_oval_from_ink(self.BOX, self.PAGE, None, self.SPACE))

    def test_default_is_on(self):
        # Sean 2026-11-23: default ON; `0`/false still switches it off
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(AJ.DOT_BY_HEAD_INK_ENV, None)
            self.assertTrue(AJ.dot_by_head_ink_enabled())
            for off in ("0", "false"):
                os.environ[AJ.DOT_BY_HEAD_INK_ENV] = off
                self.assertFalse(AJ.dot_by_head_ink_enabled())


if __name__ == "__main__":
    unittest.main()
