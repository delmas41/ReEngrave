"""ROADMAP 2.245 -- a detector box is tested against its own class's printed size before it stands as that kind (STAGED ADJUDICATE, flag
`OMR_BOX_KIND_SIZE`, default OFF; `tools/omr/staged/box_kind.py`).

Real numbers, the 20261029-night record (benchmarks/wrong-kind-boxes-2026-10/FINDINGS.md): Sean's 2.240-s2 tile 12 is Brahms p5
`glyph/5/0/4/4/15`, a `noteheadBlackOnLine` box at 0.287, 5.19 x 1.53 spaces, on a slur four other boxes (`slur`/`tie`) already name;
ADJUDICATE kept it as a head. The four cases of the lane, and what this rule does and does NOT claim to reach:
  1. Litolff p10 `glyph/10/1/9/7/12` (ledger line + the bottom of a head, 1.85 x 0.59): NOT this rule -- ADJUDICATE already refuses it
     `notehead_is_a_duplicate_box`; the page owner (2.240) read a refused box. Pinned here as a control the rule leaves alone.
  2. Brahms p19 `glyph/19/0/9/1/17` (`tie`, a hairpin's leg): NOT this rule -- a size fits a tie; the ink does not bow (2.223).
  3. Brahms p5 `glyph/5/0/4/4/15`: THIS rule (RED with the flag off).
  4. Litolff p4 `glyph/4/0/8/5/8` (eighth rest, a head box 0.92 wide): NOT this rule -- `too_narrow` already refuses it (2.242's
     accidental box is what blocks the eighth-rest reader).
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import box_kind as BK
from tools.omr.staged import record as R
from tools.omr.staged import stroke_owner as SO
from tools.omr.staged.record import Log, Q, READERS, STROKE_GLYPH_BASE

ON = {BK.ENV: "1"}
OFF = {BK.ENV: "0"}
SP = 28.0                                   # canonical px per space in these synthetic cells
CELL = R.cell(5, 0, 4, 4)


class TestThePredicate(unittest.TestCase):

    def test_case_3_a_head_box_five_spaces_wide_is_not_one_head_RED(self):
        got = BK.head_box_misfit("noteheadBlackOnLine", 5.19, 1.53)
        self.assertEqual(got[0], "wider_than_a_head")
        self.assertAlmostEqual(got[1], 5.19 - BK.HEAD_BOX_MAX_W_SP, places=6)

    def test_TWIN_real_heads_and_two_heads_abreast_are_left_alone(self):
        # a black head (Brahms median 1.36 x 1.12), a Litolff merged head (1.85 wide), a whole (1.7), two heads of a second (2.6)
        for w, h in ((1.36, 1.12), (1.85, 1.57), (1.7, 1.0), (2.6, 1.6), (2.99, 1.3)):
            self.assertIsNone(BK.head_box_misfit("noteheadBlackInSpace", w, h), (w, h))

    def test_case_1_and_4_are_not_this_rules(self):
        self.assertIsNone(BK.head_box_misfit("noteheadBlackOnLine", 1.85, 0.59))     # Litolff p10 tile 2: refused as a duplicate already
        self.assertIsNone(BK.head_box_misfit("noteheadBlackInSpace", 0.92, 0.87))    # Litolff p4: refused too_narrow already
        self.assertIsNone(BK.head_box_misfit("tie", 5.69, 0.58))                     # Brahms p19: not a head class

    def test_the_bound_is_the_stroke_owners_own_head_size(self):
        self.assertEqual(BK.HEAD_BOX_MAX_W_SP, SO.HEAD_MAX_W_SP)

    def test_default_off_and_deny_list_words(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(BK.ENV, None)
            self.assertFalse(BK.enabled())
        for val, want in (("1", True), ("on", True), ("yes", True), ("0", False), ("off", False), ("no", False), ("false", False),
                          ("", False)):
            with mock.patch.dict(os.environ, {BK.ENV: val}):
                self.assertEqual(BK.enabled(), want, val)


def _log():
    log = Log()
    log.observe(CELL, Q.CELL_STAFF_SPACE, SP, reader=READERS.GEOMETRY, frame="cell:4")
    return log


def _box(log, gi, cls, box, *, head=True, pos=4.0, strokes=None):
    g = R.glyph(5, 0, 4, 4, gi)
    if head:
        log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR, frame="cell:4", score=0.29)
    x, y, w, h = box
    log.observe(g, Q.GLYPH_BOX, (cls,) + tuple(box), reader=READERS.DETECTOR, frame="cell:4", score=0.29,
                bbox_page_px=[3500 + x, 1400 + y, 3500 + x + w, 1400 + y + h])
    if head:
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, float(pos), reader=READERS.GEOMETRY, frame="cell:4")
    if strokes is not None:
        log.observe(g, Q.GLYPH_STROKES, list(strokes), reader=READERS.CV_GLYPH_STROKES, frame="cell:4",
                    shares=[1.0] * len(strokes), cover_min=0.5)
    return g


def _run(log, env):
    with mock.patch.dict(os.environ, env):
        adjudicate.run(log)
    return log


#: the slur of tile 12, canonical: 5.19 x 1.53 spaces (the head box and the slur boxes share it)
WIDE = (100, 300, int(5.19 * SP), int(1.53 * SP))
HEAD = (40, 290, int(1.36 * SP), int(1.12 * SP))


class TestNoteheadIsNotANotehead(unittest.TestCase):

    def _case3(self, env):
        log = _log()
        wide = _box(log, 15, "noteheadBlackOnLine", WIDE)
        head = _box(log, 0, "noteheadBlackInSpace", HEAD, pos=5.0)
        _run(log, env)
        return log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, wide), log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, head)

    def test_ON_the_slur_wide_head_box_is_refused_wider_than_a_head_RED(self):
        wide, head = self._case3(ON)
        self.assertEqual((wide.value, wide.reason), (True, "wider_than_a_head"))
        self.assertEqual(wide.detail["box_spaces"][0], round(int(5.19 * SP) / SP, 3))

    def test_OFF_the_rule_does_not_speak(self):
        wide, _head = self._case3(OFF)
        self.assertNotEqual(wide.reason, "wider_than_a_head")

    def test_CONTROL_a_real_head_beside_it_is_kept_either_way(self):
        for env in (ON, OFF):
            _wide, head = self._case3(env)
            self.assertNotEqual(head.reason, "wider_than_a_head")


class TestTheStrokeOwnerNeedsNoSizeVeto(unittest.TestCase):
    """Measured (FINDINGS): a size veto in the stroke owner lost real MERGED-head eighths on Litolff (the wide box is the only claimant
    big enough to hold a fused head blob), so the owner has none. Where the wide box stands on a slur, the per-stroke shape already
    refuses it: the slur's curve is the arc's with the flag ON or OFF."""

    def _cell(self, env):
        log = _log()
        strokes = [("curve", (100, 300, int(5.19 * SP), int(1.53 * SP)), 5.3, 0.15, 0.6),
                   ("blob", (40, 290, int(1.3 * SP), int(1.1 * SP)), 1.3, 1.0, None)]
        for i, (kind, box, L, T, sag) in enumerate(strokes):
            log.observe(R.glyph(5, 0, 4, 4, STROKE_GLYPH_BASE + i), Q.STROKE, kind, reader=READERS.CV_STROKE, frame="cell:4",
                        stroke_box=list(box), length_spaces=L, angle_deg=0.0, thickness_spaces=T, thickness_spread_spaces=0.02,
                        fill=0.3 if kind == "curve" else 0.9, sagitta_spaces=sag, touches=[], staff_space_local_px=SP,
                        ends=[0, 0, 0, 0], end_steps_from_top=[0.0, 0.0], component=i)
        wide = _box(log, 15, "noteheadBlackOnLine", WIDE, strokes=[0])
        _box(log, 8, "slur", WIDE, head=False, strokes=[0])
        _box(log, 0, "noteheadBlackInSpace", HEAD, pos=5.0, strokes=[1])
        _run(log, env)
        return log.verdict(Q.STROKE_OWNER, CELL), wide.to_key()

    def test_the_slur_stroke_is_the_arcs_and_the_head_keeps_its_blob_either_way(self):
        for env in (ON, OFF):
            v, wide = self._cell(env)
            self.assertEqual(v.detail["strokes"]["0"][1], "arc", env)
            self.assertEqual(v.detail["strokes"]["1"][1], "head", env)
            self.assertNotIn(wide, v.detail.get("vetoes") or {})


if __name__ == "__main__":
    unittest.main()
