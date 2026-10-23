"""ROADMAP 2.186 -- ONE INK, ONE MARK (flag `OMR_ONE_INK_ONE_MARK`, default OFF). STAGED GATHER merge + ADJUDICATE + EXPORT.

CONVENTION ASSUMED: of two classes of one family the detector boxed on one ink (IoU >= 0.5), the more confident is right more often than
not (Sean's 2.182a tiles: 6 of 7 real rest pairs), and the ink belongs to the staff `glyph_owner` names. WHAT WOULD FALSIFY IT: blind tiles
where the stronger class is wrong on most. NOT CONFIRMED by Sean for this lane: every merged box is written GUESSED (blue).
Every keep/refuse test has a control in the same class that can fail.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import export as SX
from tools.omr.staged import one_ink as OI
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS
from tools.omr.template_matcher import SymbolDetection
from tools.omr.tests.test_staged_family_refusals import _page_box_at_step, _staff_geometry
from tools.omr.tests.test_staged_rest_placement_2_33 import _run
from tools.omr.tests import test_staged_accidental as TA

ENV = "OMR_ONE_INK_ONE_MARK"


def B(cls, x, y, w, h, c):
    return (cls, x, y, w, h, c)


class TestPlan(unittest.TestCase):

    def test_two_rest_classes_on_one_ink_merge_to_the_stronger(self):
        p = OI.plan([B("rest16th", 100, 100, 50, 80, 0.44), B("rest8th", 101, 100, 50, 80, 0.35)])
        self.assertEqual(list(p), [0])
        self.assertEqual(p[0]["absorbed"], [1])
        self.assertEqual(p[0]["rivals"], [{"class": "rest8th", "conf": 0.35}])
        self.assertAlmostEqual(p[0]["margin"], 0.09, places=3)

    def test_whatever_the_order_the_higher_confidence_wins(self):
        p = OI.plan([B("rest8th", 100, 100, 50, 80, 0.30), B("restQuarter", 100, 100, 50, 80, 0.66)])
        self.assertEqual(list(p), [1])

    def test_CONTROL_same_class_is_not_merged(self):
        self.assertEqual(OI.plan([B("rest8th", 100, 100, 50, 80, 0.5), B("rest8th", 102, 100, 50, 80, 0.4)]), {})

    def test_CONTROL_below_the_iou_floor_is_two_marks(self):
        self.assertEqual(OI.plan([B("rest8th", 100, 100, 50, 80, 0.5), B("rest16th", 140, 100, 50, 80, 0.4)]), {})

    def test_never_across_families(self):
        for other in ("noteheadBlackOnLine", "accidentalSharp", "augmentationDot", "flag8thUp"):
            self.assertEqual(OI.plan([B("rest8th", 100, 100, 50, 80, 0.5), B(other, 100, 100, 50, 80, 0.4)]), {}, other)
        self.assertEqual(OI.plan([B("accidentalSharp", 100, 100, 50, 80, 0.5), B("noteheadBlackOnLine", 100, 100, 50, 80, 0.4)]), {})

    def test_accidentals_merge_but_key_signature_classes_and_flags_do_not(self):
        self.assertEqual(list(OI.plan([B("accidentalFlat", 0, 0, 20, 40, 0.6), B("accidentalNatural", 1, 0, 20, 40, 0.5)])), [0])
        self.assertEqual(OI.plan([B("keyFlat", 0, 0, 20, 40, 0.6), B("keyNatural", 1, 0, 20, 40, 0.5)]), {})
        self.assertEqual(OI.plan([B("keyFlat", 0, 0, 20, 40, 0.6), B("accidentalFlat", 1, 0, 20, 40, 0.5)]), {})
        self.assertEqual(OI.plan([B("flag8thUp", 0, 0, 20, 40, 0.6), B("flag16thUp", 1, 0, 20, 40, 0.5)]), {})

    def test_no_chaining_A_B_C(self):
        # A~B and B~C overlap, A and C do not: C is not dragged into A's mark.
        p = OI.plan([B("rest8th", 0, 0, 100, 10, 0.9), B("rest16th", 25, 0, 100, 10, 0.8), B("restQuarter", 50, 0, 100, 10, 0.7)])
        absorbed = {j for info in p.values() for j in info["absorbed"]}
        self.assertEqual(p[0]["absorbed"], [1])
        self.assertNotIn(2, absorbed)

    def test_a_tie_goes_to_the_earlier_box(self):
        self.assertEqual(list(OI.plan([B("rest8th", 0, 0, 50, 50, 0.5), B("rest16th", 0, 0, 50, 50, 0.5)])), [0])


def _det(cls, x, c, w=50):
    return SymbolDetection(cell=None, smufl_name=cls, category=("rest" if cls.startswith("rest") else "accidental"), x_canonical=x,
                           y_canonical=100, width_canonical=w, height_canonical=80, confidence=c)


class TestMergeLive(unittest.TestCase):

    def test_merge_keeps_every_index_marks_the_absorbed_and_carries_the_rivals(self):
        dets = [_det("rest16th", 100, 0.44), _det("rest8th", 101, 0.35), _det("restQuarter", 400, 0.5)]
        out = OI.merge(dets)
        self.assertEqual([d.smufl_name for d in out], ["rest16th", "rest8th", "restQuarter"])   # same length, same order: ids stable
        self.assertEqual(out[0].one_ink_rivals, (("rest8th", 0.35),))
        self.assertEqual(out[1].one_ink_absorbed_by, 0)
        self.assertIsNone(out[2].one_ink_rivals)
        self.assertIsNone(out[2].one_ink_absorbed_by)
        d = OI.box_detail(out[0])["one_ink"]
        self.assertEqual(d["winner"], {"class": "rest16th", "conf": 0.44})
        self.assertEqual(OI.box_detail(out[1]), {"one_ink_absorbed_by_index": 0})

    def test_CONTROL_nothing_to_merge_returns_the_boxes_untouched(self):
        dets = [_det("rest16th", 100, 0.44), _det("rest16th", 400, 0.35)]
        self.assertEqual(OI.merge(dets), dets)

    def test_the_flag_defaults_ON(self):
        # ROADMAP 2.186 landed ON (Sean 2026-10-22): unset is ON, an explicit 0/false/no/off disables.
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ENV, None)
            self.assertTrue(OI.enabled())
        for v in ("1", "true", "on"):
            with mock.patch.dict(os.environ, {ENV: v}):
                self.assertTrue(OI.enabled())
        for v in ("0", "false", "no", "off"):
            with mock.patch.dict(os.environ, {ENV: v}):
                self.assertFalse(OI.enabled())

    def test_no_margin_reads_until_the_bar_is_set(self):
        self.assertFalse(OI.reads(0.99))
        with mock.patch.object(OI, "ONE_INK_READ_MARGIN", 0.2):
            self.assertTrue(OI.reads(0.25))
            self.assertFalse(OI.reads(0.1))
            self.assertFalse(OI.reads(None))


def _rest(log, gi, cls, score, one_ink=None, *, x_c=200.0, w_c=100.0, h_c=300.0, page_w=20.0):
    g = R.glyph(0, 0, 0, 0, gi)
    extra = {"one_ink": one_ink} if one_ink else {}
    log.observe(g, Q.GLYPH_BOX, (cls, x_c, 100.0, w_c, h_c), reader=READERS.DETECTOR, frame="cell:0", score=score,
                category="rest", bbox_page_px=list(_page_box_at_step(4.0, x0=500.0, x1=500.0 + page_w, thickness=60.0)), **extra)
    log.observe(g, Q.REST, cls, reader=READERS.DETECTOR, frame="cell:0", score=score, category="rest")
    return g


MERGED = {"rivals": [{"class": "rest16th", "conf": 0.37}], "margin": 0.06, "winner": {"class": "rest8th", "conf": 0.43}, "iou_min": 0.5}


def _decide_pair_rest(flag=True):
    """The winner (rest8th .43, merged) and the box it absorbed (rest16th .37, kept at its own index) in ONE cell."""
    log = Log()
    _staff_geometry(log)
    w = _rest(log, 0, "rest8th", 0.43, MERGED)
    g = R.glyph(0, 0, 0, 0, 1)
    log.observe(g, Q.GLYPH_BOX, ("rest16th", 201.0, 100.0, 100.0, 300.0), reader=READERS.DETECTOR, frame="cell:0", score=0.37, category="rest",
                bbox_page_px=list(_page_box_at_step(4.0, x0=500.0, x1=520.0, thickness=60.0)), one_ink_absorbed_by=w.to_key())
    log.observe(g, Q.REST, "rest16th", reader=READERS.DETECTOR, frame="cell:0", score=0.37, category="rest")
    with mock.patch.dict(os.environ, {ENV: "1" if flag else "0"}, clear=False):
        _run(log, Q.REST_IS_NOT_A_REST)
    return log, w, g


def _decide_rest(one_ink, flag=True, cls="rest8th", w_c=100.0, extra_env=None):
    log = Log()
    _staff_geometry(log)
    g = _rest(log, 0, cls, 0.43, one_ink, w_c=w_c)
    env = dict(extra_env or {})
    env[ENV] = "1" if flag else "0"
    with mock.patch.dict(os.environ, env, clear=False):
        _run(log, Q.REST_IS_NOT_A_REST)
    return log, g


class TestRestNarrowing(unittest.TestCase):

    def test_a_merged_rest_no_rule_refused_is_narrowed_rest_first(self):
        log, g = _decide_rest(MERGED)
        v = log.verdict(Q.REST_IS_NOT_A_REST, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "one_ink_merged")
        self.assertAlmostEqual(v.margin, 0.06, places=3)
        self.assertIs(v.candidates[0].value, False)

    def test_CONTROL_an_unmerged_rest_is_decided_a_rest(self):
        log, g = _decide_rest(None)
        v = log.verdict(Q.REST_IS_NOT_A_REST, g)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")

    def test_a_merged_box_a_later_rule_refuses_stays_refused_with_its_own_reason(self):
        """Sean's tiles 2 and 9 (a stem tip, a barline+ff): the surviving box still goes through every refusal."""
        log, g = _decide_rest(MERGED, cls="restQuarter", w_c=45.0, extra_env={"OMR_REST_WIDTH_FLOOR": "1"})
        v = log.verdict(Q.REST_IS_NOT_A_REST, g)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "rest_narrower_than_its_class")

    def test_the_absorbed_box_is_refused_a_duplicate_and_the_winner_is_not_refused_with_it(self):
        log, w, g = _decide_pair_rest()
        vw, vg = log.verdict(Q.REST_IS_NOT_A_REST, w), log.verdict(Q.REST_IS_NOT_A_REST, g)
        self.assertEqual(vw.outcome, Outcome.NARROWED)
        self.assertEqual(vw.reason, "one_ink_merged")
        self.assertIs(vg.value, True)
        self.assertEqual(vg.reason, "rest_is_a_duplicate_box")
        self.assertTrue(vg.detail["one_ink_absorbed"])

    def test_CONTROL_off_the_same_pair_is_still_refused_both(self):
        log, w, g = _decide_pair_rest(flag=False)
        for x in (w, g):
            v = log.verdict(Q.REST_IS_NOT_A_REST, x)
            self.assertIs(v.value, True)
            self.assertEqual(v.reason, "rest_is_a_duplicate_box")

    def test_the_read_bar_when_cleared_leaves_a_plain_decided_rest(self):
        with mock.patch.object(OI, "ONE_INK_READ_MARGIN", 0.05):
            log, g = _decide_rest(MERGED)
        v = log.verdict(Q.REST_IS_NOT_A_REST, g)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")

    def test_the_export_guess_carries_both_classes_chosen_first(self):
        log, g = _decide_rest(MERGED)
        rec = SX.Record({"record": {"observations": [], "abstentions": [], "verdicts": log.to_json()["verdicts"]}})
        gs = SX.one_ink_guess_of(rec, "glyph/0/0/0/0/0")
        self.assertEqual(gs["rule"], "one_ink_merged")
        self.assertEqual([c["value"] for c in gs["candidates"]], ["rest8th", "rest16th"])
        self.assertEqual(gs["chosen"], {"value": "rest8th"})

    def test_CONTROL_an_unmerged_rest_has_no_guess(self):
        log, g = _decide_rest(None)
        rec = SX.Record({"record": {"observations": [], "abstentions": [], "verdicts": log.to_json()["verdicts"]}})
        self.assertIsNone(SX.one_ink_guess_of(rec, "glyph/0/0/0/0/0"))


