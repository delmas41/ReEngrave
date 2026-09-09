"""The families that were detected and read by NOTHING.

⚠️ Until 2026-09-09 the staged record carried these five kinds of ink only as
an untyped `GLYPH_BOX`. Four of the quantities existed — in `Q` and in a
stub's `wants` — and were observed by no gather site, so writing those
adjudicators would still have produced nothing. The fifth, `Q.REST`, did not
exist at all, which made rests the worst case of the family this architecture
exists to kill: nothing anywhere declared their absence.

Measured over four real conductor's pages before the fix: **838 rests, 755
ties, 291 slurs, 542 dynamic letters, 40 articulation marks, 1 hairpin.**
"""

import unittest

from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS, Scope


class Det:
    def __init__(self, name, x=100, y=50, w=20, h=16, conf=0.8,
                 category="structural"):
        self.smufl_name = name
        self.x_canonical, self.y_canonical = x, y
        self.width_canonical, self.height_canonical = w, h
        self.confidence, self.category = conf, category

    @property
    def y_center(self):
        return self.y_canonical + self.height_canonical // 2

    @property
    def x_center(self):
        return self.x_canonical + self.width_canonical // 2


CELL = R.cell(0, 0, 0, 0)


def _log(*dets):
    log = Log()
    gather.gather_glyph_families(log, {CELL.to_key(): list(dets)})
    return log


def _values(log, quantity):
    return [r.value for r in
            log.rows(quantity, CELL, scope=Scope.SELF_AND_DESCENDANTS)]


class TestEachFamilyGetsATypedRow(unittest.TestCase):
    def test_a_rest_is_observed_as_a_rest(self):
        log = _log(Det("restWhole", category="rest"))
        self.assertEqual(_values(log, Q.REST), ["restWhole"])

    def test_ties_and_slurs_are_arcs(self):
        log = _log(Det("tie"), Det("slur", x=200))
        self.assertEqual(sorted(_values(log, Q.ARC_BOX)), ["slur", "tie"])

    def test_a_dynamic_letter_is_NOT_this_functions_to_claim(self):
        """⚠️ IT USED TO BE, AND THE CHANGE IS DELIBERATE.
        `gather_dynamic_letters` owns `Q.DYNAMIC_LETTER`: it reads the same
        ink in the STAFF's own frame, so it can record the band offset that a
        per-cell frame cannot express. Emitting the letter here as well would
        put two rows from ONE reader on one glyph -- the "two rows from one
        reader are ONE signal" fault, arrived at by accident rather than by
        argument. See `test_staged_dynamics.py` for the owner's own tests.
        """
        log = _log(Det("dynamicF", category="dynamic"))
        self.assertEqual(_values(log, Q.DYNAMIC_LETTER), [])

    def test_an_articulation_is_observed_with_the_side_its_class_names(self):
        log = _log(Det("articStaccatoAbove", category="ornament"))
        rows = log.rows(Q.ARTICULATION_MARK, CELL,
                        scope=Scope.SELF_AND_DESCENDANTS)
        self.assertEqual(rows[0].value, "articStaccatoAbove")
        self.assertEqual(rows[0].detail["side"], "above")

    def test_a_class_that_states_no_side_records_None_rather_than_guessing(self):
        """⚠️ `class_aliases.COARSER_THAN_CANONICAL` records
        `articulationAccent` / `Staccato` / `Tenuto` as coarser than the
        canonical spelling precisely because they carry NO side, and the
        legacy attach pass requires the geometry to agree with the side when
        there is one."""
        log = _log(Det("articulationStaccato", category="ornament"))
        rows = log.rows(Q.ARTICULATION_MARK, CELL,
                        scope=Scope.SELF_AND_DESCENDANTS)
        self.assertIsNone(rows[0].detail["side"])


class TestAHairpinIsNeverReadAsALetter(unittest.TestCase):
    """⚠️ THE HAZARD IS UNCHANGED; ITS OWNER MOVED.
    `dynamicDiminuendoHairpin` carries the detector's `dynamic` category AND a
    class name starting with `dynamic`, so any PREFIX test spells a crescendo
    into a dynamic word. This function used to hold the ordering that kept
    them apart; the dynamics rungs now do, and they do it structurally rather
    than by ordering -- `_DYNAMIC_LETTER_CLASSES` is an explicit six-member
    set, so a hairpin cannot fall into it whatever order the branches run in.
    A structural guarantee still needs a test, because the set could be
    widened to a prefix by someone who did not know why it was not one.
    """

    def test_the_letter_set_is_EXPLICIT_and_holds_no_hairpin(self):
        for cls in gather._WEDGE_CLASSES:
            self.assertNotIn(cls, gather._DYNAMIC_LETTER_CLASSES)
        # ⚠️ Six letters, not a `dynamic` prefix. If this becomes a prefix
        # test, the hairpins come back in with it.
        self.assertEqual(len(gather._DYNAMIC_LETTER_CLASSES), 6)

    def test_both_hairpin_classes_name_which_way_they_open(self):
        self.assertEqual(gather._WEDGE_CLASSES, {
            "dynamicCrescendoHairpin": "crescendo",
            "dynamicDiminuendoHairpin": "diminuendo",
        })

    def test_this_function_claims_NEITHER_quantity(self):
        """Single ownership, asserted from the other side."""
        log = _log(Det("dynamicCrescendoHairpin", category="dynamic"),
                   Det("dynamicF", x=300, category="dynamic"))
        self.assertEqual(_values(log, Q.WEDGE_BOX), [])
        self.assertEqual(_values(log, Q.DYNAMIC_LETTER), [])


