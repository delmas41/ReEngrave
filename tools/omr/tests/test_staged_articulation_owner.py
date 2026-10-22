"""`articulation_owner`: a mark belongs to the notehead it is printed against.

⚠️ THE SIDE TEST IS WHERE THIS CAN GO SILENTLY WRONG, and it reads backwards:
a LARGER canonical y is LOWER on the page, so a mark printed ABOVE its notehead
has the SMALLER y. A test suite that only ever places marks above notes would
pass with the comparison inverted, so both sides are exercised and the inverted
comparison is a mutation arm.

⚠️ THE REFUSALS CARRY THEIR OWN POSITIVE CONTROL. Every test asserting that a
mark is NOT attached sets up a case that differs from an attaching one in ONE
fact, and asserts the attaching version too -- otherwise the whole class passes
the moment the decision starts abstaining on everything.
"""

from __future__ import annotations

import unittest

from tools.omr import transcribe as _legacy
from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS

CELL = R.cell(0, 0, 0, 0)
HOME = R.staff(0, 0, 0)
NEIGHBOUR = R.staff(0, 0, 1)


def _head(log, gi, x, y, *, w=20.0, h=20.0, staff=0, stem="down"):
    """A notehead with ONE CV stem touching it (ROADMAP 2.12f round 2: the owner
    reads each head's `Q.STEM_DIRECTION`, so a head with no stem row is a head
    whose direction is unread). `stem="down"` is the default because the default
    mark is an ABOVE mark, and an above mark is on a stem-down head's notehead
    side; the BELOW tests pass `stem="up"`. `stem=None` files no stem."""
    g = R.glyph(0, 0, staff, 0, gi)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlackOnLine", x, y, w, h),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                category="notehead")
    log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine",
                reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    if stem == "up":
        _stem(log, x + w - 3, y - 40, 40 + h / 2)
    elif stem == "down":
        _stem(log, x, y + h / 2, 40 + h / 2)
    return g


def _stem(log, x, y, h, w=3.0):
    log.observe(R.cell(0, 0, 0, 0), Q.STEM, (x, y, w, h),
                reader=READERS.CV_LINES, frame="cell:0", x0=x, x1=x + w,
                y_center=y + h / 2, image="no_staff", staff_lines_erased=True)


def _owned_by_the_neighbour(log, glyph, *, near=1.0, far=4.0):
    """ROADMAP 2.27: a real cross-staff contest that `glyph_owner` DECIDES
    for `NEIGHBOUR`, filed the same way `test_staged_dynamics._contest`
    proves the identical composition for a dynamic letter -- two `Q.GLYPH_
    BAND_DISTANCE` rows on `glyph`'s OWN subject, near the candidate that
    should win and far from the one that should lose."""
    log.observe(glyph, Q.GLYPH_BAND_DISTANCE, far, reader=READERS.GEOMETRY,
                frame="page", candidate=HOME.to_key(), own=True,
                position_in_candidate=2.0)
    log.observe(glyph, Q.GLYPH_BAND_DISTANCE, near, reader=READERS.GEOMETRY,
                frame="page", candidate=NEIGHBOUR.to_key(), own=False,
                position_in_candidate=2.0)


def _mark(log, gi, x, y, cls="articStaccatoAbove", *, w=6.0, h=6.0):
    g = R.glyph(0, 0, 0, 0, gi)
    side = ("above" if cls.endswith("Above")
            else "below" if cls.endswith("Below") else None)
    log.observe(g, Q.ARTICULATION_MARK, cls, reader=READERS.DETECTOR,
                frame="cell:0", score=0.8,
                x0=x, x1=x + w, y0=y, y1=y + h,
                x_center=x + w / 2.0, y_center=y + h / 2.0, side=side)
    return g


def _decide(log, mark):
    log.freeze()
    adjudicate.run(log)
    return log.verdict(Q.ARTICULATION_OWNER, mark)


class TestItIsNoLongerAStub(unittest.TestCase):
    def test_the_registry_says_it_decides(self):
        self.assertFalse(adjudicate.REGISTRY[Q.ARTICULATION_OWNER].stub)

    def test_the_constant_is_imported_not_restated(self):
        """⚠️ AN AST CHECK, because a copied number does not fail a test.

        The 0.75 was swept over eight engraved works and sits on a plateau.
        A second copy of it here would drift silently from the legacy pass,
        which is the `LETTER_METERS` lesson.
        """
        import inspect
        from tools.omr.staged.adjudicators import ownership
        src = inspect.getsource(ownership.adjudicate_articulation_owner)
        self.assertIn("_ARTIC_MAX_DX_NOTEHEAD_WIDTHS", src)
        self.assertNotIn("0.75", src)


