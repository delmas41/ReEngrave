"""ROADMAP 2.199 -- the accidental owner's head search without a class guess (flag `OMR_ACCIDENTAL_ANCHOR_UNCLASSED`, default OFF).

Every test that says the centre-anchored head IS taken has a twin that says it must not be: flag off, the shape reader confirms the class, the
class anchor already decides (additive), the two anchors coincide (sharp / natural), two heads at the centre (ambiguity), no head at all."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import accidental_anchor as AA
from tools.omr.staged import export as E
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS
from tools.omr.tests import test_staged_accidental as TA

FLAG = "OMR_ACCIDENTAL_ANCHOR_UNCLASSED"
NAT = {"bl": 0.0, "tr": 0.0, "shape": "natural"}
FLATSH = {"bl": 0.8, "tr": 0.0, "shape": "flat"}
UNCL = {"bl": 0.28, "tr": 0.0, "shape": "unclear"}


def _ink(shape, cls="accidentalFlat", alt="b", class_pos=6.0, centre=4.0, heads=((4.0,),), flag=True):
    """One accidental the detector drew as `cls`, whose class anchor stands at `class_pos` and whose box centre at `centre`; one head per entry
    of `heads` (a tuple of positions sharing a column)."""
    log = Log()
    TA._cell_unit(log)
    g = R.glyph(0, 0, 0, 0, 0)
    y0 = centre * TA.HALF - 3 * TA.SPACE
    log.observe(g, Q.GLYPH_BOX, (cls, 88.0, y0, 12.0, 6 * TA.SPACE), reader=READERS.DETECTOR, frame="cell:0", score=0.8, category="accidental")
    log.observe(g, Q.ACCIDENTAL_STAFF_POSITION, class_pos, reader=READERS.GEOMETRY, frame="cell:0", alteration=alt, detector_class=cls,
                anchor_fraction=0.715, box_centre_position=centre, residual=0.0, rounded=int(class_pos), x0=88.0, x1=100.0, y0=y0,
                y1=y0 + 6 * TA.SPACE, confidence=0.8, shape=shape)
    gi = 1
    for col, ps in enumerate(heads):
        for p in ps:
            TA._head(log, gi, 106.0 + 40.0 * col, p)
            gi += 1
    with mock.patch.dict(os.environ, {FLAG: "1" if flag else "0", "OMR_ONE_INK_ONE_MARK": "1", "OMR_ACCIDENTAL_SHAPE": "1"}):
        TA._decide(log)
    return log.verdict(Q.ACCIDENTAL_OWNER, g)


class TestUnclassedAnchor(unittest.TestCase):

    def test_a_natural_boxed_as_a_flat_finds_its_head_from_the_centre(self):
        v = _ink(NAT)
        self.assertEqual(v.outcome.value, "decided")
        self.assertEqual(v.reason, "immediately_right_same_position")
        au = v.detail["anchor_unclassed"]
        self.assertEqual(au["why"], "contradicted")
        self.assertEqual(au["label"], "b")                                   # the alteration stays the detector's label
        self.assertAlmostEqual(v.detail["accidental_position"], 4.0, places=2)

    def test_an_unclear_shape_is_unverified_and_also_searches_from_the_centre(self):
        v = _ink(UNCL)
        self.assertEqual(v.detail["anchor_unclassed"]["why"], "unverified")

    def test_TWIN_flag_off_it_stays_no_candidate(self):
        v = _ink(NAT, flag=False)
        self.assertEqual(v.reason, "no_candidate")

    def test_TWIN_a_shape_that_reads_the_same_class_keeps_the_class_anchor(self):
        v = _ink(FLATSH)
        self.assertEqual(v.reason, "no_candidate")                           # the class is confirmed: the miss is a missing head

    def test_TWIN_the_class_anchor_that_decides_is_never_moved(self):
        v = _ink(NAT, heads=((6.0, 4.0),))                                   # a head at the class anchor AND one at the centre
        self.assertNotIn("anchor_unclassed", v.detail)
        self.assertAlmostEqual(v.detail["accidental_position"], 6.0, places=2)

    def test_TWIN_anchors_that_coincide_say_nothing_new(self):
        v = _ink(NAT, cls="accidentalSharp", alt="#", class_pos=4.3, centre=4.0, heads=((2.4,),))   # shift 0.3 < half a step: no second search
        self.assertEqual(v.reason, "no_candidate")

    def test_TWIN_two_heads_at_the_centre_abstain_ambiguous(self):
        v = _ink(NAT, heads=((3.5, 4.5),))
        self.assertEqual(v.reason, "ambiguous_height")

    def test_TWIN_no_head_inside_the_bound_of_the_centre_either(self):
        v = _ink(NAT, heads=((0.0,),))
        self.assertEqual(v.reason, "no_candidate")

    def test_the_bound_is_the_owners_own(self):
        v = _ink(NAT, heads=((5.5,),))                                       # 1.5 from the centre, 0.5 from the class anchor -> class anchor decides
        self.assertNotIn("anchor_unclassed", v.detail)
        v2 = _ink(NAT, heads=((2.4,),))                                      # 1.6 from the centre
        self.assertEqual(v2.reason, "no_candidate")

    def test_applies_is_pure(self):
        self.assertIsNone(AA.applies("accidentalFlat", 6.0, None, NAT))
        self.assertIsNone(AA.applies("accidentalFlat", 6.0, 4.0, {"shape": "flat"}))
        self.assertEqual(AA.applies("accidentalFlat", 6.0, 4.0, {"shape": "sharp"})["why"], "contradicted")
        self.assertEqual(AA.applies("accidentalDoubleFlat", 6.0, 4.0, {"shape": "flat"})["why"], "contradicted")


class _Rec:
    def __init__(self, owner_detail):
        self._o = {"id": "o1", "quantity": Q.ACCIDENTAL_OWNER, "outcome": "decided", "detail": owner_detail}
        self._a = {"id": "a1", "quantity": Q.ACCIDENTAL, "outcome": "decided", "basis": ["o1"]}

    def verdict(self, q, sub):
        return self._a if q == Q.ACCIDENTAL else None

    def verdict_by_id(self, i):
        return self._o if i == "o1" else None


class TestExportMarksItGuessed(unittest.TestCase):
    def test_it_is_written_guessed_with_the_measured_shape_beside_the_label(self):
        g = E.one_ink_guess_of(_Rec({"anchor_unclassed": {"label": "b", "measured_shape": "natural", "named_shape": "flat"}}), "x")
        self.assertEqual(g["rule"], "accidental_anchor_unclassed")
        self.assertEqual([c["value"] for c in g["candidates"]], ["b", "natural"])
        self.assertEqual(g["chosen"]["value"], "b")

    def test_TWIN_no_marker_no_guess(self):
        self.assertIsNone(E.one_ink_guess_of(_Rec({}), "x"))

    def test_TWIN_an_unclear_shape_adds_no_candidate(self):
        g = E.one_ink_guess_of(_Rec({"anchor_unclassed": {"label": "b", "measured_shape": "unclear", "named_shape": "flat"}}), "x")
        self.assertEqual([c["value"] for c in g["candidates"]], ["b"])


if __name__ == "__main__":
    unittest.main()