class TestItRecordsWhereTheInkIs(unittest.TestCase):
    """⚠️ The extents are here because the consumers cannot work without them
    and the class alone is not enough: an arc is PAIRED across a barline by
    its ends, a hairpin is anchored by its EDGES (its ink does not overlap the
    notes it binds at all — 0 of 4 on Mahler), and `f`+`f` becomes `ff` by
    x-adjacency."""

    def test_an_arc_carries_its_span(self):
        log = _log(Det("tie", x=100, w=250))
        row = log.rows(Q.ARC_BOX, CELL, scope=Scope.SELF_AND_DESCENDANTS)[0]
        self.assertEqual((row.detail["x0"], row.detail["x1"]), (100, 350))

    def test_every_family_row_carries_the_detector_score(self):
        log = _log(Det("restQuarter", conf=0.42, category="rest"))
        row = log.rows(Q.REST, CELL, scope=Scope.SELF_AND_DESCENDANTS)[0]
        self.assertAlmostEqual(row.score, 0.42)


class TestItDecidesNothing(unittest.TestCase):
    """⚠️ The split is the point. A rest's DURATION, an arc's OWNER and KIND, a
    hairpin's ANCHORS and the spelling of `f`+`f` into `ff` are each an
    interpretation with its own evidence and its own right to abstain."""

    def test_a_multi_measure_rest_indicator_is_still_RECORDED(self):
        """⚠️ `restHBar` carries no single duration — `rhythm._rest_duration`
        returns None for it — and it is observed anyway. Recording the ink and
        declining to read it is the honest pair; dropping it at the gather
        site is how `Q.REST` came to be missing in the first place."""
        log = _log(Det("restHBar", category="rest"))
        self.assertEqual(_values(log, Q.REST), ["restHBar"])

    def test_no_duration_verdict_is_written_here(self):
        log = _log(Det("restWhole", category="rest"))
        self.assertEqual(log.verdicts(Q.DURATION, CELL,
                                      scope=Scope.SELF_AND_DESCENDANTS), ())

    def test_a_glyph_of_no_family_gets_no_typed_row(self):
        log = _log(Det("beam"), Det("staff", x=0), Det("ledgerLine", x=50))
        for q in (Q.REST, Q.ARC_BOX, Q.WEDGE_BOX, Q.DYNAMIC_LETTER,
                  Q.ARTICULATION_MARK):
            self.assertEqual(_values(log, q), [], q)


class TestTheStubsNowHaveARealDomain(unittest.TestCase):
    """⚠️ Until the rows existed there was nothing to name, so each of these
    stubs abstained once per DETECTION — 2,728 rows on one page, burying its
    199 real subjects in 2,529 no-ops. `subjects_from` is what makes an
    abstention mean "I could not read THIS arc"."""

    def test_each_starved_stub_names_the_quantity_it_is_about(self):
        from tools.omr.staged import adjudicate
        adjudicate._ensure_decisions()
        expected = {
            Q.ARC_OWNER: Q.ARC_BOX,
            Q.ARC_KIND: Q.ARC_BOX,
            Q.ARTICULATION_OWNER: Q.ARTICULATION_MARK,
            Q.WEDGE_ANCHOR: Q.WEDGE_BOX,
            Q.DYNAMIC: Q.DYNAMIC_LETTER,
        }
        for quantity, domain in expected.items():
            self.assertEqual(adjudicate.REGISTRY[quantity].subjects_from,
                             domain, quantity)

    def test_a_page_with_no_arcs_produces_no_arc_abstentions(self):
        """The point of a domain: silence where there is nothing to decide,
        rather than a no-op per glyph."""
        from tools.omr.staged import adjudicate
        adjudicate._ensure_decisions()
        log = _log(Det("restWhole", category="rest"))
        log.freeze()
        spec = adjudicate.REGISTRY[Q.ARC_OWNER]
        self.assertEqual(adjudicate.subjects_for(log, spec), ())


if __name__ == "__main__":
    unittest.main()