class TestTheMarkGoesToTheNoteheadUnderIt(unittest.TestCase):

    def test_a_staccato_above_takes_the_note_below_it(self):
        log = Log()
        _mark(log, 0, 100.0, 0.0)            # above: smaller y
        head = _head(log, 1, 97.0, 40.0)
        v = _decide(log, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, head.to_key())
        self.assertEqual(v.detail["articulation"], "staccato")

    def test_a_staccato_BELOW_takes_the_note_above_it(self):
        """⚠️ THE OTHER SIDE. Without this, inverting the y comparison passes."""
        log = Log()
        _mark(log, 0, 100.0, 80.0, cls="articStaccatoBelow")
        head = _head(log, 1, 97.0, 40.0, stem="up")
        v = _decide(log, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, head.to_key())

    def test_the_NEAREST_by_gap_wins_not_the_nearest_in_x(self):
        """ROADMAP 2.12f round 2 (Sean, tiles 7, 9, 10): the x window GATES the
        column, the edge gap SELECTS within it. Both heads below the mark are in
        its column; the nearer in x is the farther in y and does NOT win."""
        log = Log()
        # ⚠️ CENTRES, not corners: the mark spans 100-106 so its centre is 103.
        _mark(log, 0, 100.0, 0.0)
        _head(log, 1, 96.0, 100.0)           # centre 106, dx  3  (x-nearer)
        near = _head(log, 2, 88.0, 20.0)     # centre  98, dx  5, TOUCHING
        v = _decide(log, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(v.value, near.to_key())

    def test_the_kind_travels_with_the_owner(self):
        """A tenuto must not reach the file as a staccato."""
        log = Log()
        _mark(log, 0, 100.0, 80.0, cls="articTenutoBelow")
        _head(log, 1, 97.0, 40.0, stem="up")
        v = _decide(log, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(v.detail["articulation"], "tenuto")


class TestTheRefusals(unittest.TestCase):
    """⚠️ Each carries its POSITIVE CONTROL: the same page, one fact changed."""

    def test_a_mark_with_no_notehead_on_its_side_abstains(self):
        log = Log()
        _mark(log, 0, 100.0, 80.0)           # says Above, but sits BELOW
        _head(log, 1, 97.0, 40.0)
        v = _decide(log, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(v.outcome, "abstained")
        # ROADMAP 2.12f ROUND 2: `no_notehead` IS the true statement here (Sean,
        # tiles 1, 2, 5, 11 -- the class was right and the head is in the
        # NEIGHBOUR staff), so the round-1 relabel `suffix_contradicts_geometry`
        # is reverted. The measurement stays in the detail.
        self.assertEqual(v.reason, "no_notehead")
        self.assertEqual(v.detail["measured_side"], "below")

        log2 = Log()                          # positive control: move it above
        _mark(log2, 0, 100.0, 0.0)
        _head(log2, 1, 97.0, 40.0)
        self.assertEqual(_decide(log2, R.glyph(0, 0, 0, 0, 0)).outcome,
                         "decided")

    def test_a_mark_too_far_in_x_abstains(self):
        """The limit is 0.75 NOTEHEAD WIDTHS -- here 15px of a 20px head."""
        log = Log()
        _mark(log, 0, 100.0, 0.0)
        _head(log, 1, 130.0, 40.0)           # centre 37px away, over the limit
        v = _decide(log, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "no_notehead")
        self.assertIn("limit_canonical_px", v.detail)

        log2 = Log()                          # positive control: bring it in
        _mark(log2, 0, 100.0, 0.0)
        _head(log2, 1, 98.0, 40.0)
        self.assertEqual(_decide(log2, R.glyph(0, 0, 0, 0, 0)).outcome,
                         "decided")

    def test_a_cell_with_no_notehead_at_all_abstains(self):
        log = Log()
        _mark(log, 0, 100.0, 0.0)
        v = _decide(log, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "no_notehead")

    def test_a_class_that_names_no_side_abstains_with_its_own_reason(self):
        """⚠️ ZERO REACH ON THE DOCUMENT THIS LANDED WITH, so it is tested here.

        `class_aliases.COARSER_THAN_CANONICAL` records `articulationStaccato`
        as a coarser spelling carrying no side. All 24 marks on Litolff
        `984073` p1-3 name one, so the page cannot exercise this branch.
        """
        log = Log()
        _mark(log, 0, 100.0, 0.0, cls="articulationStaccato")
        _head(log, 1, 97.0, 40.0)
        v = _decide(log, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "no_side_declared")

        log2 = Log()                          # positive control: name the side
        _mark(log2, 0, 100.0, 0.0, cls="articStaccatoAbove")
        _head(log2, 1, 97.0, 40.0)
        self.assertEqual(_decide(log2, R.glyph(0, 0, 0, 0, 0)).reason,
                         "nearest_on_notehead_side")

    def test_a_mark_outside_the_five_exported_kinds_abstains(self):
        """`_ARTICULATION_KINDS` is the legacy list and is not widened here."""
        log = Log()
        _mark(log, 0, 100.0, 0.0, cls="articSoftAccentAbove")
        _head(log, 1, 97.0, 40.0)
        self.assertEqual(_decide(log, R.glyph(0, 0, 0, 0, 0)).reason,
                         "no_side_declared")


class TestTheMedianWidthSetsTheLimit(unittest.TestCase):
    def test_one_giant_detection_does_not_widen_the_cell(self):
        """⚠️ MEDIAN, not max -- one merged blob must not set the limit for
        every mark in the bar, which is the same reason the legacy pass takes
        a median."""
        log = Log()
        _mark(log, 0, 100.0, 0.0)
        _head(log, 1, 130.0, 40.0)                  # too far under a 20px head
        _head(log, 2, 400.0, 40.0, w=400.0)         # a blob, far away
        _head(log, 3, 500.0, 40.0)
        v = _decide(log, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(v.outcome, "abstained",
                         "the blob widened the limit and let a far head win")


class TestAPadCandidateOwnedByTheNeighbourIsNotThisStaffsToAttachTo(
        unittest.TestCase):
    """ROADMAP 2.27. The measure cell is padded 4-6 staff spaces (CLAUDE.md
    §10) and on a conductor's page that reaches the next staff's ink, so this
    cell's own `Q.GLYPH_BOX` can hold a notehead that `glyph_owner` has
    already DECIDED belongs to `NEIGHBOUR` -- the exact ink a resolved
    contest drops rather than relocates. Before ROADMAP 2.27 this decision
    never read `Q.GLYPH_OWNER` at all (`grep GLYPH_OWNER` on its `wants=`
    returned nothing), so it attached the mark to that candidate anyway.

    ⚠️ THE FIX. Remove the `_owned_by_a_different_staff` filter and this goes
    RED -- the mark attaches to `ghost`, which `glyph_owner` has already
    handed to the neighbour.
    """

    def test_the_only_candidate_owned_by_the_neighbour_is_not_attached(self):
        log = Log()
        _mark(log, 0, 100.0, 0.0)              # above: smaller y
        ghost = _head(log, 1, 97.0, 40.0)      # this cell's only notehead
        _owned_by_the_neighbour(log, ghost)
        v = _decide(log, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "owned_by_another_staff")
        self.assertEqual(v.detail["n_candidates"], 1)

        # ⚠️ POSITIVE CONTROL: the identical page, minus the contest -- an
        # uncontested candidate is untouched and the mark still attaches.
        log2 = Log()
        _mark(log2, 0, 100.0, 0.0)
        head = _head(log2, 1, 97.0, 40.0)
        v2 = _decide(log2, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(v2.outcome, "decided")
        self.assertEqual(v2.value, head.to_key())

    def test_a_real_notehead_beside_a_neighbours_ghost_is_still_found(self):
        """The filter drops ONLY the losing candidate -- it must not make the
        decision abstain just because a contest exists in the cell at all."""
        log = Log()
        _mark(log, 0, 100.0, 0.0)
        ghost = _head(log, 1, 400.0, 40.0)     # far away, and owned elsewhere
        _owned_by_the_neighbour(log, ghost)
        real = _head(log, 2, 97.0, 40.0)       # this staff's own note
        v = _decide(log, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, real.to_key())

    def test_a_candidate_glyph_owner_never_ran_on_is_untouched(self):
        """No `Q.GLYPH_BAND_DISTANCE` row was ever filed for this head --
        `glyph_owner`'s domain is the CONTESTED population only
        (`subjects_from=Q.GLYPH_BAND_DISTANCE`) -- so it carries no verdict
        at all, and `owner is None` must fall through unchanged rather than
        abstain."""
        log = Log()
        _mark(log, 0, 100.0, 0.0)
        head = _head(log, 1, 97.0, 40.0)
        v = _decide(log, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, head.to_key())


if __name__ == "__main__":
    unittest.main()
