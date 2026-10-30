"""ROADMAP 2.205 (STAGED ADJUDICATE `adjudicate_stroke_owner` + pure `stroke_owner`), flag `OMR_STROKE_OWNER`, default ON since 2026-10-26: one owner per stroke,
the claimants first (area claims, heads, accidentals, arcs, letters, rests), the consumers (2.202 beams, 2.204 stems) reading only what no mark
owns. Constructed cells only. Every RED case has a twin that must NOT fire; `TestTheControlCanFail` breaks the claim order (and the consumer
mask) and shows the RED cases turn."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators            # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged import stroke_owner as SO
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.adjudicators import stroke_owner as SOA
from tools.omr.staged.record import Outcome, Q, READERS
from tools.omr.tests import test_staged_beams_from_strokes_2_202 as B2
from tools.omr.tests import test_staged_stems_from_strokes_2_204 as S4

SP = 100.0
OWNER = SO.ENV
BEAMS = rhythm.BEAMS_FROM_STROKES_ENV
STEMS = rhythm.STEMS_FROM_STROKES_ENV


def ink(o, kind, box, length, thick, area=None, touches=(), angle=0.0):
    w, h = box[2] / SP, box[3] / SP
    return SO.Ink(o, kind, tuple(float(v) for v in box), length, thick, (w * h * 0.8 if area is None else area), SP,
                  tuple((j, 1.0) for j in touches), "s%d" % o, angle)


def claim(key, cls, covers=(), partial=()):
    return SO.Claim(key, SO.family_of(cls), cls, tuple(covers), tuple(partial), "gs:" + key)


# ── the pure rule ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
class TestFamilies(unittest.TestCase):

    def test_the_detector_classes_fall_in_their_families_and_consumers_are_not_claimants(self):
        self.assertEqual([SO.family_of(c) for c in ("noteheadBlackOnLine", "keyFlat", "accidentalNatural", "slur", "dynamicF", "restQuarter",
                                                     "clefG", "timeSig4", "ledgerLine", "augmentationDot")],
                         ["head", "accidental", "accidental", "arc", "dynamic", "rest", "clef", "meter", "ledger", "dot"])
        self.assertIsNone(SO.family_of("staff"))
        for c in ("beam", "flag8thUp", "stem"):
            self.assertIn(SO.family_of(c), SO.CONSUMERS)
            self.assertIsNone(next((i for i, t in enumerate(SO.TIERS) if SO.family_of(c) in t), None))


class TestASharpsCrossbarNearAStemTip(unittest.TestCase):
    """2.202 tile 2 (Brahms p14): a 3.1-sp crossbar touching the sharp's two stems AND the note's stem read as a beam."""
    STEM = ink(0, "vertical", (400, 300, 30, 400), 4.0, 0.3, touches=(3,))
    LEFT = ink(1, "vertical", (250, 550, 15, 300), 3.0, 0.15, touches=(3,))
    RIGHT = ink(2, "vertical", (300, 530, 15, 300), 3.0, 0.15, touches=(3,))
    BAR = ink(3, "horizontal", (240, 620, 190, 52), 3.1, 0.52, touches=(0, 1, 2), angle=21.9)

    def test_the_crossbar_is_the_SHARPS_attached_by_the_two_stems_it_ties_RED(self):
        own = SO.own_strokes([self.STEM, self.LEFT, self.RIGHT, self.BAR],
                             [claim("acc", "accidentalSharp", covers=(1, 2), partial=((3, 0.3),))])
        self.assertEqual((own[3].state, own[3].family, own[3].by), ("decided", "accidental", "attach"))
        self.assertTrue(own[3].claimed)
        self.assertEqual(own[0].state, "unclaimed")          # the note's stem stays the consumers'
        self.assertNotIn(3, SO.unclaimed(own))

    def test_TWIN_without_the_sharp_the_same_stroke_is_unclaimed_and_the_beam_reader_may_read_it(self):
        own = SO.own_strokes([self.STEM, self.BAR], [])
        self.assertEqual(own[3].state, "unclaimed")

    def test_TWIN_a_stroke_touching_ONE_owned_stroke_is_not_attached(self):
        own = SO.own_strokes([self.STEM, self.LEFT, self.RIGHT, self.BAR],
                             [claim("acc", "accidentalSharp", covers=(1,), partial=((3, 0.3),))])
        self.assertEqual(own[3].state, "unclaimed")


class TestAStemTouchingBothHalvesOfASplitHead(unittest.TestCase):
    """A head on a line, cut in two by the staff-line erase: its stem touches both halves. Measured 2.205: 647 / 143 finder stems went to heads."""

    def test_the_stem_never_attaches_to_the_head_RED_TWIN_of_the_sharps_crossbar(self):
        top = ink(0, "blob", (500, 500, 130, 45), 1.3, 0.45)
        bottom = ink(1, "blob", (500, 555, 130, 45), 1.3, 0.45)
        stem = ink(2, "vertical", (600, 180, 30, 400), 4.0, 0.3, touches=(0, 1))
        own = SO.own_strokes([top, bottom, stem], [claim("h", "noteheadBlackOnLine", covers=(0, 1), partial=((2, 0.2),))])
        self.assertEqual(own[2].state, "unclaimed")
        self.assertEqual({own[0].family, own[1].family}, {"head"})


class TestAStemSharedByAChord(unittest.TestCase):
    """Sean 2026-10-26 (page-facts): a chord's stem runs THROUGH its notes and every head on it shares it; a second puts heads on BOTH sides;
    a long stem through stacked heads is a chord stem, never a barline. No head may claim the shared stem -- each must still see it."""
    STEM = ink(3, "vertical", (600, 150, 30, 750), 7.5, 0.3, touches=(0, 1, 2))
    CHORD = [ink(0, "blob", (480, 700, 130, 110), 1.3, 0.9, touches=(3,)), ink(1, "blob", (480, 500, 130, 110), 1.3, 0.9, touches=(3,)),
             ink(2, "blob", (480, 300, 130, 110), 1.3, 0.9, touches=(3,))]

    def heads(self):
        return [claim("h%d" % i, "noteheadBlackInSpace", covers=(i,), partial=((3, 0.16),)) for i in range(3)]

    def test_a_three_note_chord_no_head_owns_the_stem_and_each_owns_its_blob_RED(self):
        own = SO.own_strokes(self.CHORD + [self.STEM], self.heads())
        self.assertEqual(own[3].state, "unclaimed")
        self.assertIn(3, SO.unclaimed(own))
        for i in range(3):
            self.assertEqual(own[i].owners, ("h%d" % i,))
            self.assertEqual(SO.box_verdict(self.heads()[i], own, {s.ordinal: s for s in self.CHORD + [self.STEM]})["verdict"], "owns")

    def test_a_second_heads_on_both_sides_of_the_stem_neither_owns_it(self):
        left = ink(0, "blob", (470, 500, 130, 110), 1.3, 0.9, touches=(2,))
        right = ink(1, "blob", (630, 450, 130, 110), 1.3, 0.9, touches=(2,))
        stem = ink(2, "vertical", (600, 150, 30, 460), 4.6, 0.3, touches=(0, 1))
        cl = [claim("L", "noteheadBlackInSpace", covers=(0,), partial=((2, 0.25),)),
              claim("R", "noteheadBlackOnLine", covers=(1,), partial=((2, 0.25),))]
        own = SO.own_strokes([left, right, stem], cl)
        self.assertEqual(own[2].state, "unclaimed")
        self.assertEqual((own[0].owners, own[1].owners), (("L",), ("R",)))

    def test_TWIN_a_letter_box_on_the_chord_stem_cannot_take_it_either(self):
        own = SO.own_strokes(self.CHORD + [self.STEM], self.heads() + [claim("f", "dynamicF", covers=(3,))])
        self.assertNotEqual(own[3].family, "dynamic")
        self.assertIn(3, SO.unclaimed(own))

    def test_through_the_pipeline_every_head_of_the_chord_reads_the_stem_as_with_ownership_off(self):
        lower, upper = (500, 540, 130, 100), (500, 440, 130, 100)
        stem = S4.V(0, (600, 180, 30, 460), touches=[1, 2])
        blobs = [dict(i=1, kind="blob", box=lower, L=1.3, T=0.9, touches=[0], steps=None),
                 dict(i=2, kind="blob", box=upper, L=1.3, T=0.9, touches=[0], steps=None)]

        def extra(log):
            _claimant(log, 0, "noteheadBlackInSpace", lower, [1], [(0, 0.2)])
            _claimant(log, 1, "noteheadBlackInSpace", upper, [2], [(0, 0.2)])

        got = {}
        for owner in (False, True):
            log, gs = S4.build([stem] + blobs, finder=((600, 180, 30, 460),), heads=(lower, upper), extra=extra)
            with mock.patch.dict(os.environ, {STEMS: "1", OWNER: "1" if owner else "0"}):
                adjudicate.run(log)
            got[owner] = [S4.direction(log, g).value for g in gs]
        self.assertEqual(got[True], got[False])
        self.assertEqual(set(got[True]), {"up"})


class TestANoteheadFusedToItsLedger(unittest.TestCase):
    """2.202 tile 6 (Brahms p0): the head merged with its ledger is one 'horizontal' 1.9 x 0.8 sp piece the beam rule counted."""
    BLOB = ink(0, "horizontal", (200, 400, 190, 81), 1.9, 0.81)

    def test_the_head_owns_the_fused_piece_and_the_ledger_box_only_could_RED(self):
        own = SO.own_strokes([self.BLOB], [claim("h", "noteheadBlackOnLine", covers=(0,)), claim("l", "ledgerLine", covers=(0,))])
        self.assertEqual((own[0].state, own[0].family, own[0].by), ("decided", "head", "shape"))

    def test_TWIN_a_thin_rung_alone_is_the_ledgers_and_a_long_thick_beam_is_nobodys(self):
        rung = ink(0, "horizontal", (200, 400, 200, 15), 2.0, 0.15)
        own = SO.own_strokes([rung], [claim("h", "noteheadBlackOnLine", covers=(0,)), claim("l", "ledgerLine", covers=(0,))])
        self.assertEqual(own[0].family, "ledger")
        beam = ink(0, "horizontal", (200, 400, 500, 60), 5.0, 0.6)
        own = SO.own_strokes([beam], [claim("h", "noteheadBlackOnLine", covers=(0,)), claim("l", "ledgerLine", covers=(0,))])
        self.assertEqual(own[0].state, "refused_claims")          # neither shape fits: the beam is the consumers'
        self.assertIn(0, SO.unclaimed(own))


class TestASlurStartingAtAStem(unittest.TestCase):
    """2.202 tiles 8 / 12: the thin start of a slur at a stem tip read as a flag hook."""
    STEM = ink(0, "vertical", (244, 383, 31, 437), 4.37, 0.3, touches=(1,))
    START = ink(1, "curve", (251, 770, 106, 10), 1.06, 0.06, touches=(0,))

    def test_the_arc_owns_its_start_RED(self):
        own = SO.own_strokes([self.STEM, self.START], [claim("slur", "slur", covers=(1,))])
        self.assertEqual((own[1].state, own[1].family), ("decided", "arc"))
        self.assertEqual(own[0].state, "unclaimed")

    def test_TWIN_an_arc_box_never_owns_a_blob_it_passes_over_or_a_beam(self):
        head = ink(2, "blob", (300, 700, 130, 100), 1.3, 0.9)
        beam = ink(3, "horizontal", (250, 760, 360, 63), 3.6, 0.63)
        own = SO.own_strokes([head, beam], [claim("slur", "slur", covers=(2, 3))])
        self.assertEqual({own[2].state, own[3].state}, {"refused_claims"})


class TestAFlagBoxedAsALetter(unittest.TestCase):
    """2.205 milestone, Litolff p10 (Sean's 2.154 tile 7, an eighth): the flag hook on the note's stem lay in detector `dynamicF` boxes."""
    HEAD = ink(0, "blob", (500, 500, 120, 110), 1.2, 0.9)
    STEM = ink(1, "vertical", (500, 520, 25, 450), 4.5, 0.25, touches=(0, 2))
    HOOK = ink(2, "horizontal", (510, 900, 113, 19), 1.13, 0.19, touches=(1,))

    def test_a_letter_box_never_owns_ink_that_runs_into_a_note_RED(self):
        own = SO.own_strokes([self.HEAD, self.STEM, self.HOOK],
                             [claim("h", "noteheadBlackInSpace", covers=(0,)), claim("f", "dynamicF", covers=(2,))])
        self.assertEqual(own[2].state, "refused_claims")
        self.assertIn("letter_ink_runs_into_a_note", own[2].candidates[0]["why"])

    def test_TWIN_a_letter_standing_clear_of_the_notes_is_the_letters(self):
        free = ink(2, "horizontal", (900, 900, 113, 19), 1.13, 0.19)
        own = SO.own_strokes([self.HEAD, self.STEM, free], [claim("h", "noteheadBlackInSpace", covers=(0,)), claim("f", "dynamicF", covers=(2,))])
        self.assertEqual(own[2].family, "dynamic")

    def test_CONTROL_with_the_order_broken_letters_before_heads_the_letter_takes_the_flag(self):
        broken = (SO.TIERS[0], ("dynamic", "mark", "dot", "text"), ("head", "ledger"), ("accidental",), ("arc", "hairpin"), ("rest",))
        own = SO.own_strokes([self.HEAD, self.STEM, self.HOOK],
                             [claim("h", "noteheadBlackInSpace", covers=(0,)), claim("f", "dynamicF", covers=(2,))], tiers=broken)
        self.assertEqual(own[2].family, "dynamic")


class TestAContestedStroke(unittest.TestCase):
    """2.192's case: an eighth rest's bulb boxed both as an accidental and as a rest -- both shapes fit, the shape cannot settle it."""
    BULB = ink(0, "blob", (300, 400, 50, 60), 0.6, 0.3, area=0.25)

    def test_two_families_whose_shapes_both_fit_ABSTAIN_and_are_counted_RED(self):
        own = SO.own_strokes([self.BULB], [claim("a", "accidentalDoubleSharp", covers=(0,)), claim("r", "rest8th", covers=(0,))])
        self.assertEqual(own[0].state, "contested")
        self.assertIsNone(own[0].family)
        self.assertEqual([c["family"] for c in own[0].candidates], ["accidental", "rest"])     # claim order kept
        self.assertTrue(own[0].claimed)                    # no consumer may read it as a witness
        self.assertEqual(SO.census(own)["contested"], 1)

    def test_TWIN_one_claimant_decides(self):
        own = SO.own_strokes([self.BULB], [claim("r", "rest8th", covers=(0,))])
        self.assertEqual((own[0].state, own[0].family), ("decided", "rest"))

    def test_TWIN_two_boxes_of_ONE_family_are_merged_not_contested(self):
        own = SO.own_strokes([self.BULB], [claim("r1", "rest8th", covers=(0,)), claim("r2", "restQuarter", covers=(0,))])
        self.assertEqual((own[0].state, own[0].family, own[0].owners), ("merged", "rest", ("r1", "r2")))

    def test_the_cell_census_partitions_every_stroke(self):
        own = SO.own_strokes([self.BULB, ink(1, "blob", (900, 400, 50, 60), 0.6, 0.3)],
                             [claim("a", "accidentalSharp", covers=(0,)), claim("r", "rest8th", covers=(0,))])
        c = SO.census(own)
        self.assertEqual(sum(c[k] for k in SO.STATES if k in c), 2)


class TestTheOldPairRulesAsOwnership(unittest.TestCase):
    """Plan section 3: the rest / head pair rules re-asked as "who owns this stroke"."""
    HEAD_BLOB = ink(0, "blob", (500, 500, 130, 100), 1.3, 0.9)
    STEM = ink(1, "vertical", (600, 180, 30, 330), 3.3, 0.3, touches=(0,))

    def test_rest_stroke_into_a_head_the_rest_owns_nothing_RED(self):
        own = SO.own_strokes([self.HEAD_BLOB, self.STEM], [claim("h", "noteheadBlackInSpace", covers=(0,)), claim("r", "restQuarter", covers=(1,))])
        self.assertEqual(own[1].state, "refused_claims")
        self.assertIn("rest_ink_runs_into_a_head", own[1].candidates[0]["why"])
        bv = SO.box_verdict(claim("r", "restQuarter", covers=(1,)), own, {0: self.HEAD_BLOB, 1: self.STEM})
        self.assertEqual(bv["verdict"], "refused")

    def test_TWIN_a_quarter_rests_own_stroke_touching_no_head_is_the_rests(self):
        own = SO.own_strokes([self.STEM], [claim("r", "restQuarter", covers=(0,) if False else (1,))])
        self.assertEqual((own[1].state, own[1].family), ("decided", "rest"))

    def test_rest_has_a_stem_a_block_rest_never_owns_a_vertical(self):
        own = SO.own_strokes([self.STEM], [claim("r", "restWhole", covers=(1,))])
        self.assertEqual(own[1].state, "refused_claims")

    def test_a_block_rest_box_on_a_heads_blob_owns_nothing_and_the_head_keeps_it(self):
        blob = ink(0, "blob", (500, 500, 130, 125), 1.3, 0.85)      # the measured median filled-head blob (1.24-1.32 sp tall, 2.205)
        own = SO.own_strokes([blob], [claim("h", "noteheadBlackInSpace", covers=(0,)), claim("r", "restWhole", covers=(0,))])
        self.assertEqual(own[0].family, "head")
        self.assertEqual(SO.box_verdict(claim("r", "restWhole", covers=(0,)), own, {0: blob})["verdict"], "refused")
        self.assertEqual(SO.box_verdict(claim("h", "noteheadBlackInSpace", covers=(0,)), own, {0: blob})["verdict"], "owns")

    def test_a_head_at_the_block_rests_height_is_CONTESTED_not_picked(self):
        # 1.0 sp: inside both shapes' measured ranges -- the shape cannot settle it, so it abstains (rule 8)
        own = SO.own_strokes([self.HEAD_BLOB], [claim("h", "noteheadBlackInSpace", covers=(0,)), claim("r", "restWhole", covers=(0,))])
        self.assertEqual(own[0].state, "contested")

    def test_TWIN_a_real_whole_rest_block_is_the_rests(self):
        block = ink(0, "blob", (500, 500, 140, 76), 1.4, 0.75)
        with mock.patch.dict(os.environ, {"OMR_WHOLE_REST_HANGS": "0"}):       # the flag is default ON since 2026-10-29 (own family `whole_rest`)
            own = SO.own_strokes([block], [claim("r", "restWhole", covers=(0,))])
        self.assertEqual(own[0].family, "rest")
        own = SO.own_strokes([block], [claim("r", "restWhole", covers=(0,))])
        self.assertEqual(own[0].family, "whole_rest")

    def test_rest_is_a_barline_a_rest_never_owns_a_stroke_longer_than_any_rest(self):
        bar = ink(0, "vertical", (0, 100, 20, 420), 4.2, 0.2)
        own = SO.own_strokes([bar], [claim("r", "restQuarter", covers=(0,))])
        self.assertEqual(own[0].state, "refused_claims")

    def test_tremolo_slash_a_thick_diagonal_across_a_stem_is_never_a_heads(self):
        stem = ink(0, "vertical", (600, 100, 30, 400), 4.0, 0.3, touches=(1,))
        slash = ink(1, "horizontal", (540, 250, 150, 70), 1.5, 0.45, touches=(0,), angle=25.0)
        own = SO.own_strokes([stem, slash], [claim("h", "noteheadBlackInSpace", covers=(1,))])
        self.assertEqual(own[1].state, "refused_claims")
        self.assertIn("tremolo_slash", own[1].candidates[0]["why"])

    def test_TWIN_a_head_beside_its_stem_is_not_a_slash(self):
        own = SO.own_strokes([self.HEAD_BLOB, self.STEM], [claim("h", "noteheadBlackInSpace", covers=(0,))])
        self.assertEqual(own[0].family, "head")

    def test_a_heads_own_stem_beside_it_is_no_evidence_against_the_head(self):
        own = SO.own_strokes([self.HEAD_BLOB, self.STEM], [claim("h", "noteheadBlackInSpace", covers=(1,))])
        self.assertEqual(SO.box_verdict(claim("h", "noteheadBlackInSpace", covers=(1,)), own, {0: self.HEAD_BLOB, 1: self.STEM})["verdict"],
                         "no_ink")

    def test_an_area_claim_owns_what_stands_in_it_whatever_box_also_covers_it(self):
        own = SO.own_strokes([self.HEAD_BLOB], [claim("h", "noteheadBlackInSpace", covers=(0,)),
                                                SO.Claim("ks", "key_signature", "key_signature", (0,), (), "ca:1", area=True)])
        self.assertEqual((own[0].family, own[0].by), ("key_signature", "area"))


# ── through the pipeline ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _claimant(log, gi, cls, box, covers, partial=()):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.GLYPH_BOX, (cls,) + tuple(box), reader=READERS.DETECTOR, frame="cell:0", score=0.7)
    log.observe(g, Q.GLYPH_STROKES, list(covers), reader=READERS.CV_GLYPH_STROKES, frame="cell:0", shares=[1.0] * len(covers),
                cover_min=0.5, partial=[list(p) for p in partial])
    return g


def _beam_dur(owner, strokes, claimants=(), **kw):
    def extra(log):
        for gi, cls, box, cov, part in claimants:
            _claimant(log, gi, cls, box, cov, part)
    log, g = B2.build(strokes, extra=extra, **kw)
    with mock.patch.dict(os.environ, {BEAMS: "1", OWNER: "1" if owner else "0"}):
        adjudicate.run(log)
    return log, log.verdict(Q.DURATION, g)


class TestOffIsByteIdentical(unittest.TestCase):

    def test_flag_OFF_no_stroke_owner_verdict_is_filed_and_the_duration_is_the_same(self):
        log0, v0 = _beam_dur(False, B2.PAIR, boxes=[(B2.BEAM, [2])])
        self.assertEqual([v for v in log0.all_verdicts() if v.quantity == Q.STROKE_OWNER], [])
        with mock.patch.dict(os.environ, {BEAMS: "1"}):
            log1, g1 = B2.build(B2.PAIR, boxes=[(B2.BEAM, [2])])
            os.environ[OWNER] = "0"
            adjudicate.run(log1)
        v1 = log1.verdict(Q.DURATION, g1)
        for f in ("outcome", "value", "reason", "detail", "candidates"):
            self.assertEqual(getattr(v0, f), getattr(v1, f), f)

    def test_default_on_and_explicit_off(self):
        old = os.environ.pop(OWNER, None)
        try:
            self.assertTrue(SOA.enabled())
        finally:
            if old is not None:
                os.environ[OWNER] = old
        for val, want in (("1", True), ("on", True), ("", True), ("0", False), ("false", False), ("no", False), ("off", False)):
            with mock.patch.dict(os.environ, {OWNER: val}):
                self.assertEqual(SOA.enabled(), want, val)


class TestTheBeamReaderReadsOnlyUnclaimedStrokes(unittest.TestCase):
    """2.202's rule unchanged; the strokes another mark owns are masked before it reads them."""

    def sharp_at_the_tip(self):
        # head 0's down stem (ordinal 0) with a sharp's two stems (1, 2) and its crossbar (3) touching all three, 0.6 sp above the tip
        s = [dict(B2.stem_stroke(0), touches=[3]),
             B2.S("vertical", (150, 650, 15, 250), 2.5, 0.15, [3], sag=0.0, angle=90.0),
             B2.S("vertical", (200, 640, 15, 250), 2.5, 0.15, [3], sag=0.0, angle=90.0),
             B2.S("horizontal", (140, 760, 135, 52), 1.35, 0.52, [0, 1, 2], angle=20.0)]
        return s, [(40, "accidentalSharp", (140, 640, 80, 260), [1, 2], [(3, 0.4)])]

    def test_OWNER_off_the_sharps_crossbar_is_counted_as_a_beam_level_at_the_tip(self):
        s, c = self.sharp_at_the_tip()
        _log, v = _beam_dur(False, s, c, heads=(0,))
        self.assertIn(3, v.detail["beams_from_strokes"]["tip"]["beams"])

    def test_OWNER_on_the_crossbar_is_the_sharps_and_no_beam_RED(self):
        s, c = self.sharp_at_the_tip()
        log, v = _beam_dur(True, s, c, heads=(0,))
        self.assertEqual(v.detail["beams_from_strokes"]["tip"]["beams"], [])
        so = log.verdict(Q.STROKE_OWNER, R.cell(0, 0, 0, 0))
        self.assertIn(3, so.value["owned"])
        self.assertEqual(so.detail["strokes"]["3"][1], "accidental")

    def test_OWNER_on_a_slur_start_at_the_tip_is_never_a_flag_RED_and_a_real_flag_still_is_TWIN(self):
        two = B2.TestAFlagBoxedAsABeam.TWO
        _l, real = _beam_dur(True, two, boxes=[((251, 690, 110, 110), [1, 2])], heads=(0,))
        self.assertEqual(real.detail["beam_evidence"], "flag")                      # nothing claims the hooks: a flag, as 2.202
        slur = [dict(two[0]), dict(two[1], kind="curve", T=0.06), dict(two[2])]
        _l, off = _beam_dur(False, slur, boxes=[((251, 690, 110, 110), [1, 2])], heads=(0,),
                            claimants=[(41, "slur", (251, 760, 400, 40), [1], ())])
        _l, on = _beam_dur(True, slur, boxes=[((251, 690, 110, 110), [1, 2])], heads=(0,),
                           claimants=[(41, "slur", (251, 760, 400, 40), [1], ())])
        self.assertEqual(off.detail["flag_levels"], 2)                              # today: the slur's start is counted as a hook
        self.assertNotEqual(on.detail.get("flag_levels"), 2)

    def test_TWIN_a_real_beamed_pair_is_unclaimed_and_reads_as_today(self):
        _l, off = _beam_dur(False, B2.PAIR, boxes=[(B2.BEAM, [2])])
        _l, on = _beam_dur(True, B2.PAIR, boxes=[(B2.BEAM, [2])])
        self.assertEqual((on.outcome, on.value, on.detail["beams_from_strokes"]["settled"]),
                         (off.outcome, off.value, off.detail["beams_from_strokes"]["settled"]))

    def test_a_contested_stroke_is_no_beam_witness_either_way(self):
        # the beam stroke is covered by a dynamic's box AND a rest box whose shapes both only "could": contested, masked -> the box narrows
        s = [dict(B2.stem_stroke(0), touches=[2]), dict(B2.stem_stroke(1), touches=[2]), B2.beam_stroke([0, 1], box=(251, 757, 150, 63))]
        s[2]["L"] = 1.5
        c = [(42, "dynamicF", (251, 740, 150, 90), [2], ()), (43, "restQuarter", (251, 740, 150, 90), [2], ())]
        log, v = _beam_dur(True, s, c, boxes=[((251, 757, 150, 63), [2])])
        so = log.verdict(Q.STROKE_OWNER, R.cell(0, 0, 0, 0))
        self.assertEqual(so.value["contested"], [2])
        self.assertEqual(so.reason, "some_strokes_contested")
        self.assertEqual(v.outcome, Outcome.NARROWED)


class TestTheStemReaderReadsOnlyUnclaimedStrokes(unittest.TestCase):
    """2.204's rule unchanged. `refuse_owned`'s case: a false rest box standing on a real stem."""

    def go(self, owner, stem_len, *, tiers=None):
        stem = S4.V(0, (600, 180, 30, int(stem_len * SP)) if stem_len != 4.0 else S4.UP, touches=[1])
        blob = dict(i=1, kind="blob", box=(500, 500, 130, 100), L=1.3, T=0.9, touches=[0], steps=None)

        def extra(log):
            _claimant(log, 0, "noteheadBlackInSpace", S4.HEAD, [1])            # the head's box (glyph 0) stands on its blob
            _claimant(log, 44, "restQuarter", (590, 180, 50, int(stem_len * SP)), [0])

        log, gs = S4.build([stem, blob], extra=extra)
        env = {STEMS: "1", OWNER: "1" if owner else "0"}
        with mock.patch.dict(os.environ, env):
            if tiers is not None:
                with mock.patch.object(SO, "TIERS", tiers):
                    adjudicate.run(log)
            else:
                adjudicate.run(log)
        return log, gs

    def test_OWNER_on_a_rest_box_on_a_stem_that_runs_into_a_head_leaves_the_stem_to_the_stem_reader_RED(self):
        log, gs = self.go(True, 3.6)
        v = S4.direction(log, gs[0])
        self.assertEqual(v.value, "up")
        so = log.verdict(Q.STROKE_OWNER, R.cell(0, 0, 0, 0))
        self.assertNotIn(0, so.value["owned"])
        self.assertEqual(so.detail["boxes"][R.glyph(0, 0, 0, 0, 44).to_key()][0], "refused")

    def test_TWIN_the_head_box_owns_its_blob_and_the_stem_is_never_the_heads(self):
        log, gs = self.go(True, 3.6)
        so = log.verdict(Q.STROKE_OWNER, R.cell(0, 0, 0, 0))
        self.assertEqual(so.detail["strokes"]["1"][1], "head")


class TestTheControlCanFail(unittest.TestCase):
    """CLAUDE rule 7. Break the claim order (rests before heads) and the stem the rest box stands on is the rest's; turn the consumer mask off
    and the sharp's crossbar is a beam again."""

    def test_with_the_order_broken_the_rest_takes_the_stem_and_the_stem_reader_loses_it(self):
        broken = (SO.TIERS[0], ("rest",), ("head", "ledger"), ("accidental",), ("arc", "hairpin"), ("dynamic", "mark", "dot", "text"))
        ok_log, ok_gs = TestTheStemReaderReadsOnlyUnclaimedStrokes().go(True, 3.6)
        bad_log, bad_gs = TestTheStemReaderReadsOnlyUnclaimedStrokes().go(True, 3.6, tiers=broken)
        self.assertNotIn(0, ok_log.verdict(Q.STROKE_OWNER, R.cell(0, 0, 0, 0)).value["owned"])
        self.assertIn(0, bad_log.verdict(Q.STROKE_OWNER, R.cell(0, 0, 0, 0)).value["owned"])
        self.assertEqual(S4.direction(ok_log, ok_gs[0]).value, "up")
        self.assertNotEqual(S4.direction(bad_log, bad_gs[0]).value, "up")

    def test_with_the_consumer_mask_off_the_crossbar_is_a_beam_level_again(self):
        t = TestTheBeamReaderReadsOnlyUnclaimedStrokes()
        s, c = t.sharp_at_the_tip()
        with mock.patch.object(rhythm, "_owner_mask", lambda verdict: {}):
            _l, v = _beam_dur(True, s, c, heads=(0,))
        self.assertIn(3, v.detail["beams_from_strokes"]["tip"]["beams"])


class TestExportTally(unittest.TestCase):

    def test_the_report_partitions_every_stroke_and_is_absent_with_the_flag_off(self):
        from tools.omr.staged import export as E
        s, c = TestTheBeamReaderReadsOnlyUnclaimedStrokes().sharp_at_the_tip()
        for owner in (False, True):
            log, _v = _beam_dur(owner, s, c, heads=(0,))
            rec = E.Record({"record": log.to_json()})
            got = E._stroke_owner_census(rec)
            if not owner:
                self.assertEqual(got, {})
                continue
            so = got["stroke_ownership"]
            self.assertEqual(so["strokes"], 4)
            self.assertEqual(so["unaccounted"], 0)
            self.assertEqual(so["owned_by_family"], {"accidental": 3})


if __name__ == "__main__":
    unittest.main()
