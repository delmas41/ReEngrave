"""ROADMAP 2.238 (STAGED ADJUDICATE, flag `OMR_OWNER_SHAPE`, default ON since 2026-10-30): the stroke owner learns the old pair rules' SHAPE evidence as
vetoes, and the precision rules read its box verdict. Constructed cells, shaped on Sean's 2.237 tiles (benchmarks/rule-page/FINDINGS.md).
Every RED case has a twin that must NOT fire; `vetoes=None` is the 2.205 behaviour exactly (the control that can fail)."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import stroke_owner as SO
from tools.omr.staged.adjudicators import stroke_owner as SOA

SP = 100.0


def ink(o, kind, box, length, thick, area=None, touches=()):
    w, h = box[2] / SP, box[3] / SP
    return SO.Ink(o, kind, tuple(float(v) for v in box), length, thick, (w * h * 0.8 if area is None else area), SP,
                  tuple((j, 1.0) for j in touches), "s%d" % o, 0.0)


def claim(key, cls, covers=()):
    return SO.Claim(key, SO.family_of(cls), cls, tuple(covers), (), "gs:" + key)


class TestFlag(unittest.TestCase):

    def test_default_on_and_only_an_explicit_no_disables(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(SO.ENV_SHAPE, None)
            self.assertTrue(SO.owner_shape_enabled())
        for v, want in (("1", True), ("on", True), ("0", False), ("off", False), ("", True)):
            with mock.patch.dict(os.environ, {SO.ENV_SHAPE: v}):
                self.assertIs(SO.owner_shape_enabled(), want)


class TestAHeadPieceOnAQuarterRest(unittest.TestCase):
    """Tile 9 (Brahms 8/1/8/11): a whole-note box on the foot of a quarter rest. Its pieces are small ("could"), it shares a stroke with a
    rest box that holds clear rest pieces: under 2.205 the head-first order took the shared stroke and refused the rest's claim on it."""
    REST_A = ink(4, "blob", (0, 0, 20, 80), 0.88, 0.19, area=0.12)       # 0.2 x 0.8 sp: a rest body piece, too small for a head
    SHARED = ink(5, "horizontal", (0, 80, 119, 25), 1.19, 0.25, area=0.28, touches=(4, 3))
    FOOT = ink(3, "blob", (10, 105, 31, 30), 0.55, 0.30, area=0.13, touches=(5,))
    REST = claim("rest", "restQuarter", covers=(4, 5))
    HEAD = claim("head", "noteheadWholeInSpace", covers=(3, 5))

    def strokes(self):
        return [self.REST_A, self.SHARED, self.FOOT]

    def test_2205_gives_the_shared_stroke_to_the_head_CONTROL(self):
        own = SO.own_strokes(self.strokes(), [self.REST, self.HEAD])
        self.assertEqual(own[5].family, "head")
        self.assertEqual(SO.box_verdict(self.HEAD, own, {s.ordinal: s for s in self.strokes()})["verdict"], "owns")

    def test_the_shapeless_head_yields_its_ink_to_the_rest_RED(self):
        v = SO.structural_vetoes(self.strokes(), [self.REST, self.HEAD])
        self.assertEqual(set(v), {"head"})
        own = SO.own_strokes(self.strokes(), [self.REST, self.HEAD], vetoes=v)
        self.assertEqual((own[5].family, own[3].family), ("rest", "rest"))
        by = {s.ordinal: s for s in self.strokes()}
        self.assertEqual(SO.box_verdict(self.HEAD, own, by)["verdict"], "refused")
        self.assertEqual(SO.box_verdict(self.REST, own, by)["verdict"], "owns")

    def test_a_head_with_a_clear_head_blob_is_not_vetoed_GREEN(self):
        head_blob = ink(3, "blob", (10, 105, 130, 100), 1.3, 1.0, area=1.0, touches=(5,))
        self.assertEqual(SO.structural_vetoes([self.REST_A, self.SHARED, head_blob], [self.REST, self.HEAD]), {})

    def test_a_rest_with_no_clear_piece_vetoes_nothing_GREEN(self):
        rest = claim("rest", "restQuarter", covers=(5,))
        self.assertEqual(SO.structural_vetoes(self.strokes(), [rest, self.HEAD]), {})


