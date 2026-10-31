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
from tools.omr.staged.record import Log, Outcome, Q, READERS, STROKE_GLYPH_BASE

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


def _box(log, gi, cls, box, *, head=True, pos=4.0, strokes=None, split=None):
    g = R.glyph(5, 0, 4, 4, gi)
    if head:
        log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR, frame="cell:4", score=0.29)
    x, y, w, h = box
    log.observe(g, Q.GLYPH_BOX, (cls,) + tuple(box), reader=READERS.DETECTOR, frame="cell:4", score=0.29,
                bbox_page_px=[3500 + x, 1400 + y, 3500 + x + w, 1400 + y + h], **({"box_kind": split} if split is not None else {}))
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

    def _case3(self, env, split=None):
        log = _log()
        wide = _box(log, 15, "noteheadBlackOnLine", WIDE, split=split)
        head = _box(log, 0, "noteheadBlackInSpace", HEAD, pos=5.0)
        _run(log, env)
        return log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, wide), log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, head)

    def test_ON_inside_read_no_head_left_the_slur_box_is_the_remainder_and_refused_RED(self):
        wide, head = self._case3(ON, split={"heads": 0, "added": [], "unread": False})
        self.assertEqual((wide.value, wide.reason), (True, "wider_than_a_head"))
        self.assertEqual(wide.detail["box_spaces"][0], round(int(5.19 * SP) / SP, 3))

    def test_ON_inside_not_read_the_box_ABSTAINS_never_kept_as_one_head(self):
        for split in (None, {"heads": 1, "added": [], "unread": True}):
            wide, _head = self._case3(ON, split=split)
            self.assertNotEqual(wide.outcome, Outcome.DECIDED, split)
            self.assertEqual(wide.reason, "wide_box_unread")

    def test_OFF_the_rule_does_not_speak(self):
        wide, _head = self._case3(OFF, split={"heads": 0, "added": [], "unread": False})
        self.assertNotIn(wide.reason, ("wider_than_a_head", "wide_box_unread"))

    def test_CONTROL_a_real_head_beside_it_is_kept_either_way(self):
        for env in (ON, OFF):
            _wide, head = self._case3(env)
            self.assertEqual((head.value, head.reason), (False, "notehead"))


def _ink(h, w, rects):
    import numpy as np
    img = np.full((h, w), 255, np.uint8)
    for x, y, rw, rh in rects:
        img[y:y + rh, x:x + rw] = 0
    return img


class TestReadTheHeadsInsideAWideBox(unittest.TestCase):
    """Sean's tile 10 ("three eighth notes") and tile 4 ("an eighth and a natural"), drawn at 28 px a space."""

    def three_eighths(self):
        # three heads 1.3 x 1.0 sp on stems, joined by a beam 0.5 sp thick above them
        heads = [(10 + 60 * i, 120, 36, 28) for i in range(3)]
        stems = [(10 + 60 * i + 32, 40, 4, 90) for i in range(3)]
        beam = [(42, 40, 124, 14)]
        return _ink(170, 200, heads + stems + beam), heads

    def test_three_heads_on_a_beam_are_three_blobs_and_the_beam_is_not_one(self):
        img, heads = self.three_eighths()
        blobs, unread = BK.head_blobs(img == 0, SP)
        self.assertEqual(len(blobs), 3)
        self.assertFalse(unread)

    def test_an_arc_or_a_beam_alone_holds_no_head(self):
        arc = _ink(60, 200, [(0, 20 + abs(x - 100) // 12, 1, 5) for x in range(200)])
        self.assertEqual(BK.head_blobs(arc == 0, SP), ([], False))
        beam = _ink(60, 200, [(0, 20, 200, 14)])
        self.assertEqual(BK.head_blobs(beam == 0, SP), ([], False))

    def test_a_natural_beside_an_eighth_leaves_the_eighths_head_only(self):
        natural = [(10, 10, 4, 80), (30, 30, 4, 80), (10, 40, 24, 7), (10, 62, 24, 7)]
        img = _ink(120, 140, natural + [(70, 60, 36, 28), (102, 0, 4, 70)])
        blobs, unread = BK.head_blobs(img == 0, SP)
        self.assertEqual(len(blobs), 1)
        self.assertGreater(blobs[0][0], 60)

    def test_fused_head_thick_ink_is_UNREAD(self):
        blobs, unread = BK.head_blobs((_ink(60, 200, [(10, 10, 120, 30)]) == 0), SP)
        self.assertEqual(blobs, [])
        self.assertTrue(unread)

    def test_split_appends_only_heads_no_other_box_stands_on_and_keeps_every_index(self):
        from types import SimpleNamespace as N
        import dataclasses

        @dataclasses.dataclass
        class D:
            smufl_name: str
            x_canonical: int
            y_canonical: int
            width_canonical: int
            height_canonical: int
            confidence: float = 0.3
        img, heads = self.three_eighths()
        own = D("noteheadBlackOnLine", *heads[0])                     # the first head already has its own box
        wide = D("noteheadBlackOnLine", 0, 110, 190, 50)
        out, info = BK.split_wide_heads([own, wide], img, SP)
        self.assertEqual(out[:2], [own, wide])
        self.assertEqual(len(out), 4)                                  # heads 2 and 3 added, head 1 not twice
        self.assertEqual(info[1]["box_kind"], {"heads": 3, "added": [2, 3], "unread": False})
        self.assertEqual(info[2]["box_kind"], {"split_from": 1})
        self.assertEqual(BK.split_wide_heads([own], img, SP), ([own], {}))   # nothing wide: unchanged
        _ = N


class TestArcsBowAndHairpinsAreWiderThanLetters(unittest.TestCase):

    def test_case_2_a_hairpin_leg_does_not_bow_RED(self):
        # Brahms p19 glyph/19/0/9/1/17: x 1820 -> 1939, centre y 2751 -> 2757.5, 27.5 px a space
        tr = [[1820 + i, 2750 + i * 6.5 / 119, 2752 + i * 6.5 / 119] for i in range(120)]
        self.assertTrue(BK.trace_is_not_an_arc(tr, 27.5))

    def test_TWIN_a_tie_bows(self):
        import math
        tr = [[x, 100 + 12 * math.sin(math.pi * x / 120), 104 + 12 * math.sin(math.pi * x / 120)] for x in range(121)]
        self.assertFalse(BK.trace_is_not_an_arc(tr, 27.5))

    def test_TWIN_a_short_straight_piece_is_left_alone(self):
        self.assertFalse(BK.trace_is_not_an_arc([[x, 10, 12] for x in range(60)], 27.5))

    def test_the_letter_cut_sits_in_the_measured_gap(self):
        self.assertTrue(1.46 < BK.HAIRPIN_MIN_W_SP < 2.02)


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