def _owner_verdict(log, subject, value, outcome=R.Outcome.DECIDED, reason="distance"):
    return log.record(R.Verdict(id=log._next_id("vrd"), subject=subject, quantity=Q.GLYPH_OWNER, outcome=outcome,
                                value=value if outcome is R.Outcome.DECIDED else None,
                                decider="t", reason=reason))


def _acc_case(owner=None, outcome=R.Outcome.DECIDED, flag=True):
    log = Log()
    TA._cell_unit(log)
    acc = TA._acc(log, 0, 100.0, 4.0)
    head = TA._head(log, 1, 106.0, 4.0)
    if owner is not None:
        _owner_verdict(log, acc, owner, outcome)
    with mock.patch.dict(os.environ, {ENV: "1" if flag else "0"}):
        TA._decide(log)
    return log, acc, head


class TestOwnershipFirstForAccidentals(unittest.TestCase):

    def test_CONTROL_off_the_wrong_cells_copy_still_pairs_with_a_head(self):
        log, acc, head = _acc_case("staff/0/0/1", flag=False)
        self.assertEqual(log.verdict(Q.ACCIDENTAL_OWNER, acc).value, head.to_key())

    def test_on_the_copy_the_contest_gave_to_another_staff_owns_no_head(self):
        log, acc, head = _acc_case("staff/0/0/1")
        v = log.verdict(Q.ACCIDENTAL_OWNER, acc)
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "owned_by_another_staff")

    def test_on_its_own_staff_owns_as_before(self):
        log, acc, head = _acc_case("staff/0/0/0")
        self.assertEqual(log.verdict(Q.ACCIDENTAL_OWNER, acc).value, head.to_key())

    def test_on_an_undecided_contest_abstains_and_is_counted_by_name(self):
        log, acc, head = _acc_case("staff/0/0/0", outcome=R.Outcome.ABSTAINED)
        v = log.verdict(Q.ACCIDENTAL_OWNER, acc)
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "ownership_undecided")

    def test_CONTROL_on_an_uncontested_glyph_has_no_owner_verdict_and_passes(self):
        log, acc, head = _acc_case(None)
        self.assertEqual(log.verdict(Q.ACCIDENTAL_OWNER, acc).value, head.to_key())

    def test_an_absorbed_accidental_owns_no_head_and_is_counted_by_name(self):
        log = Log()
        TA._cell_unit(log)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.GLYPH_BOX, ("accidentalNatural", 88.0, 4 * TA.HALF - TA.SPACE, 12.0, TA.SPACE * 2), reader=READERS.DETECTOR,
                    frame="cell:0", score=0.6, category="accidental", one_ink_absorbed_by="glyph/0/0/0/0/2")
        log.observe(g, Q.ACCIDENTAL_STAFF_POSITION, 4.0, reader=READERS.GEOMETRY, frame="cell:0", alteration="n", detector_class="accidentalNatural",
                    anchor_fraction=0.5, box_centre_position=4.0, residual=0.0, rounded=4, x0=88.0, x1=100.0, y0=4 * TA.HALF - TA.SPACE,
                    y1=4 * TA.HALF + TA.SPACE, confidence=0.6, one_ink_absorbed=True)
        TA._head(log, 1, 106.0, 4.0)
        with mock.patch.dict(os.environ, {ENV: "1"}):
            TA._decide(log)
        v = log.verdict(Q.ACCIDENTAL_OWNER, g)
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "one_ink_absorbed")

    def test_a_merged_glyph_carries_its_classes_on_the_owner_verdict(self):
        log = Log()
        TA._cell_unit(log)
        acc = TA._acc(log, 0, 100.0, 4.0)
        head = TA._head(log, 1, 106.0, 4.0)
        # re-file the position row with the merge detail (what GATHER does)
        log2 = Log()
        TA._cell_unit(log2)
        g = R.glyph(0, 0, 0, 0, 0)
        log2.observe(g, Q.GLYPH_BOX, ("accidentalFlat", 88.0, 4 * TA.HALF - TA.SPACE, 12.0, TA.SPACE * 2), reader=READERS.DETECTOR,
                     frame="cell:0", score=0.8, category="accidental")
        log2.observe(g, Q.ACCIDENTAL_STAFF_POSITION, 4.0, reader=READERS.GEOMETRY, frame="cell:0", alteration="b",
                     detector_class="accidentalFlat", anchor_fraction=0.5, box_centre_position=4.0, residual=0.0, rounded=4,
                     x0=88.0, x1=100.0, y0=4 * TA.HALF - TA.SPACE, y1=4 * TA.HALF + TA.SPACE, confidence=0.8,
                     one_ink={"rivals": [{"class": "accidentalNatural", "conf": 0.6}], "margin": 0.2,
                              "winner": {"class": "accidentalFlat", "conf": 0.8}, "iou_min": 0.5})
        TA._head(log2, 1, 106.0, 4.0)
        with mock.patch.dict(os.environ, {ENV: "1"}):
            TA._decide(log2)
        v = log2.verdict(Q.ACCIDENTAL_OWNER, g)
        self.assertEqual(v.detail["one_ink"]["rivals"][0]["class"], "accidentalNatural")


if __name__ == "__main__":
    unittest.main()