class TestANamedRivalAndAVetoWithoutOne(unittest.TestCase):

    def test_a_letter_veto_hands_the_heads_ink_to_the_letter_RED(self):
        hook = ink(0, "blob", (0, 0, 82, 95), 1.03, 0.51, area=0.44)       # tile 7: an f's hook, CLEAR as a head blob by size alone
        head = claim("head", "noteheadBlackOnLine", covers=(0,))
        own = SO.own_strokes([hook], [head], vetoes={"head": SO.Veto("on_a_dynamic_letter", "glyph/letter", "dynamic", "dynamicF")})
        self.assertEqual((own[0].state, own[0].family, own[0].owners), ("decided", "dynamic", ("glyph/letter",)))
        self.assertEqual(SO.box_verdict(head, own, {0: hook})["verdict"], "refused")
        self.assertEqual(SO.own_strokes([hook], [head])[0].family, "head")                 # control: no veto, the head owns it

    def test_a_rest_into_a_head_veto_leaves_the_stem_to_the_consumers_RED(self):
        stem = ink(0, "vertical", (0, 0, 19, 369), 3.75, 0.19)              # tile 4: a 3.75-sp stem under a quarter-rest box
        rest = claim("rest", "restQuarter", covers=(0,))
        own = SO.own_strokes([stem], [rest], vetoes={"rest": SO.Veto("rest_stroke_into_a_head")})
        self.assertEqual(own[0].state, "refused_claims")
        self.assertFalse(own[0].claimed)
        self.assertEqual(SO.box_verdict(rest, own, {0: stem})["verdict"], "refused")

    def test_a_veto_that_needs_a_clear_rival_holds_only_with_one(self):
        acc = ink(0, "blob", (0, 0, 62, 75), 0.84, 0.43, area=0.34)
        body = ink(1, "blob", (0, 80, 62, 75), 0.84, 0.43, area=0.34)
        a = claim("acc", "accidentalDoubleSharp", covers=(0,))
        veto = {"acc": SO.Veto("acc_on_a_rest", "rest", "rest", "rest8th", rival_must_be_clear=True)}
        with_clear = SO.own_strokes([acc, body], [a, claim("rest", "rest8th", covers=(0, 1))], vetoes=veto)
        self.assertEqual(with_clear[0].family, "rest")
        stem_only = ink(1, "vertical", (0, 80, 19, 500), 5.0, 0.19)      # the rival's only piece is no rest piece: the veto does not hold
        without = SO.own_strokes([acc, stem_only], [a, claim("rest", "rest8th", covers=(1,))], vetoes=veto)
        self.assertEqual(without[0].family, "accidental")


