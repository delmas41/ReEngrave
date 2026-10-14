"""ROADMAP 2.127 -- a dot SEEN beside a decided-plain note must not leave the
note written plain and unmarked (`OMR_AUG_DOT_JOIN`, default OFF).

Every number is a real case from Brahms `overnight-20261013-night`
(`benchmarks/omr-aug-dots-2026-10/FINDINGS.md`): page boxes in 600 dpi page
pixels, the cell staff space in canonical pixels, the head's live duration as
the record held it. RED first: each rule is shown firing with the flag on, and
silent with it off; every refusal has its positive control.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import aug_dot_join as J
from tools.omr.staged.record import Log, Outcome, Q, READERS

ON = {"OMR_AUG_DOT_JOIN": "1"}
QUARTER = {"beats": 1.0, "written": 1.0, "dots": 0, "beam_levels": 0}
HALF = {"beats": 2.0, "written": 2.0, "dots": 0, "beam_levels": 0}
EIGHTH = {"beats": 0.5, "written": 0.5, "dots": 0, "beam_levels": 1}


def _log(space=100.0, cells=((0, 0, 4, 1),)):
    log = Log()
    for c in cells:
        log.observe(R.cell(*c), Q.CELL_STAFF_SPACE, float(space),
                    reader=READERS.GEOMETRY, frame="cell:0")
    return log


def _glyph(log, key, cls, canon, page):
    g = R.Subject.from_key(key)
    log.observe(g, Q.GLYPH_BOX, (cls,) + tuple(canon),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                bbox_page_px=list(page))
    return g


def _head(log, key, canon, page, value, cls="noteheadBlackOnLine"):
    g = _glyph(log, key, cls, canon, page)
    log.record(R.Verdict(
        id=log._next_id("vrd"), subject=g, quantity=Q.DURATION,
        outcome=Outcome.DECIDED, value=dict(value),
        decider="adjudicate_duration", reason="head_and_marks"))
    return g


def _dot(log, key, canon, page, role, head=None, reason=None):
    d = _glyph(log, key, "augmentationDot", canon, page)
    log.observe(d, Q.AUG_DOT, (canon[0] + canon[2] / 2.0,
                                canon[1] + canon[3] / 2.0),
                reader=READERS.DETECTOR, frame="cell:0", score=0.8,
                detector_role="dot", detector_class="augmentationDot")
    detail = {"head": head, "head_owned_elsewhere": True} if head else {}
    if role == "augmentation":
        log.record(R.Verdict(
            id=log._next_id("vrd"), subject=d, quantity=Q.DOT_ROLE,
            outcome=Outcome.DECIDED, value="augmentation",
            decider="adjudicate_dot_role",
            reason="right_of_and_level_with_a_head", detail=detail))
    else:
        log.record(R.Verdict(
            id=log._next_id("vrd"), subject=d, quantity=Q.DOT_ROLE,
            outcome=Outcome.ABSTAINED, value=None,
            decider="adjudicate_dot_role",
            reason=reason or "dot_role_ambiguous"))
    return d


def _reconcile(log, on=True):
    with mock.patch.dict(os.environ, ON if on else {"OMR_AUG_DOT_JOIN": ""},
                         clear=False):
        return J.reconcile_unjoined_dots(log)


class TestADecidedDotNamingAPlainHeadInAnotherCell(unittest.TestCase):
    """Brahms `1/0/10/5/12` -> head `1/0/9/5/1`: the dot is boxed in staff 10's
    strip, the note is staff 9's; the head's own strip never saw the dot, so
    its duration read `dots: 0`."""

    def _case(self, extra_flag=None):
        log = _log(92.0, cells=((1, 0, 10, 5),))
        h = _head(log, "glyph/1/0/9/5/1", (212, 727, 127, 102),
                  (4347.35, 2846.25, 4385.30, 2876.73), EIGHTH,
                  "noteheadBlackInSpace")
        if extra_flag:
            _glyph(log, "glyph/1/0/9/5/9", extra_flag[0], (0, 0, 10, 10),
                   extra_flag[1])
        d = _dot(log, "glyph/1/0/10/5/12", (396, 0, 27, 17),
                 (4402.34, 2851.0, 4410.40, 2856.08), "augmentation",
                 head=h.to_key())
        return log, h, d

    def test_RED_the_note_is_narrowed_to_plain_and_dotted(self):
        log, h, d = self._case()
        census = _reconcile(log)
        v = log.verdict(Q.DURATION, h)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, J.NARROWED_REASON)
        self.assertEqual([c.value["dots"] for c in v.candidates], [0, 1])
        self.assertEqual(v.candidates[1].value["beats"], 0.75)
        self.assertEqual(census["narrowed_decided_dot_named_this_head"], 1)
        self.assertEqual(v.detail["dot"], d.to_key())

    def test_the_flag_off_leaves_the_note_decided_plain(self):
        log, h, d = self._case()
        self.assertEqual(_reconcile(log, on=False), {})
        v = log.verdict(Q.DURATION, h)
        self.assertEqual((v.outcome, v.value["dots"]), (Outcome.DECIDED, 0))

    def test_CONTROL_a_dot_inside_a_flag_box_is_the_flags_tip(self):
        # Brahms `1/0/5/1/14`: the dot box lies inside the neighbouring note's
        # `flag8thUp` box -- the curl of a flag, not a dot.
        log = _log(85.75, cells=((1, 0, 5, 1),))
        h = _head(log, "glyph/1/0/4/1/0", (474, 635, 122, 108),
                  (1982.29, 1656.02, 2021.49, 1690.72), EIGHTH)
        _glyph(log, "glyph/1/0/4/1/10", "flag8thUp", (612, 403, 71, 254),
               (2026.63, 1581.48, 2049.44, 1663.09))
        _dot(log, "glyph/1/0/5/1/14", (652, 4, 29, 36),
             (2039.48, 1648.29, 2048.80, 1659.85), "augmentation",
             head=h.to_key())
        census = _reconcile(log)
        self.assertEqual(log.verdict(Q.DURATION, h).outcome, Outcome.DECIDED)
        self.assertEqual(census["dot_is_a_flag_tip"], 1)

    def test_CONTROL_a_head_that_already_carries_its_dot_is_untouched(self):
        # Brahms `0/0/0/0/12` names `0/0/1/0/5`, which already has dots 1 from
        # ITS OWN cell: the same physical dot twice, not a second dot.
        log = _log(100.0, cells=((0, 0, 0, 0),))
        dotted = {"beats": 1.5, "written": 1.5, "dots": 1, "beam_levels": 0}
        h = _head(log, "glyph/0/0/1/0/5", (982, 249, 95, 86),
                  (1647.71, 1885.45, 1689.08, 1922.91), dotted)
        _dot(log, "glyph/0/0/0/0/12", (1113, 1123, 27, 28),
             (1704.76, 1880.12, 1716.52, 1892.31), "augmentation",
             head=h.to_key())
        census = _reconcile(log)
        self.assertEqual(log.verdict(Q.DURATION, h).value["dots"], 1)
        self.assertEqual(census["head_already_dotted_or_not_a_decided_note"], 1)


class TestAnUnplacedDotBesideAPlainNote(unittest.TestCase):
    """Sean's Brahms 317803 page 0, `0/0/4/1/0`: a dotted half note. The dot is
    0.68 sp right of the head and 0.93 sp above its box centre -- outside the
    role window's 0.75, so `dot_role_ambiguous`, and the note went out a plain
    half."""

    def _case(self, role_reason="dot_role_ambiguous", value=HALF):
        log = _log(100.0)
        h = _head(log, "glyph/0/0/4/1/3", (360, 1000, 119, 57),
                  (2229.0, 3265.0, 2267.68, 3283.53), value,
                  "noteheadHalfInSpace")
        d = _dot(log, "glyph/0/0/4/1/0", (547, 914, 39, 44),
                 (2289.78, 3237.05, 2302.45, 3251.35), "abstain",
                 reason=role_reason)
        return log, h, d

    def test_RED_the_plain_half_is_narrowed_to_half_and_dotted_half(self):
        log, h, d = self._case()
        census = _reconcile(log)
        v = log.verdict(Q.DURATION, h)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual([c.value["beats"] for c in v.candidates], [2.0, 3.0])
        self.assertEqual(census["narrowed_unplaced_dot_beside_this_head"], 1)

    def test_the_flag_off_leaves_it_plain(self):
        log, h, d = self._case()
        _reconcile(log, on=False)
        self.assertEqual(log.verdict(Q.DURATION, h).outcome, Outcome.DECIDED)

    def test_CONTROL_a_dot_on_a_stroke_is_not_a_dot(self):
        # Sean 2026-10-09: ink on a stroke is not a lengthening dot -- the
        # role decision's own abstention, and it is not "ambiguous".
        log, h, d = self._case(role_reason="on_a_stroke")
        _reconcile(log)
        self.assertEqual(log.verdict(Q.DURATION, h).outcome, Outcome.DECIDED)

    def test_CONTROL_a_note_that_is_not_decided_is_not_touched(self):
        log = _log(100.0)
        h = _glyph(log, "glyph/0/0/4/1/3", "noteheadHalfInSpace",
                   (360, 1000, 119, 57), (2229.0, 3265.0, 2267.68, 3283.53))
        log.record(R.Verdict(
            id=log._next_id("vrd"), subject=h, quantity=Q.DURATION,
            outcome=Outcome.NARROWED, value=None,
            decider="adjudicate_duration", reason="beams_ambiguous",
            candidates=(R.Candidate(value={"beats": 1.5, "written": 1.5,
                                           "dots": 1, "beam_levels": 0},
                                    support=1.0),
                        R.Candidate(value=dict(EIGHTH), support=1.0))))
        _dot(log, "glyph/0/0/4/1/0", (547, 914, 39, 44),
             (2289.78, 3237.05, 2302.45, 3251.35), "abstain")
        census = _reconcile(log)
        self.assertEqual(log.verdict(Q.DURATION, h).reason, "beams_ambiguous")
        self.assertEqual(census["head_already_dotted_or_not_a_decided_note"], 1)

    def test_CONTROL_a_stray_dot_with_no_head_beside_it_changes_nothing(self):
        log = _log(100.0)
        h = _head(log, "glyph/0/0/4/1/3", (360, 1000, 119, 57),
                  (2229.0, 3265.0, 2267.68, 3283.53), HALF,
                  "noteheadHalfInSpace")
        # 5 sp to the right: not beside the note
        _dot(log, "glyph/0/0/4/1/0", (547, 914, 39, 44),
             (2429.78, 3237.05, 2442.45, 3251.35), "abstain")
        census = _reconcile(log)
        self.assertEqual(log.verdict(Q.DURATION, h).outcome, Outcome.DECIDED)
        self.assertEqual(census["no_head_beside_the_dot"], 1)

    def test_CONTROL_a_dot_centred_over_another_head_is_its_staccato(self):
        log = _log(100.0)
        h = _head(log, "glyph/0/0/4/1/3", (360, 1000, 119, 57),
                  (2229.0, 3265.0, 2267.68, 3283.53), QUARTER,
                  "noteheadBlackInSpace")
        # the NEXT note: the mark sits 0.8 sp above it, centred on it, and
        # 1.0 sp right of the first head's edge -- inside the first head's
        # dot window, but it is the second head's staccato.
        _head(log, "glyph/0/0/4/1/4", (500, 1000, 119, 57),
              (2287.0, 3265.0, 2325.68, 3283.53), QUARTER,
              "noteheadBlackInSpace")
        _dot(log, "glyph/0/0/4/1/0", (547, 914, 39, 44),
             (2300.0, 3241.0, 2312.68, 3255.3), "abstain")
        census = _reconcile(log)
        self.assertEqual(log.verdict(Q.DURATION, h).outcome, Outcome.DECIDED)
        self.assertEqual(census["staccato_like_over_another_head"], 1)

    def test_a_note_already_dotted_by_its_own_dot_is_not_narrowed(self):
        dotted = {"beats": 3.0, "written": 3.0, "dots": 1, "beam_levels": 0}
        log, h, d = self._case(value=dotted)
        _reconcile(log)
        self.assertEqual(log.verdict(Q.DURATION, h).value["dots"], 1)


class TestSeansTilesOfTheSameChord(unittest.TestCase):
    """Brahms 317803 p0 `0/0/11/0`, Sean's 2.121 tiles: `/4` and `/9` are
    DOTTED quarters (the dot was missed and the plain quarter chosen) and
    `/10` a SINGLE-dotted quarter (one dot boxed twice made it 1.75)."""

    def _narrowed_head(self, log, key, canon, page):
        g = _glyph(log, key, "noteheadBlackOnLine", canon, page)
        log.record(R.Verdict(
            id=log._next_id("vrd"), subject=g, quantity=Q.DURATION,
            outcome=Outcome.NARROWED, value=None,
            decider="adjudicate_duration", reason="beam_discounted_uncertain",
            candidates=(R.Candidate(value=dict(EIGHTH), support=2.0),
                        R.Candidate(value=dict(QUARTER), support=1.0))))
        return g

    def test_RED_a_narrowing_with_no_dotted_candidate_gains_them(self):
        log = _log(74.0, cells=((0, 0, 11, 0),))
        h = self._narrowed_head(log, "glyph/0/0/11/0/4", (990, 551, 95, 87),
                                (1651.19, 6044.99, 1692.57, 6082.88))
        _dot(log, "glyph/0/0/11/0/8", (1112, 611, 30, 33),
             (1704.33, 6071.12, 1717.39, 6085.49), "abstain")
        census = _reconcile(log)
        v = log.verdict(Q.DURATION, h)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(sorted(c.value["beats"] for c in v.candidates),
                         [0.5, 0.75, 1.0, 1.5])
        self.assertIn(1.5, [c.value["beats"] for c in v.candidates
                            if c.value["dots"] == 1])
        self.assertEqual(
            census["extended_a_narrowing_with_dotted_candidates"], 1)

    def test_the_flag_off_leaves_the_narrowing_alone(self):
        log = _log(74.0, cells=((0, 0, 11, 0),))
        h = self._narrowed_head(log, "glyph/0/0/11/0/4", (990, 551, 95, 87),
                                (1651.19, 6044.99, 1692.57, 6082.88))
        _dot(log, "glyph/0/0/11/0/8", (1112, 611, 30, 33),
             (1704.33, 6071.12, 1717.39, 6085.49), "abstain")
        _reconcile(log, on=False)
        self.assertEqual(len(log.verdict(Q.DURATION, h).candidates), 2)

    def test_CONTROL_a_narrowing_that_already_has_a_dotted_candidate_stays(self):
        log = _log(74.0, cells=((0, 0, 11, 0),))
        g = _glyph(log, "glyph/0/0/11/0/4", "noteheadBlackOnLine",
                   (990, 551, 95, 87), (1651.19, 6044.99, 1692.57, 6082.88))
        dotted = {"beats": 1.5, "written": 1.5, "dots": 1, "beam_levels": 0}
        log.record(R.Verdict(
            id=log._next_id("vrd"), subject=g, quantity=Q.DURATION,
            outcome=Outcome.NARROWED, value=None,
            decider="adjudicate_duration", reason="beam_discounted_uncertain",
            candidates=(R.Candidate(value=dict(dotted), support=2.0),
                        R.Candidate(value=dict(QUARTER), support=1.0))))
        _dot(log, "glyph/0/0/11/0/8", (1112, 611, 30, 33),
             (1704.33, 6071.12, 1717.39, 6085.49), "abstain")
        _reconcile(log)
        self.assertEqual(len(log.verdict(Q.DURATION, g).candidates), 2)


class TestOneDotBoxedTwiceIsOneDot(unittest.TestCase):
    """`0/0/11/0/15` and `0/0/11/0/24`: two boxes, 2 px apart, one dot."""

    def _attached(self, flag, gap_px=2.0):
        from tools.omr.staged import adjudicate
        from tools.omr.staged import adjudicators  # noqa: F401
        log = _log(74.0, cells=((0, 0, 11, 0),))
        log.observe(R.cell(0, 0, 11, 0), Q.CELL_BOX, (0.0, 0.0, 2000.0, 700.0),
                    reader=READERS.GEOMETRY, frame="page")
        h = R.glyph(0, 0, 11, 0, 10)
        log.observe(h, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(h, Q.GLYPH_BOX, ("noteheadBlackOnLine", 1464, 330, 97, 84),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        for gi, dy, sc in ((15, 0, 0.6), (24, int(gap_px), 0.5)):
            d = R.glyph(0, 0, 11, 0, gi)
            log.observe(d, Q.GLYPH_BOX,
                        ("augmentationDot", 1600, 330 + dy, 30, 30),
                        reader=READERS.DETECTOR, frame="cell:0", score=sc)
            log.observe(d, Q.AUG_DOT, (1615.0, 345.0 + dy),
                        reader=READERS.DETECTOR, frame="cell:0", score=sc,
                        detector_role="dot", detector_class="augmentationDot")
        env = {"OMR_AUG_DOT_JOIN": "1" if flag else ""}
        with mock.patch.dict(os.environ, env, clear=False):
            adjudicate.run(log)
        v = log.verdict(Q.DURATION, h)
        return v

    def test_RED_two_boxes_on_one_dot_make_one_dot(self):
        v = self._attached(True)
        self.assertEqual((v.detail or {}).get("dots_attached"), 1)

    def test_the_flag_off_counts_both_as_before(self):
        v = self._attached(False)
        self.assertEqual((v.detail or {}).get("dots_attached"), 2)

    def test_CONTROL_two_dots_over_a_third_of_a_space_apart_are_two_dots(self):
        v = self._attached(True, gap_px=25.0)       # 0.34 sp
        self.assertEqual((v.detail or {}).get("dots_attached"), 2)


class TestTheHookRunsAfterDuration(unittest.TestCase):
    def test_adjudicate_run_calls_the_reconcile_once(self):
        from tools.omr.staged import adjudicate
        from tools.omr.staged import adjudicators  # noqa: F401
        log = _log()
        with mock.patch.object(J, "reconcile_unjoined_dots") as m:
            adjudicate.run(log)
        self.assertEqual(m.call_count, 1)


if __name__ == "__main__":
    unittest.main()
