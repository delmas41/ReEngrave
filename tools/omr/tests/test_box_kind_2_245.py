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

import dataclasses
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


def _paper(h, w):
    import numpy as np
    return np.full((h, w), 255, np.uint8)


def _ellipse(img, cx, cy, w, h, hollow=False):
    import cv2
    cv2.ellipse(img, (int(cx), int(cy)), (int(w / 2), int(h / 2)), -20, 0, 360, 0, -1)
    if hollow:
        cv2.ellipse(img, (int(cx), int(cy)), (int(w / 2) - 7, int(h / 2) - 7), -20, 0, 360, 255, -1)


def _rect(img, x, y, w, h):
    img[y:y + h, x:x + w] = 0


@dataclasses.dataclass
class _D:
    smufl_name: str
    x_canonical: int
    y_canonical: int
    width_canonical: int
    height_canonical: int
    confidence: float = 0.3


S3 = 40.0         # canonical px per space in the round-3 cells; staff top at y 200, so a head centre on a line is at 200 + 20 k


class TestRoundThreeHeadsHaveAHeadsOwnShape(unittest.TestCase):
    """Sean's round-2 tiles (2026-10-31): 5, 8 right; 2 (a stem and a flag) and 10 (a C clef piece) wrong as heads; remainders 3 (a head
    under a slur) and 6 (a HALF note) must not be refused with a head inside."""

    def split(self, img, dets, i=None):
        out, info = BK.split_wide_heads(dets, img, S3, staff_top=200.0)
        wide = [k for k, d in enumerate(dets) if d.width_canonical / S3 >= BK.HEAD_BOX_MAX_W_SP][0] if i is None else i
        return out, info[wide]["box_kind"]

    def test_tile_10_three_merged_beamed_eighths_are_three_heads_RED(self):
        img = _paper(600, 400)
        for k in range(3):                                        # heads touching side by side (Litolff merges), centres on y 300
            _ellipse(img, 70 + 52 * k, 300, 54, 40)
            _rect(img, 70 + 52 * k + 22, 150, 6, 150)             # up stems at the heads' right
        _rect(img, 92, 150, 116, 20)                              # the beam (0.5 sp)
        out, bk = self.split(img, [_D("noteheadBlackOnLine", 40, 270, 180, 60)])
        self.assertFalse(bk["unread"], bk)
        self.assertEqual(len(bk["added"]), 3, bk)

    def test_tile_6_a_hollow_head_is_found_or_the_box_abstains_never_refused_RED(self):
        img = _paper(600, 400)
        _ellipse(img, 120, 300, 54, 40, hollow=True)
        img[298:302, :] = 255                                     # the staff line through it, erased
        _rect(img, 144, 160, 5, 140)
        out, bk = self.split(img, [_D("noteheadBlackOnLine", 60, 250, 140, 110)])
        self.assertTrue(bk["added"] or bk["unread"], bk)
        if bk["added"]:
            self.assertTrue(out[bk["added"][0]] is not None)

    def test_tile_2_a_flags_curl_at_the_stem_tip_is_not_a_head_RED(self):
        img = _paper(600, 400)
        _ellipse(img, 100, 380, 54, 40)                           # the head, with its own box
        _rect(img, 122, 220, 6, 160)                              # its stem up
        _ellipse(img, 140, 240, 44, 36)                           # a thick flag curl hanging off the stem's top end, on a space
        head = _D("noteheadBlackInSpace", 73, 360, 54, 40)
        wide = _D("noteheadBlackOnLine", 70, 210, 130, 60)        # 3.25 sp wide over the stem's top and the curl
        out, bk = self.split(img, [head, wide], i=1)
        self.assertEqual(bk["added"], [], bk)
        self.assertTrue(bk["unread"], bk)

    def test_tile_10_a_c_clef_bowl_beside_its_thick_bar_is_not_a_head_RED(self):
        img = _paper(600, 400)
        _rect(img, 60, 160, 18, 160)                              # the clef's thick bar (0.45 sp x 4 sp)
        _ellipse(img, 110, 220, 54, 40)                           # a bowl, joined to the bar
        _rect(img, 78, 215, 10, 10)
        out, bk = self.split(img, [_D("noteheadBlackOnLine", 55, 195, 130, 60)])
        self.assertEqual(bk["added"], [], bk)
        self.assertTrue(bk["unread"], bk)

    def test_tile_3_a_head_under_a_slur_with_its_own_box_is_covered_and_the_remainder_refused(self):
        img = _paper(600, 400)
        _ellipse(img, 80, 300, 54, 40)
        for x in range(60, 260):                                  # a slur over it, thin
            y = 270 + int(((x - 160) / 100.0) ** 2 * 20)
            img[y:y + 5, x] = 0
        head = _D("noteheadBlackOnLine", 53, 280, 54, 40)
        out, bk = self.split(img, [head, _D("noteheadBlackOnLine", 50, 260, 210, 70)], i=1)
        self.assertEqual(bk["added"], [], bk)
        self.assertEqual(bk["covered"], 1, bk)
        self.assertFalse(bk["unread"], bk)

    def test_r3_tile_6_a_piece_of_a_thick_beam_between_two_stems_is_not_a_head_RED(self):
        # Litolff p8 8/1/0/17/20: a beam ~0.8 sp thick (merged with a line remnant) cut between two stems read 1.01 x 0.76 sp, fill 0.93,
        # on the grid; its ink runs on through its rows on both sides (0.82 / 0.91)
        img = _paper(600, 500)
        _rect(img, 40, 302, 300, 34)                              # the beam, 0.85 sp thick, centred on a line (y 320)
        for x in (145, 245):
            img[302:312, x:x + 10] = 255                          # where the scan thins it, the core erosion breaks it into pieces
        for x in (60, 160, 260):
            _rect(img, x, 120, 6, 190)                            # three stems down onto it
        out, bk = self.split(img, [_D("noteheadBlackOnLine", 100, 300, 130, 40)])
        self.assertEqual(bk["added"], [], bk)                     # round 3 added the piece between the two thin places
        self.assertTrue(bk["unread"], bk)

    def test_TWIN_a_lone_head_beside_the_same_stems_is_still_a_head(self):
        img = _paper(600, 500)
        _ellipse(img, 120, 320, 54, 40)
        _rect(img, 143, 170, 6, 150)
        out, bk = self.split(img, [_D("noteheadBlackOnLine", 60, 290, 130, 60)])
        self.assertEqual(len(bk["added"]), 1, bk)

    def test_an_arc_or_a_beam_alone_holds_no_head_and_the_box_is_refused(self):
        img = _paper(600, 400)
        _rect(img, 40, 290, 200, 20)                              # a beam alone
        out, bk = self.split(img, [_D("noteheadBlackOnLine", 40, 280, 200, 40)])
        self.assertEqual((bk["added"], bk["unread"]), ([], False), bk)

    def test_two_wide_boxes_add_a_head_once(self):
        img = _paper(600, 400)
        _ellipse(img, 100, 300, 54, 40)
        _rect(img, 122, 150, 6, 150)
        a, b = _D("noteheadBlackOnLine", 40, 270, 140, 60), _D("noteheadBlackInSpace", 30, 265, 150, 70)
        out, info = BK.split_wide_heads([a, b], img, S3, staff_top=200.0)
        self.assertEqual(len(out), 3)


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

    def test_case_4_the_double_sharp_box_is_far_bigger_than_a_double_sharp_RED(self):
        self.assertTrue(BK.oversized_for_its_class("accidentalDoubleSharp", 1.45, 1.87))     # printed 0.99 x 1.01
        self.assertFalse(BK.oversized_for_its_class("accidentalDoubleSharp", 1.1, 1.2))      # TWIN: its own size
        self.assertFalse(BK.oversized_for_its_class("accidentalSharp", 1.03, 3.14))          # the sharp boxes' median: left alone
        self.assertFalse(BK.oversized_for_its_class("noteheadBlackOnLine", 9.0, 9.0))        # not a sized class here

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