class TestSeansRound2Tiles(unittest.TestCase):
    """Sean's 2.238 tiles (out/print/2.238-tiles/answers.json): three places the first build wrote wrong."""

    def test_tile4_a_rest_box_on_a_half_note_and_its_stem_RED(self):
        # Litolff 6/1/11/5/2: the box covers the hollow head's pieces (fit as rest pieces) and the 4.5-sp stem joined to them
        piece = ink(8, "blob", (0, 380, 49, 110), 1.10, 0.50, area=0.44, touches=(10,))
        stem = ink(10, "vertical", (40, 0, 38, 450), 4.50, 0.38, touches=(8,))
        rest = claim("rest", "restQuarter", covers=(8, 10))
        self.assertEqual(SO.structural_vetoes([piece, stem], [rest]), {"rest": SO.Veto("rest_holds_a_stem")})
        own = SO.own_strokes([piece, stem], [rest])
        self.assertEqual(SO.box_verdict(rest, own, {8: piece, 10: stem})["verdict"], "owns")      # control: 2.205 alone keeps it

    def test_tile10_a_real_eighth_rest_holds_no_stroke_a_rest_never_prints_GREEN(self):
        body = ink(5, "blob", (0, 0, 87, 130), 1.35, 0.81, area=0.80, touches=(9,))
        tail = ink(9, "vertical", (60, 100, 19, 161), 1.62, 0.19, touches=(5,))
        self.assertEqual(SO.structural_vetoes([body, tail], [claim("rest", "rest8th", covers=(5, 9))]), {})

    def test_tile11_a_vetoed_rest_is_never_a_heads_rival_RED(self):
        # Litolff 8/1/0/0: a false quarter-rest box on a unison head, itself refused as running into a head, took the head's ink
        blob = ink(72, "blob", (0, 0, 144, 100), 1.44, 0.2, area=0.2)
        head = claim("head", "noteheadBlackInSpace", covers=(72,))
        rest = claim("rest", "restQuarter", covers=(72,))
        clear_rest = ink(73, "blob", (0, 120, 50, 100), 1.0, 0.5, area=0.4)
        rest2 = claim("rest", "restQuarter", covers=(72, 73))
        self.assertIn("head", SO.structural_vetoes([blob, clear_rest], [head, rest2]))                # control: an unvetoed rival
        self.assertNotIn("head", SO.structural_vetoes([blob, clear_rest], [head, rest2],
                                                      already={"rest": SO.Veto("rest_stroke_into_a_head")}))
        own = SO.own_strokes([blob], [head, rest], vetoes={"head": SO.Veto("head_piece_on_a_rest", "rest", "rest", "restQuarter"),
                                                           "rest": SO.Veto("rest_stroke_into_a_head")})
        self.assertNotIn("rest", own[72].owners)

    def test_tile1_owns_does_not_silence_the_whole_on_a_rest_rule(self):
        import inspect
        from tools.omr.staged.adjudicators import notehead_precision as NP
        src = inspect.getsource(NP.adjudicate_notehead_is_not_a_notehead)
        self.assertIn("if whole_refusal is not None:\n        return whole_refusal", src)


class TestSeansRound3Tile(unittest.TestCase):
    """Sean's 2.238 round-2 tile 1 (Brahms 5/0/13/2/5, "8"): refusing a false quarter-rest box on an eighth's unread stem left the bar
    unable to sum and main's real eighth was held out red. `rest_holds_a_stem` may not refuse: the old rules decide, a kept box is
    NARROWED (written blue, never plain)."""

    def test_the_veto_hands_the_box_to_the_old_rules_and_narrows_what_they_keep(self):
        import inspect
        from tools.omr.staged.adjudicators import family_precision as FP
        src = inspect.getsource(FP.adjudicate_rest_is_not_a_rest)
        self.assertIn('== "rest_holds_a_stem"', src)
        self.assertIn('owner_says = "silent"', src)
        self.assertIn('"rest_holds_a_stem",', src)                       # the narrowing's reason, declared and returned
        from tools.omr.staged import adjudicate
        from tools.omr.staged.record import Q
        self.assertIn("rest_holds_a_stem", adjudicate.REGISTRY[Q.REST_IS_NOT_A_REST].reasons)


class TestTheNoiseGateOnTheRestsInkContact(unittest.TestCase):
    """Tile 10 (Litolff 16/1/2/2): the 2.150b margin 0.01 is inside the 0.05 re-read noise -- no veto; tile 4's 0.69 vetoes."""

    def test_the_gate(self):
        from tools.omr.staged.adjudicators import family_precision as FP

        def margin(thin, blob, head):
            return min(thin / FP.REST_STROKE_MIN_SP - 1.0, max(blob / FP.REST_HEAD_BLOB_MIN_SP - 1.0, head / FP.REST_HEAD_INK_MIN_SP2 - 1.0))
        self.assertLess(margin(1.01, 0.77, 1.611), SOA.REREAD_NOISE)
        self.assertGreaterEqual(margin(1.69, 1.25, 0.938), SOA.REREAD_NOISE)


class TestBoxSaysIsSilentWithTheFlagOff(unittest.TestCase):

    def test_silent(self):
        with mock.patch.dict(os.environ, {SO.ENV_SHAPE: "0"}):
            self.assertEqual(SOA.box_says(None, "glyph/0/0/0/0/0")[0], "silent")


if __name__ == "__main__":
    unittest.main()
