"""`arc_owner`: an arc belongs to the staff whose NOTEHEADS IT HUGS.

⚠️ THE TESTS THAT MATTER MOST ARE THE REFUSALS. This rule is COMPARATIVE by
measurement, not by taste — the clearance tail is not clean enough to
threshold on — so the tests that must never go green by accident are the ones
asserting an arc STAYS where a rival does not clearly beat it.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS

UPPER = R.staff(0, 0, 0)
LOWER = R.staff(0, 0, 1)


def _head(log, staff_i, gi, x, y, *, w=20.0, h=20.0):
    g = R.glyph(0, 0, staff_i, 0, gi)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlackOnLine", x, y, w, h),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                category="notehead",
                bbox_page_px=[x, y, x + w, y + h],
                x_center_page=x + w / 2.0, y_center_page=y + h / 2.0)
    return g


def _arc(log, staff_i, gi, x0, x1, y0, y1, cls="slur"):
    g = R.glyph(0, 0, staff_i, 0, gi)
    log.observe(g, Q.ARC_BOX, cls, reader=READERS.DETECTOR, frame="cell:0",
                score=0.8, x0=x0, x1=x1, y0=y0, y1=y1,
                x_center=(x0 + x1) / 2, y_center=(y0 + y1) / 2,
                bbox_page_px=[x0, y0, x1, y1],
                x_center_page=(x0 + x1) / 2.0, y_center_page=(y0 + y1) / 2.0)
    return g


def _spacing(log, staff, px=10.0):
    log.observe(staff, Q.STAFF_SPACING, px, reader=READERS.GEOMETRY,
                frame=G.FRAME_PAGE)


def _own(log, arc_glyph):
    log.freeze()
    adjudicate.run(log)
    return log.verdict(Q.ARC_OWNER, arc_glyph)


class TestItIsNoLongerAStub(unittest.TestCase):
    def test_the_registry_says_it_decides(self):
        self.assertFalse(adjudicate.REGISTRY[Q.ARC_OWNER].stub)


class TestTheArcGoesToTheStaffItHugs(unittest.TestCase):

    def _two_staves(self, arc_y0, arc_y1):
        """UPPER's arc, with LOWER's heads sitting right under it."""
        log = Log()
        _spacing(log, UPPER); _spacing(log, LOWER)
        # the arc is cut from staff 0 (UPPER)
        arc = _arc(log, 0, 0, 100.0, 300.0, arc_y0, arc_y1)
        # UPPER's own heads are FAR above the arc
        _head(log, 0, 1, 100.0, 0.0)
        _head(log, 0, 2, 280.0, 0.0)
        # LOWER's heads sit immediately below it
        _head(log, 1, 1, 100.0, arc_y1 + 2.0)
        _head(log, 1, 2, 280.0, arc_y1 + 2.0)
        return log, arc

    def test_an_arc_moves_to_the_staff_whose_heads_it_hugs(self):
        """⚠️ The Brahms Timpani case: it exported 4 slurs and 1 tie against a
        truth of ZERO — they are Violin 1's, drawn over ITS ledger notes in
        the 7.7-space gap between the two staves."""
        log, arc = self._two_staves(200.0, 220.0)
        v = _own(log, arc)
        self.assertEqual(v.value, LOWER.to_key())
        self.assertEqual(v.reason, "hugs_noteheads")
        self.assertEqual(v.detail["moved_from"], UPPER.to_key())

    def test_it_MOVES_and_never_deletes(self):
        """⚠️ `drop` measured 2,388 edits against `move`'s 2,371 — better
        arm-for-arm — and was REFUSED: it gets there by emitting 20 fewer
        slurs, 12 of them REAL. The verdict must NAME a staff, never nothing."""
        log, arc = self._two_staves(200.0, 220.0)
        v = _own(log, arc)
        self.assertIsNotNone(v.value)
        self.assertTrue(str(v.value).startswith("staff/"))


class TestTheRefusals(unittest.TestCase):
    """⚠️ The comparative rule's whole point: an arc leaves ONLY where another
    staff explains it better."""

    def test_an_arc_hugging_its_OWN_heads_stays(self):
        log = Log()
        _spacing(log, UPPER); _spacing(log, LOWER)
        arc = _arc(log, 0, 0, 100.0, 300.0, 100.0, 120.0)
        _head(log, 0, 1, 100.0, 122.0)      # own heads: hugging
        _head(log, 0, 2, 280.0, 122.0)
        _head(log, 1, 1, 100.0, 400.0)      # rival heads: far
        _head(log, 1, 2, 280.0, 400.0)
        v = _own(log, arc)
        self.assertEqual(v.value, UPPER.to_key())
        self.assertEqual(v.reason, "no_better_staff")

    def test_a_rival_covering_only_ONE_head_cannot_claim_it(self):
        """⚠️ `_ARC_RIVAL_MIN_COVERED = 2`, so a single stray head cannot take
        an arc."""
        log = Log()
        _spacing(log, UPPER); _spacing(log, LOWER)
        arc = _arc(log, 0, 0, 100.0, 300.0, 200.0, 220.0)
        _head(log, 0, 1, 100.0, 0.0)
        _head(log, 1, 1, 150.0, 222.0)      # ONE hugging head only
        v = _own(log, arc)
        self.assertEqual(v.value, UPPER.to_key())

    def test_a_ONE_STAFF_page_can_never_move_an_arc(self):
        """The rule is comparative, so it cannot fire with nobody to compare
        against — by construction, not by a threshold."""
        log = Log()
        _spacing(log, UPPER)
        arc = _arc(log, 0, 0, 100.0, 300.0, 200.0, 220.0)
        _head(log, 0, 1, 100.0, 0.0)
        _head(log, 0, 2, 280.0, 0.0)
        v = _own(log, arc)
        self.assertEqual(v.value, UPPER.to_key())
        self.assertEqual(v.reason, "no_rival_staff")

    def test_no_rival_staff_is_a_DECISION_not_an_abstention(self):
        """"No other staff explains this better" is an answer. Abstaining
        would lose the arc's home for no reason."""
        log = Log()
        _spacing(log, UPPER)
        arc = _arc(log, 0, 0, 100.0, 300.0, 200.0, 220.0)
        _head(log, 0, 1, 100.0, 0.0)
        v = _own(log, arc)
        self.assertEqual(v.outcome.value if hasattr(v.outcome, "value")
                         else v.outcome, "decided")


