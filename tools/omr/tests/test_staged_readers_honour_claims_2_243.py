"""ROADMAP 2.243 (STAGED ADJUDICATE; flags `OMR_DOTS_HONOUR_CLAIMS` and `OMR_BEAMS_HONOUR_CLAIMS`, default OFF until Sean's tiles).

The augmentation-dot ROLE reader and the beam reader consult `Q.STROKE_OWNER`: ink the owner DECIDED to a slur / hairpin / word / accidental is
not a dot, not a staccato and not a beam level. Every test that says RED has a twin that must NOT fire (unclaimed ink, contested ink, a dot's
own ink, a head-owned blob, the flag OFF). Constructed cells only."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators, consequences          # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.adjudicate import Evidence
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import Outcome, Q, READERS
from tools.omr.tests.test_staged_stems_from_strokes_2_204 import UP, V, build
from tools.omr.tests.test_stroke_owner_2_205 import _claimant

DOTS = rhythm.DOTS_HONOUR_CLAIMS_ENV
BEAMS = rhythm.BEAMS_HONOUR_CLAIMS_ENV
CELL = R.cell(0, 0, 0, 0)
DOT_BOX = (650, 540, 40, 40)                                   # right of the head (500, 500, 130, 100), level with it
TIP = dict(kind="curve", i=1, box=DOT_BOX, L=0.5, T=0.15, touches=[], steps=None)      # a slur's tip: a short curve
BLOB = dict(kind="blob", i=1, box=DOT_BOX, L=0.4, T=0.4, touches=[], steps=None)       # a round dot


FAR = (900, 100, 40, 40)                                       # no head in reach: the role reader abstains `dot_role_ambiguous`


def _dot_cell(strokes, claimants=(), on=True, box=DOT_BOX):
    """A head with a dot box beside it standing on `strokes`; `claimants` = (glyph index, class, box, covered ordinals)."""
    holder = {}

    def extra(log):
        d = R.glyph(0, 0, 0, 0, 9)
        log.observe(d, Q.GLYPH_BOX, ("augmentationDot",) + tuple(box), reader=READERS.DETECTOR, frame="cell:0", score=0.8)
        log.observe(d, Q.AUG_DOT, (box[0] + box[2] / 2.0, box[1] + box[3] / 2.0), reader=READERS.DETECTOR, frame="cell:0",
                    score=0.8, detector_role="dot", detector_class="augmentationDot")
        log.observe(d, Q.GLYPH_STROKES, [s["i"] for s in strokes], reader=READERS.CV_GLYPH_STROKES, frame="cell:0",
                    shares=[1.0] * len(strokes), cover_min=0.5, partial=[])
        for gi, cls, cbox, cov in claimants:
            _claimant(log, gi, cls, cbox, cov)
        holder["dot"] = d
    log, _gs = build([V(0, UP)] + list(strokes), finder=(UP,), extra=extra)
    with mock.patch.dict(os.environ, {DOTS: "1" if on else "0"}):
        adjudicate.run(log)
    return log.verdict(Q.DOT_ROLE, holder["dot"])


class TestDotsHonourClaims(unittest.TestCase):

    def test_a_slur_tip_the_arc_owns_is_not_a_dot_RED(self):
        tip = dict(TIP, box=FAR)
        v = _dot_cell([tip], claimants=[(7, "slur", FAR, (1,))], box=FAR)
        self.assertIsNone(v.value)
        self.assertEqual(v.reason, "ink_owned_by_another_mark")
        self.assertIn("arc", v.detail["owner_families"])

    def test_twin_OFF_the_same_cell_reads_as_it_did(self):
        tip = dict(TIP, box=FAR)
        v = _dot_cell([tip], claimants=[(7, "slur", FAR, (1,))], on=False, box=FAR)
        self.assertEqual(v.reason, "dot_role_ambiguous")

    def test_twin_a_role_already_decided_is_never_overturned_by_the_owner(self):
        v = _dot_cell([TIP], claimants=[(7, "slur", DOT_BOX, (1,))])
        self.assertEqual(v.value, "augmentation")

    def test_twin_a_round_dot_the_dot_owns_stays_a_dot(self):
        v = _dot_cell([BLOB], claimants=[(7, "augmentationDot", DOT_BOX, (1,))])
        self.assertEqual(v.value, "augmentation")

    def test_twin_ink_nobody_claimed_stays_a_dot_candidate(self):
        v = _dot_cell([BLOB])
        self.assertEqual(v.value, "augmentation")

    def test_twin_a_staccato_family_owner_is_the_dots_own(self):
        v = _dot_cell([BLOB], claimants=[(7, "articStaccatoAbove", DOT_BOX, (1,))])
        self.assertNotEqual(v.reason, "ink_owned_by_another_mark")

    def test_twin_a_box_standing_on_no_filed_stroke_is_not_refused(self):
        v = _dot_cell([], claimants=[])
        self.assertNotEqual(v.reason, "ink_owned_by_another_mark")


def _beam_dropped(strokes, claimants=(), on=True, box=(500, 60, 400, 60)):
    """`_not_a_beam_by_ink`'s drop map for one CV beam row `box` over `strokes` (a head with an up-stem beside)."""
    def extra(log):
        log.observe(CELL, Q.BEAM_STROKE, tuple(float(t) for t in box), reader=READERS.CV_LINES, frame="cell:0", x0=box[0], x1=box[0] + box[2],
                    y_center=box[1] + box[3] / 2.0, image="no_staff", staff_lines_erased=True)
        for gi, cls, bx, cov in claimants:
            _claimant(log, gi, cls, bx, cov)
    log, gs = build([V(0, UP)] + list(strokes), finder=(UP,), extra=extra)
    with mock.patch.dict(os.environ, {BEAMS: "1" if on else "0"}):
        adjudicate.run(log)
        ev = Evidence(log, gs[0], adjudicate.REGISTRY[Q.DURATION])
        beams = [b for b in ev.rows(Q.BEAM_STROKE, scope=R.Scope.SELF_AND_ANCESTORS, subject=CELL)]
        stems = ev.rows(Q.STEM, scope=R.Scope.SELF_AND_ANCESTORS, subject=CELL)
        _kept, dropped, _used = rhythm._not_a_beam_by_ink(ev, CELL, beams, stems, 20.0)
    return dropped