class TestAnUnreadWideBoxIsMarkedUnreadInTheFile(unittest.TestCase):
    """Sean's r3 tile 1 (Litolff p2 2/0/7/10/3, a real half in a box whose inside is not read): never written as a note and never a silent
    gap -- EXPORT drops it under `unread:wide_box_unread`, which `_attach_unplaced` files as an unread glyph of its bar."""

    def _rec(self, env, split):
        from tools.omr.staged import export as SX
        log = _log()
        wide = _box(log, 15, "noteheadBlackOnLine", WIDE, split=split)
        _run(log, env)
        return SX._place_notes(SX.Record({"record": log.to_json()}), {}), SX

    def test_ON_unread_the_box_is_dropped_as_UNREAD_and_is_a_gap_RED(self):
        dropped, SX = self._rec(ON, {"heads": 0, "added": [], "unread": True})
        self.assertEqual(dropped.get("unread:wide_box_unread"), 1, dict(dropped))
        self.assertNotIn("unread:wide_box_unread", SX._NOT_A_GAP_REASONS)

    def test_TWIN_OFF_nothing_is_dropped_under_that_name(self):
        dropped, _SX = self._rec(OFF, {"heads": 0, "added": [], "unread": True})
        self.assertNotIn("unread:wide_box_unread", dropped)