class TestTheFrame(unittest.TestCase):
    """⚠️ `gather_glyph_families` emitted CANONICAL coordinates only until
    2026-09-09, so this decision's declared input was present and in a frame
    that cannot answer a cross-staff question — the fault `Q.ONSET_COLUMN`
    paid for (1,062 columns, 699 agreeing to the FLOAT)."""

    def test_an_arc_with_no_PAGE_box_abstains_rather_than_using_the_cell_frame(self):
        log = Log()
        _spacing(log, UPPER); _spacing(log, LOWER)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.ARC_BOX, "slur", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.8,
                    x0=100.0, x1=300.0, y0=200.0, y1=220.0,
                    x_center=200.0, y_center=210.0,
                    frame_note="no page box: cell has no bbox_page_px")
        _head(log, 1, 1, 100.0, 222.0); _head(log, 1, 2, 280.0, 222.0)
        v = _own(log, g)
        self.assertEqual(v.reason, "no_page_frame")
        self.assertIsNone(v.value)

    def test_the_gatherer_now_CARRIES_the_page_box(self):
        """Anti-drift: if `gather_glyph_families` ever loses the page frame
        again, this decision silently abstains on every arc."""
        import inspect
        src = inspect.getsource(G.gather_glyph_families)
        self.assertIn("bbox_page_px", src)
        self.assertIn("_page_box", src)


class TestHeadsAreGroupedByOWNER(unittest.TestCase):
    """⚠️ The legacy rule in one line: the noteheads "have already been
    arbitrated across staves and each staff's head set is the one a READER
    would see". A cross-staff duplicate is FILED on the staff that detected
    it, so grouping by subject compares the arc against a page nobody sees."""

    def test_glyph_owner_is_declared_because_it_is_read(self):
        spec = adjudicate.REGISTRY[Q.ARC_OWNER]
        self.assertIn(Q.GLYPH_OWNER, spec.wants)

    def test_the_step_quantity_is_NOT_declared_because_it_is_not_read(self):
        """⚠️ A `wants` entry nothing reads is INERT: `Evidence` fills
        `missing`/`declined` only for quantities actually queried, so it
        records nothing and cannot be told from one that is read and always
        present. Ten decisions here carry such a declaration; this is not an
        eleventh."""
        spec = adjudicate.REGISTRY[Q.ARC_OWNER]
        self.assertNotIn(Q.NOTEHEAD_STAFF_POSITION, spec.wants)