HAIRPIN = dict(kind="horizontal", i=1, box=(520, 80, 360, 20), L=3.6, T=0.2, touches=[0], steps=None)       # a thin line across the beam row
THICK = dict(kind="horizontal", i=1, box=(520, 70, 360, 50), L=3.6, T=0.6, touches=[0], steps=None)         # a beam-thick stroke


class TestBeamsHonourClaims(unittest.TestCase):

    def test_a_beam_row_on_a_hairpin_the_owner_decided_is_not_a_beam_RED(self):
        d = _beam_dropped([HAIRPIN], claimants=[(7, "dynamicCrescendoHairpin", (520, 80, 360, 20), (1,))])
        self.assertEqual(list(d.values()), ["owned_by_another_mark"])

    def test_twin_OFF_the_row_is_not_dropped_for_that_reason(self):
        d = _beam_dropped([HAIRPIN], claimants=[(7, "dynamicCrescendoHairpin", (520, 80, 360, 20), (1,))], on=False)
        self.assertNotIn("owned_by_another_mark", d.values())

    def test_twin_an_unclaimed_stroke_in_the_row_keeps_it(self):
        d = _beam_dropped([THICK])
        self.assertNotIn("owned_by_another_mark", d.values())

    def test_twin_a_head_owned_blob_is_never_called_not_a_beam(self):
        blob = dict(kind="blob", i=1, box=(520, 70, 120, 90), L=1.2, T=0.9, touches=[0], steps=None)
        d = _beam_dropped([blob], claimants=[(7, "noteheadBlack", (520, 70, 120, 90), (1,))])
        self.assertNotIn("owned_by_another_mark", d.values())

    def test_twin_a_row_with_no_stroke_in_it_is_left_to_the_older_tests(self):
        d = _beam_dropped([], claimants=[])
        self.assertNotIn("owned_by_another_mark", d.values())


if __name__ == "__main__":
    unittest.main()