class TestTheMarginIsLoadBearing(unittest.TestCase):
    """⚠️ WRITTEN BECAUSE A MUTATION SURVIVED. Deleting the
    `_ARC_RIVAL_MARGIN_SPACES` comparison left the first eleven tests GREEN —
    they only ever exercised rivals that beat the incumbent by a mile. The
    margin is a measured PLATEAU (every value 0.25–0.75 reattributes the same
    arcs over the eleven works; the answer first moves at 0.90), so a rival
    that is merely NEARER must not take the arc."""

    def _arc_between(self, own_gap_px, rival_gap_px):
        log = Log()
        _spacing(log, UPPER, 10.0); _spacing(log, LOWER, 10.0)
        arc = _arc(log, 0, 0, 100.0, 300.0, 200.0, 220.0)
        # own heads ABOVE the arc at own_gap_px
        _head(log, 0, 1, 100.0, 200.0 - 20.0 - own_gap_px)
        _head(log, 0, 2, 280.0, 200.0 - 20.0 - own_gap_px)
        # rival heads BELOW at rival_gap_px
        _head(log, 1, 1, 100.0, 220.0 + rival_gap_px)
        _head(log, 1, 2, 280.0, 220.0 + rival_gap_px)
        return _own(log, arc)

    def test_a_rival_nearer_by_LESS_than_the_margin_does_NOT_take_the_arc(self):
        # own 3px = 0.3 spaces, rival 1px = 0.1 -> margin 0.2 < 0.5
        v = self._arc_between(own_gap_px=3.0, rival_gap_px=1.0)
        self.assertEqual(v.value, UPPER.to_key(),
                         "a merely-nearer rival must not claim the arc")
        self.assertEqual(v.reason, "no_better_staff")

    def test_a_rival_nearer_by_MORE_than_the_margin_does(self):
        # own 80px = 8.0 spaces, rival 1px = 0.1 -> margin 7.9 > 0.5
        v = self._arc_between(own_gap_px=80.0, rival_gap_px=1.0)
        self.assertEqual(v.value, LOWER.to_key())

    def test_the_constants_are_IMPORTED_from_the_shipped_rule(self):
        """⚠️ Imported, never restated, so the staged and legacy paths cannot
        drift apart on a measured plateau."""
        import inspect
        from tools.omr.staged.adjudicators import ownership as O
        src = inspect.getsource(O.adjudicate_arc_owner)
        self.assertIn("from ...export import", src)
        self.assertIn("_ARC_RIVAL_MARGIN_SPACES", src)


class TestHeadsFollowTheirOWNERAcrossStaves(unittest.TestCase):
    """⚠️ ALSO WRITTEN BECAUSE A MUTATION SURVIVED. Grouping heads by the staff
    their CELL was cut from left every earlier test green, because none of them
    had a head whose owner differed from its subject. That is precisely the
    population the rule exists for: a cross-staff duplicate is FILED on the
    staff that detected it and OWNED by another."""

    def test_a_head_owned_elsewhere_counts_for_its_OWNER_not_its_cell(self):
        log = Log()
        _spacing(log, UPPER, 10.0); _spacing(log, LOWER, 10.0)
        arc = _arc(log, 0, 0, 100.0, 300.0, 200.0, 220.0)
        # UPPER's own genuine heads are far above -> UPPER does not hug it
        _head(log, 0, 1, 100.0, 0.0)
        _head(log, 0, 2, 280.0, 0.0)
        # Two heads CUT FROM UPPER's cell (subject staff 0) that ownership has
        # already awarded to LOWER, sitting right under the arc.
        for gi, x in ((7, 100.0), (8, 280.0)):
            g = _head(log, 0, gi, x, 222.0)
            log.observe(g, Q.GLYPH_BAND_DISTANCE, 1.0, reader=READERS.GEOMETRY,
                        frame=G.FRAME_PAGE, candidate=LOWER.to_key(),
                        own=False, position_in_candidate=2.0)
            log.observe(g, Q.GLYPH_BAND_DISTANCE, 9.0, reader=READERS.GEOMETRY,
                        frame=G.FRAME_PAGE, candidate=UPPER.to_key(),
                        own=True, position_in_candidate=2.0)
        v = _own(log, arc)
        self.assertEqual(
            v.value, LOWER.to_key(),
            "the hugging heads are LOWER's by ownership, so the arc is too")
