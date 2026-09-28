"""*Is this really one?*, once per gathered family — ROADMAP 3.4g.

⚠️ RUN RED FIRST, against the unrepaired tree (`origin/main` at `5f109dd2`,
with `adjudicators/family_precision.py` absent, `owner:other` unknown to
`human_evidence` and `Q.LEDGER_IS_NOT_A_LEDGER` &c. not in `record.Q`).
Every test below then fails at import or at the first attribute lookup —
`AttributeError: LEDGER_IS_NOT_A_LEDGER` / `ModuleNotFoundError:
...family_precision` / `KeyError` out of `adjudicate.REGISTRY` — which is
what says these fixtures exercise code that did not previously exist. See
`benchmarks/omr-family-refusals-2026-09/FINDINGS.md` §RED for the captured
run.

⚠️ EVERY REFUSAL TEST HAS A POSITIVE CONTROL IN THE SAME CLASS, because a
battery of refusal tests passes by refusing everything — the discipline
`test_staged_notehead_precision.py` states and CLAUDE.md §6b requires. For
the human rules the control is a glyph of the same family with NO human row;
for the ledger geometry it is a rung one whole space below line 1 with a
notehead standing on it.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import export as SX
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import family_precision as FP
from tools.omr.staged.adjudicators import notehead_precision as NP
from tools.omr.staged.record import ABSTAIN, Log, Outcome, Q, READERS
from tools.omr.staged.review import human_evidence as HE

CELL = R.cell(0, 0, 0, 0)
STAFF = R.staff(0, 0, 0)
SPACING_CANONICAL = 100.0            # one staff space in the CELL's frame
SPACING_PAGE = 20.0                  # one staff space in PAGE pixels
#: Five staff lines in page px, bottom line last. Bottom line y = 1080,
#: top line y = 1000 — `_staff_step`'s step 0 and step 8.
LINE_YS = [1000.0, 1020.0, 1040.0, 1060.0, 1080.0]
#: Where a fixture's `ledgerLine` box sits in the CELL's own frame. The head
#: rule (3.4g-2) reads a distance in this frame, so the rung needs a fixed
#: canonical origin to measure it from.
LEDGER_X_CANONICAL = 200.0
LEDGER_Y_CANONICAL = 200.0

#: One row per family: (quantity, a detector class of that family, the word
#: the decision decides `False` with, the extra quantity GATHER files).
#: ⚠️ DERIVED FROM THE REGISTRY, not typed against it — `test_every_family`
#: below asserts this table covers `FP.FAMILY_REFUSALS` exactly, so a family
#: added to the module without a test here goes RED rather than unnoticed.
FAMILIES = (
    (Q.LEDGER_IS_NOT_A_LEDGER, "ledgerLine", "ledger_line", None),
    (Q.ACCIDENTAL_IS_NOT_AN_ACCIDENTAL, "accidentalFlat", "accidental", None),
    (Q.REST_IS_NOT_A_REST, "restQuarter", "rest", Q.REST),
    (Q.ARPEGGIATO_IS_NOT_AN_ARPEGGIATO, "arpeggiato", "arpeggiato", None),
    (Q.ARC_IS_NOT_AN_ARC, "slur", "arc", Q.ARC_BOX),
    (Q.DYNAMIC_IS_NOT_A_DYNAMIC, "dynamicF", "dynamic", Q.DYNAMIC_LETTER),
    (Q.ARTICULATION_IS_NOT_AN_ARTICULATION, "articStaccatoAbove",
     "articulation", Q.ARTICULATION_MARK),
)


# ─────────────────────────────────────────────────────────────────────────────
# fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _staff_geometry(log, *, line_ys=LINE_YS, spacing=SPACING_PAGE):
    if line_ys is not None:
        log.observe(STAFF, Q.STAFF_LINES, list(line_ys),
                    reader=READERS.GEOMETRY, frame="page")
    if spacing is not None:
        log.observe(STAFF, Q.STAFF_SPACING, spacing,
                    reader=READERS.GEOMETRY, frame="page")
    log.observe(CELL, Q.CELL_STAFF_SPACE, SPACING_CANONICAL,
                reader=READERS.GEOMETRY, frame="cell:0")


def _page_box_at_step(step, *, x0=500.0, x1=560.0, thickness=2.0):
    """A page rectangle whose CENTRE sits at this staff step.

    ⚠️ INVERTS `rhythm._staff_step` rather than guessing: that function reads
    `(bottom - centre) / half`, so a centre of `bottom - step * half` lands
    exactly on the step asked for. A fixture that computed the y by hand
    would be testing my arithmetic, not the decision's.
    """
    half = SPACING_PAGE / 2.0
    centre = max(LINE_YS) - step * half
    return [x0, centre - thickness / 2.0, x1, centre + thickness / 2.0]


def _box(log, gi, cls, *, quantity=None, page_box=None, w_c=140.0, h_c=20.0,
         x_c=200.0, y_c=200.0, category=None):
    g = R.glyph(0, 0, 0, 0, gi)
    kw = {}
    if page_box is not None:
        kw["bbox_page_px"] = list(page_box)
    log.observe(g, Q.GLYPH_BOX, (cls, x_c, y_c, w_c, h_c),
                reader=READERS.DETECTOR, frame="cell:0", score=0.7,
                category=category or cls, **kw)
    if quantity is not None:
        log.observe(g, quantity, cls, reader=READERS.DETECTOR,
                    frame="cell:0", score=0.7)
    return g


def _human(log, g, value):
    """One `Q.HUMAN_BOX_VERDICT` row, exactly as a review sidecar files it."""
    return log.observe(g, Q.HUMAN_BOX_VERDICT, value, reader=READERS.SEAN,
                       frame="review:box", sidecar="t.json", action="act-0001")


def _run(log, *quantities):
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=tuple(quantities))
    return log


# ─────────────────────────────────────────────────────────────────────────────
# the declarations
# ─────────────────────────────────────────────────────────────────────────────

class TestEveryGatheredFamilyHasOne(unittest.TestCase):

    def test_the_table_in_this_file_covers_every_family(self):
        """⚠️ THE GUARD THAT STOPS THIS FILE ROTTING. A family added to
        `family_precision` without a row here would otherwise be untested and
        look tested, which is the shape of a hand-written inventory going
        stale — the fault `inventory.py` exists to prevent one level up."""
        self.assertEqual(sorted(q for q, _c, _w, _e in FAMILIES),
                         sorted(FP.FAMILY_REFUSALS))

    def test_none_of_them_is_a_stub(self):
        for quantity, _c, _w, _e in FAMILIES:
            with self.subTest(quantity):
                self.assertFalse(adjudicate.REGISTRY[quantity].stub)

    def test_each_declares_the_human_witness(self):
        for quantity, _c, _w, _e in FAMILIES:
            with self.subTest(quantity):
                self.assertIn(Q.HUMAN_BOX_VERDICT,
                              adjudicate.REGISTRY[quantity].wants)

    def test_each_declares_both_human_reasons(self):
        for quantity, _c, _w, _e in FAMILIES:
            with self.subTest(quantity):
                for reason in NP.HUMAN_REFUSAL_REASONS:
                    self.assertIn(reason,
                                  adjudicate.REGISTRY[quantity].reasons)

    def test_each_runs_in_ORDER(self):
        for quantity, _c, _w, _e in FAMILIES:
            with self.subTest(quantity):
                self.assertIn(quantity, adjudicate.ORDER)

    def test_the_ledger_is_decided_before_the_notehead_reads_its_rungs(self):
        """⚠️ A DEPENDENCY, NOT A PREFERENCE. `notehead_precision.
        _ledger_rungs_in_cell` reads this decision's verdict so a refused
        rung is not counted; the reverse order would let a staff-line
        fragment vouch for a note."""
        order = adjudicate.ORDER
        self.assertLess(order.index(Q.LEDGER_IS_NOT_A_LEDGER),
                        order.index(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD))

    def test_the_three_families_with_no_quantity_narrow_by_class(self):
        """`ledger`, `accidental` and `arpeggiato` have only `Q.GLYPH_BOX`,
        whose domain is every detection on the page — so each must declare a
        class narrowing or it would file a verdict per glyph."""
        for quantity in (Q.LEDGER_IS_NOT_A_LEDGER,
                         Q.ACCIDENTAL_IS_NOT_AN_ACCIDENTAL,
                         Q.ARPEGGIATO_IS_NOT_AN_ARPEGGIATO):
            with self.subTest(quantity):
                spec = adjudicate.REGISTRY[quantity]
                self.assertEqual(spec.subjects_from, Q.GLYPH_BOX)
                self.assertTrue(spec.subjects_classed)


class TestTheClassNarrowingIsTheDomain(unittest.TestCase):

    def test_a_notehead_gets_no_ledger_verdict(self):
        """THE NARROWING'S OWN POSITIVE CONTROL: the ledger decision must see
        the ledger box in the same cell and NOT the notehead beside it."""
        log = Log()
        _staff_geometry(log)
        head = _box(log, 0, "noteheadBlackOnLine", quantity=Q.NOTEHEAD_CLASS,
                    page_box=_page_box_at_step(4.0))
        rung = _box(log, 1, "ledgerLine", page_box=_page_box_at_step(-2.0))
        _run(log, Q.LEDGER_IS_NOT_A_LEDGER)
        self.assertIsNone(log.verdict(Q.LEDGER_IS_NOT_A_LEDGER, head))
        self.assertIsNotNone(log.verdict(Q.LEDGER_IS_NOT_A_LEDGER, rung))

    def test_a_narrowing_without_a_domain_is_refused(self):
        """⚠️ A CONTROL THAT CAN FAIL on the framework itself: a class list
        with no `subjects_from` names no rows to match against."""
        with self.assertRaises(ValueError):
            adjudicate.decision(
                quantity=Q.LEDGER_IS_NOT_A_LEDGER, scope=R.Kind.GLYPH,
                wants=(), reasons=("x",), composed_from=(Q.GLYPH_BOX,),
                subjects_classed=("ledgerLine",))(lambda ev: None)


# ─────────────────────────────────────────────────────────────────────────────
# the human witness — every family, both reasons, with a positive control
# ─────────────────────────────────────────────────────────────────────────────

class TestAHumanNothingReachesEveryFamily(unittest.TestCase):

    def _one(self, quantity, cls, extra, value):
        log = Log()
        _staff_geometry(log)
        # ⚠️ OUTSIDE the staff band and AT a rung step, so the ledger's own
        # geometry cannot be what refuses it — the human must be.
        g = _box(log, 0, cls, quantity=extra,
                 page_box=_page_box_at_step(-2.0))
        if cls == "ledgerLine":
            # ⚠️ 3.4g-2: a rung with no note on it is refused by Sean's
            # second convention, so the positive control stands one ON it —
            # or the "untouched" control would be refused by geometry and
            # prove nothing about the human.
            _box(log, 9, "noteheadBlackOnLine", quantity=Q.NOTEHEAD_CLASS,
                 page_box=_page_box_at_step(-2.0))
        if value is not None:
            _human(log, g, value)
        _run(log, quantity)
        return log.verdict(quantity, g)

    def test_not_a_symbol_refuses_in_every_family(self):
        for quantity, cls, _word, extra in FAMILIES:
            with self.subTest(quantity):
                v = self._one(quantity, cls, extra, "not_a_symbol")
                self.assertEqual(v.outcome, Outcome.DECIDED)
                self.assertIs(v.value, True)
                self.assertEqual(v.reason, "human_not_a_symbol")

    def test_owner_other_refuses_in_every_family(self):
        """⚠️ SEAN, 2026-09-23, ON HIS OWN MARKS: *"'belongs to violin' were
        about the fact that they belonged to a different staff"*. The claim
        is *not this staff*, so it is a refusal here and an award nowhere."""
        for quantity, cls, _word, extra in FAMILIES:
            with self.subTest(quantity):
                v = self._one(quantity, cls, extra,
                              f"owner:{HE.OWNER_OTHER}")
                self.assertEqual(v.outcome, Outcome.DECIDED)
                self.assertIs(v.value, True)
                self.assertEqual(v.reason, "human_other_staff")

    def test_a_glyph_with_no_human_row_is_untouched(self):
        """THE POSITIVE CONTROL. Without it every test above would pass on a
        decision that refused its whole domain."""
        for quantity, cls, word, extra in FAMILIES:
            with self.subTest(quantity):
                v = self._one(quantity, cls, extra, None)
                self.assertEqual(v.outcome, Outcome.DECIDED)
                self.assertIs(v.value, False)
                self.assertEqual(v.reason, word)

    def test_an_is_a_naming_another_family_refuses(self):
        v = self._one(Q.REST_IS_NOT_A_REST, "restQuarter", Q.REST,
                      "is_a:barline")
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "human_not_a_symbol")
        self.assertEqual(v.detail["human_says"], "is_a:barline")

    def _named_owner(self, value, *, contested):
        """One accidental box, a named owner, and a band row or not.

        ⚠️ THE BAND ROW IS THE WHOLE VARIABLE. `adjudicate_glyph_owner`'s
        domain is `subjects_from=Q.GLYPH_BAND_DISTANCE`, so a glyph carrying
        one is a glyph that contest WILL decide and a glyph carrying none is
        one it never sees.
        """
        log = Log()
        _staff_geometry(log)
        g = _box(log, 0, "accidentalFlat", page_box=_page_box_at_step(-2.0))
        if contested:
            log.observe(g, Q.GLYPH_BAND_DISTANCE, 3.0,
                        reader=READERS.GEOMETRY, frame="page",
                        candidate="staff/0/0/1", own=False)
        _human(log, g, value)
        _run(log, Q.ACCIDENTAL_IS_NOT_AN_ACCIDENTAL)
        return log.verdict(Q.ACCIDENTAL_IS_NOT_AN_ACCIDENTAL, g)

    def test_a_named_owner_refuses_where_the_contest_cannot_hear_it(self):
        """⚠️⚠️ SEAN'S TWO ACCIDENTALS. He marked them *belongs to Violin II*
        and they reached NOTHING, because `glyph_owner`'s domain is the
        contested notehead population and an accidental is never in it. An
        uncontested glyph with a named owner has no contest to be awarded by,
        so the only thing his reading can mean here is *not this staff*."""
        v = self._named_owner("owner:staff/0/0/1", contested=False)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "human_other_staff")
        self.assertEqual(v.detail["human_says"], "owner:staff/0/0/1")

    def test_a_named_owner_on_a_CONTESTED_glyph_is_left_to_the_contest(self):
        """THE POSITIVE CONTROL for the rule above, and the reason it is
        narrow: where `glyph_owner` CAN hear him it decides, and answering
        the same question here would file two answers to one question and
        rename the export bucket from `owned_by_another_staff` — which says
        WHICH staff — to one that does not."""
        v = self._named_owner("owner:staff/0/0/1", contested=True)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "accidental")

    def test_a_named_owner_that_is_THIS_staff_is_not_a_refusal(self):
        """⚠️ `human_evidence._twin_on` records that the commonest `own_box`
        is a human pulling a glyph BACK to the staff it was cut from, which
        is the opposite claim and must never read as *not here*."""
        v = self._named_owner(f"owner:{STAFF.to_key()}", contested=False)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "accidental")

    def test_the_verdict_carries_what_he_said(self):
        v = self._one(Q.ARC_IS_NOT_AN_ARC, "slur", Q.ARC_BOX, "not_a_symbol")
        self.assertEqual(v.detail["human_reader"], READERS.SEAN)
        self.assertEqual(v.detail["human_sidecar"], "t.json")
        self.assertEqual(v.detail["human_action"], "act-0001")
        self.assertEqual(v.detail["class"], "slur")
        self.assertTrue(v.used)


class TestOwnerOtherDoesNotReachTheOwnershipContest(unittest.TestCase):

    def test_human_owner_skips_it(self):
        """`Q.GLYPH_OWNER`'s value is a STAFF KEY; `other` is not one, and
        awarding it would put a word where a subject belongs."""
        log = Log()
        _staff_geometry(log)
        g = _box(log, 0, "noteheadBlackOnLine", quantity=Q.NOTEHEAD_CLASS,
                 page_box=_page_box_at_step(4.0))
        _human(log, g, f"owner:{HE.OWNER_OTHER}")
        log.freeze()
        from tools.omr.staged.adjudicate import Evidence
        spec = adjudicate.REGISTRY[Q.GLYPH_OWNER]
        from tools.omr.staged.adjudicators.ownership import _human_owner
        self.assertIsNone(_human_owner(Evidence(log, g, spec)))

    def test_a_named_owner_still_reaches_it(self):
        """THE POSITIVE CONTROL for the skip: the named form is untouched."""
        log = Log()
        _staff_geometry(log)
        g = _box(log, 0, "noteheadBlackOnLine", quantity=Q.NOTEHEAD_CLASS,
                 page_box=_page_box_at_step(4.0))
        _human(log, g, "owner:staff/0/0/3")
        log.freeze()
        from tools.omr.staged.adjudicate import Evidence
        from tools.omr.staged.adjudicators.ownership import _human_owner
        hit = _human_owner(Evidence(log, g,
                                    adjudicate.REGISTRY[Q.GLYPH_OWNER]))
        self.assertIsNotNone(hit)
        self.assertEqual(hit[1], "staff/0/0/3")

    def test_the_notehead_refusal_reads_owner_other(self):
        log = Log()
        _staff_geometry(log)
        log.observe(CELL, Q.CELL_BOX, [400.0, 900.0, 800.0, 1200.0],
                    reader=READERS.GEOMETRY, frame="cell:0")
        g = _box(log, 0, "noteheadHalfInSpace", quantity=Q.NOTEHEAD_CLASS,
                 w_c=140.0, h_c=100.0, page_box=_page_box_at_step(4.0))
        log.observe(g, Q.GLYPH_CONF, 0.9, reader=READERS.DETECTOR,
                    frame="cell:0", score=0.9)
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, 4.0,
                    reader=READERS.GEOMETRY, frame="cell:0")
        _human(log, g, f"owner:{HE.OWNER_OTHER}")
        _run(log, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD)
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "human_other_staff")


# ─────────────────────────────────────────────────────────────────────────────
# §LEDGER — the geometry
# ─────────────────────────────────────────────────────────────────────────────

#: A notehead's height in the CELL frame: one staff space. ⚠️ REALISTIC ON
#: PURPOSE, not a token size — `tall_not_a_rung` asks whether a head's box
#: INTERSECTS the rung's, and an 18-unit head would make that test measure
#: the fixture instead of the geometry.
HEAD_H_CANONICAL = SPACING_CANONICAL


def _ledger_verdict(*, step, h_c=20.0, w_c=140.0, page_box=True,
                    geometry=True, heads_at=None, head_dist_spaces=None,
                    head_x_overlaps=True, heads_outward=None):
    """One `ledgerLine` box, and optionally the heads that x-overlap it.

    ⚠️ THE HEADS' DISTANCES ARE SET IN THE CANONICAL CELL FRAME and the
    rung's POSITION in page pixels, because that is where each of them is
    measured — `family_precision` never compares the two; the step says only
    which way is OUT (up above the staff, down below it).

    `heads_outward` — SIGNED distances in spaces, one head each, + farther
    from the staff than the rung, - between the rung and the staff.
    `head_dist_spaces` — ONE head at that distance on the STAFFWARD side (the
    side only the tolerance can keep; below the rung for a box inside the
    band, where out is undefined). `heads_at` only gives a head a page box
    (it needs one only to look like a real row).
    """
    log = Log()
    if geometry:
        _staff_geometry(log)
    else:
        log.observe(CELL, Q.CELL_STAFF_SPACE, SPACING_CANONICAL,
                    reader=READERS.GEOMETRY, frame="cell:0")
    out_dir = -1.0 if step > 8.0 else 1.0     # canonical y grows DOWN
    offsets = []                              # canonical, + = down
    if heads_outward is not None:
        offsets += [o * out_dir for o in heads_outward]
    if head_dist_spaces is not None:
        staffward = (1.0 if 0.0 <= step <= 8.0 else -out_dir)
        offsets.append(head_dist_spaces * staffward)
    if heads_at is not None and not offsets:
        offsets.append(0.0)
    rung_mid = LEDGER_Y_CANONICAL + h_c / 2.0
    for i, off in enumerate(offsets):
        head_mid = rung_mid + off * SPACING_CANONICAL
        _box(log, 9 + i, "noteheadBlackOnLine", quantity=Q.NOTEHEAD_CLASS,
             page_box=_page_box_at_step(
                 step if heads_at is None else heads_at),
             w_c=130.0, h_c=HEAD_H_CANONICAL,
             x_c=(LEDGER_X_CANONICAL if head_x_overlaps
                  else LEDGER_X_CANONICAL + w_c + 40.0),
             y_c=head_mid - HEAD_H_CANONICAL / 2.0)
    g = _box(log, 0, "ledgerLine", w_c=w_c, h_c=h_c,
             x_c=LEDGER_X_CANONICAL, y_c=LEDGER_Y_CANONICAL,
             page_box=_page_box_at_step(step) if page_box else None)
    _run(log, Q.LEDGER_IS_NOT_A_LEDGER)
    return log.verdict(Q.LEDGER_IS_NOT_A_LEDGER, g)


class TestTheLedgerGeometry(unittest.TestCase):

    def _rung(self, **kw):
        return _ledger_verdict(**kw)

    # ── the positive control, first ─────────────────────────────────────────

    def test_a_rung_one_space_below_line_1_with_a_head_on_it_is_KEPT(self):
        """⚠️⚠️ THE POSITIVE CONTROL THE WHOLE §LEDGER SECTION RESTS ON. A
        real first ledger line stands ONE WHOLE SPACE below the bottom line
        — step -2 — with a notehead on it. Nothing here may refuse it."""
        v = self._rung(step=-2.0, heads_at=-2.0)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "ledger_line")

    def test_a_rung_one_space_above_line_5_is_KEPT(self):
        v = self._rung(step=10.0, heads_at=10.0)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "ledger_line")

    def test_the_second_and_third_rungs_are_KEPT(self):
        for step in (-4.0, -6.0, 12.0, 14.0):
            with self.subTest(step=step):
                self.assertIs(self._rung(step=step, heads_at=step).value,
                              False)

    # ── inside_the_staff — Sean's FIRST convention, 2026-09-24 ──────────────

    def test_a_box_on_the_middle_line_is_refused(self):
        v = self._rung(step=4.0)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "inside_the_staff")

    def test_a_box_on_each_of_the_five_lines_is_refused(self):
        """⚠️ THE REASON CHANGED IN 3.4g-2 AND THE OUTCOME DID NOT. All five
        lines are INSIDE the band (steps 0 and 8 are its edges), so Sean's
        position convention condemns them before the line tolerance is
        consulted at all."""
        for step in (0.0, 2.0, 4.0, 6.0, 8.0):
            with self.subTest(step=step):
                v = self._rung(step=step)
                self.assertIs(v.value, True)
                self.assertEqual(v.reason, "inside_the_staff")

    def test_a_box_in_the_middle_of_the_staff_is_refused_even_off_every_line(
            self):
        """⚠️⚠️ THE RULE `on_a_staff_line` COULD NOT REACH, and the reason
        3.4g-2 exists. Sean's crop 1 (`glyph/4/0/9/1/7`) sits at step 4.96 —
        0.48 spaces from the nearest line, twice the measured tolerance — and
        he answered *"no — middle of the staff, where there would never be a
        ledger line"*."""
        v = self._rung(step=4.96, head_dist_spaces=2.06)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "inside_the_staff")

    def test_inside_the_staff_outranks_a_head_standing_right_on_it(self):
        """A head on the box does not make a box inside the band a rung."""
        v = self._rung(step=4.0, head_dist_spaces=0.0)
        self.assertEqual(v.reason, "inside_the_staff")

    # ── on_a_staff_line — now the OUTER lines only ──────────────────────────

    def test_a_box_just_outside_the_band_on_the_outer_line_is_refused(self):
        v = self._rung(step=-0.2, head_dist_spaces=0.0)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "on_a_staff_line")

    def test_the_tolerance_is_the_measured_one_and_holds_at_its_edge(self):
        """⚠️ THE BOUND THAT MATTERS IS THE OTHER ONE: inside the tolerance
        refuses, and a real rung at 1.0 space is FOUR TIMES clear of it.

        ⚠️ BOTH BOXES CARRY A HEAD since 3.4g-2, or the one outside the
        tolerance would be refused by Sean's second convention instead and
        this test would pass while measuring nothing."""
        inside = FP.ON_A_STAFF_LINE_TOL_SPACES - 0.01
        outside = FP.ON_A_STAFF_LINE_TOL_SPACES + 0.01
        self.assertIs(self._rung(step=-2.0 * inside,
                                 head_dist_spaces=0.0).value, True)
        self.assertIs(self._rung(step=-2.0 * outside,
                                 head_dist_spaces=0.0).value, False)

    def test_the_tolerance_cannot_reach_the_first_rung(self):
        self.assertLess(FP.ON_A_STAFF_LINE_TOL_SPACES, 0.5)

    # ── no_head_on_the_rung — Sean's SECOND convention, 2026-09-24 ──────────

    def test_a_rung_with_no_head_anywhere_in_the_cell_is_refused(self):
        v = self._rung(step=-2.0)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "no_head_on_the_rung")

    def test_a_head_that_does_not_x_overlap_the_rung_is_not_its_head(self):
        v = self._rung(step=-2.0, head_dist_spaces=0.0,
                       head_x_overlaps=False)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "no_head_on_the_rung")
        self.assertEqual(v.detail["heads_x_overlapping"], 0)

    def test_a_head_further_than_the_measured_tolerance_is_not_its_head(self):
        v = self._rung(step=-2.0,
                       head_dist_spaces=FP.HEAD_NEAR_TOL_SPACES + 0.5)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "no_head_on_the_rung")

    def test_the_head_tolerance_holds_at_its_edge(self):
        """THE POSITIVE CONTROL for the head rule, at the derived number."""
        inside = self._rung(step=-2.0,
                            head_dist_spaces=FP.HEAD_NEAR_TOL_SPACES - 0.01)
        outside = self._rung(step=-2.0,
                             head_dist_spaces=FP.HEAD_NEAR_TOL_SPACES + 0.01)
        self.assertIs(inside.value, False)
        self.assertIs(outside.value, True)

    def test_an_inner_rung_of_a_three_rung_run_is_KEPT(self):
        """⚠️⚠️ WHY THE TOLERANCE IS TWO AND THREE QUARTER SPACES AND NOT
        ONE. A note three spaces above the staff prints THREE rungs and
        stands on the OUTERMOST: the innermost is two whole spaces from the
        only head that x-overlaps it. A one-space rule would delete the
        bottom of every long ladder — which is `Q.GLYPH_LADDER`'s own
        completeness term (`C4`) being destroyed by its neighbour."""
        v = self._rung(step=10.0, heads_outward=[2.0])
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "ledger_line")

    def test_an_inner_rung_of_a_FIVE_rung_run_is_KEPT_past_the_tolerance(
            self):
        """⚠️⚠️ THE OUTWARD CLAUSE, MEASURED. A head farther OUT than the
        rung is its note at any distance — the rung lies between the staff
        and the note, the only place an engraver prints one. Of the rungs
        3.4g kept past 2.75 spaces, 5 / 43 / 51 (p1-p4 / Litolff /
        Breitkopf) have exactly this shape at 2.9-4.6 spaces; a symmetric
        tolerance alone would refuse every one."""
        for step in (10.0, -2.0):
            with self.subTest(step=step):
                v = self._rung(step=step, heads_outward=[4.0])
                self.assertIs(v.value, False)
                self.assertEqual(v.reason, "ledger_line")
                self.assertAlmostEqual(v.detail["head_outward_spaces"], 4.0,
                                       places=3)

    def test_the_same_head_STAFFWARD_past_the_tolerance_is_refused(self):
        """THE NEGATIVE CONTROL for the outward clause, at the same
        distance: heads only between the rung and the staff are what a beam
        below its heads looks like (Sean's crop 8), not a ladder."""
        for step in (10.0, -2.0):
            with self.subTest(step=step):
                v = self._rung(step=step, heads_outward=[-4.0])
                self.assertIs(v.value, True)
                self.assertEqual(v.reason, "no_head_on_the_rung")

    def test_the_head_tolerance_is_the_measured_p95(self):
        """⚠️ DERIVED, NOT CHOSEN — p95 of the kept rungs' head distance is
        2.67 / 2.67 / 1.885 spaces on the three records; the constant is the
        smallest quarter-space value covering all three.

        ⚠️ IT IS NOT BOUNDED BY SEAN'S CROP 8 (a beam, 2.975 spaces from its
        heads) and must not be: a threshold fitted between one crop and one
        percentile is a threshold tuned on one crop. Crop 8 is refused by
        `tall_not_a_rung`, which does not read this constant at all."""
        p95s = (2.67, 2.67, 1.885)
        self.assertGreaterEqual(FP.HEAD_NEAR_TOL_SPACES, max(p95s))
        self.assertLess(FP.HEAD_NEAR_TOL_SPACES - 0.25, max(p95s))

    def test_the_distance_and_the_count_are_both_recorded(self):
        v = self._rung(step=-2.0, head_dist_spaces=1.25)
        self.assertEqual(v.detail["heads_x_overlapping"], 1)
        self.assertAlmostEqual(v.detail["head_distance_spaces"], 1.25,
                               places=3)

    # ── tall_not_a_rung — RE-MEASURED in 3.4g-2 ─────────────────────────────

    def test_a_tall_box_is_refused(self):
        v = self._rung(step=-2.0, h_c=0.6 * SPACING_CANONICAL)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "tall_not_a_rung")

    def test_a_tall_box_with_a_head_on_it_is_KEPT(self):
        """⚠️⚠️ SEAN'S CROP 9 (`glyph/4/1/2/5/14`), THE ONE REAL RUNG THE
        OLD RULES REFUSED. Measured: height 0.68 spaces — past the 0.5 floor
        — with a notehead 0.085 spaces from its centre and eight heads
        x-overlapping it. On a MERGING plate the rung's box has swallowed
        the head's ink, so the height is measuring the head. A rung with its
        head on it is not a barline whatever it measures."""
        v = self._rung(step=12.58, h_c=0.68 * SPACING_CANONICAL,
                       heads_outward=[-0.085, 0.505])
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "ledger_line")

    def test_a_tall_box_with_its_heads_far_below_is_still_refused(self):
        """SEAN'S CROP 8 — *"too thick, it is a beam for 3 eighth notes"*.
        Measured: height 0.62 spaces, every x-overlapping head STAFFWARD of
        it, the nearest 2.975 spaces away — no head stands ON the box."""
        v = self._rung(step=-6.04, h_c=0.62 * SPACING_CANONICAL,
                       heads_outward=[-2.975])
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "tall_not_a_rung")

    def test_a_rung_thick_box_is_KEPT(self):
        """THE POSITIVE CONTROL for the height rule: the measured population
        sits at p50 0.28 and p95 0.37 spaces, well under the floor."""
        v = self._rung(step=-2.0, h_c=0.37 * SPACING_CANONICAL,
                       head_dist_spaces=0.0)
        self.assertIs(v.value, False)

    def test_the_height_floor_is_past_the_measured_population(self):
        self.assertGreaterEqual(FP.TALL_MIN_HEIGHT_SPACES, 0.42)

    def test_a_tall_box_a_head_is_NEAR_but_not_ON_is_still_tall(self):
        """⚠️ "ON" IS AN INTERSECTION, NOT THE HEAD TOLERANCE. A head 1.5
        spaces staffward of a tall box is near enough for the head rule and
        does not stand on the box, so the height rule still speaks — which
        is what separates a beam from a rung its head has swallowed."""
        v = self._rung(step=-6.0, h_c=0.6 * SPACING_CANONICAL,
                       heads_outward=[-1.5])
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "tall_not_a_rung")
        self.assertIs(v.detail["head_on_the_box"], False)

    def test_tall_runs_before_the_head_rule_or_it_could_never_fire(self):
        """⚠️ THE ORDER IS LOAD-BEARING AND THIS IS WHY. `tall_not_a_rung`
        now requires that no head stands on the box; a tall box with no head
        would be condemned by `no_head_on_the_rung` first if that rule ran
        earlier, and the height rule would be DEAD — a reason declared and
        unreachable, which is what `brakes.vocabulary_gap` exists to catch.
        The fixture is the one that separates the two orders."""
        v = self._rung(step=-2.0, h_c=0.6 * SPACING_CANONICAL)
        self.assertEqual(v.reason, "tall_not_a_rung")

    # ── not_at_a_rung_step — MEASURED AND HELD BACK ─────────────────────────

    def test_a_box_at_half_a_space_beyond_the_band_is_NOT_refused(self):
        """⚠️ `RUNG_STEP_SHIPS = False`. The offset-from-the-rung measurement
        is very nearly UNIFORM on Litolff, so the rule would refuse on noise;
        the signal is recorded and sets no value."""
        v = self._rung(step=-3.0, head_dist_spaces=0.0)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "ledger_line")

    def test_the_held_back_signal_is_still_on_the_record(self):
        v = self._rung(step=-3.0, head_dist_spaces=0.0)
        sig = v.detail["rung_step_signal"]
        self.assertIs(sig["would_fire"], True)
        self.assertIs(sig["ships"], False)
        self.assertAlmostEqual(sig["offset_spaces"], 0.5, places=3)

    def test_the_signal_is_recorded_even_where_another_rule_condemns_it(self):
        """⚠️ COMPUTED BEFORE ANY SHIPPED RULE RETURNS, so the held-back
        measurement survives a box Sean's conventions already refuse."""
        sig = self._rung(step=-3.0).detail["rung_step_signal"]
        self.assertIs(sig["ships"], False)
        self.assertAlmostEqual(sig["offset_spaces"], 0.5, places=3)

    def test_the_signal_on_a_real_rung_would_not_fire(self):
        sig = self._rung(step=-2.0,
                         head_dist_spaces=0.0).detail["rung_step_signal"]
        self.assertIs(sig["would_fire"], False)

    def test_the_rule_is_not_in_the_declared_vocabulary(self):
        """⚠️ A HELD-BACK RULE DECLARES NO REASON. A reason a `Ruling` site
        can never return is exactly what `brakes.vocabulary_gap` exists to
        catch, so the held-back rule must not appear in `reasons`."""
        self.assertNotIn(
            "not_at_a_rung_step",
            adjudicate.REGISTRY[Q.LEDGER_IS_NOT_A_LEDGER].reasons)
        self.assertFalse(FP.RUNG_STEP_SHIPS)

    # ── declined, never defaulted ───────────────────────────────────────────

    def test_no_page_frame_abstains(self):
        v = self._rung(step=-2.0, page_box=False)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, ABSTAIN.NO_STAFF_GEOMETRY)

    def test_no_staff_lines_abstains(self):
        v = self._rung(step=-2.0, geometry=False)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, ABSTAIN.NO_STAFF_GEOMETRY)

    def test_a_human_outranks_the_geometry(self):
        """A box the geometry would KEEP, and a human says is nothing."""
        log = Log()
        _staff_geometry(log)
        _box(log, 9, "noteheadBlackOnLine", quantity=Q.NOTEHEAD_CLASS,
             page_box=_page_box_at_step(-2.0), w_c=26.0, h_c=18.0,
             x_c=LEDGER_X_CANONICAL, y_c=LEDGER_Y_CANONICAL)
        g = _box(log, 0, "ledgerLine", x_c=LEDGER_X_CANONICAL,
                 y_c=LEDGER_Y_CANONICAL, page_box=_page_box_at_step(-2.0))
        _human(log, g, "not_a_symbol")
        _run(log, Q.LEDGER_IS_NOT_A_LEDGER)
        v = log.verdict(Q.LEDGER_IS_NOT_A_LEDGER, g)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "human_not_a_symbol")

    def test_a_human_is_read_even_with_no_geometry_at_all(self):
        """⚠️ THE HUMAN IS OUTSIDE THE GEOMETRY GATE. He looked at the print;
        putting his reading after the gate would throw it away on exactly the
        cells where the machine can say least."""
        log = Log()
        g = _box(log, 0, "ledgerLine", page_box=None)
        _human(log, g, "not_a_symbol")
        _run(log, Q.LEDGER_IS_NOT_A_LEDGER)
        self.assertIs(log.verdict(Q.LEDGER_IS_NOT_A_LEDGER, g).value, True)


#: ⚠️⚠️ SEAN'S THIRTEEN CROPS, AS FIXTURES — ROADMAP 3.4g-2.
#:
#: Each row is one crop of `benchmarks/omr-family-refusals-2026-09/out/print/`
#: that Sean adjudicated against the print on 2026-09-24
#: (`ADJUDICATION-sean-2026-09-24.json`), carrying the geometry MEASURED off
#: `beethoven5-p1-p4.record.json` by `probe/ledger_heads.py` — never numbers
#: read off the picture by eye.
#:
#: `(n, subject, is a ledger line?, staff step, height in spaces, the
#:  x-overlapping heads as SIGNED distances in spaces, expected reason)`
#:
#: The heads column is the probe's two measured numbers — the nearest head's
#: distance and the largest OUTWARD distance (`head_outward_max`, + farther
#: from the staff than the rung) — placed on their measured sides: a nearest
#: head whose side the probe does not pin is put STAFFWARD, the side only the
#: tolerance can keep. ⚠️ Inside the band OUT is undefined and the sign is
#: not a measurement; those boxes are refused on position before a head is
#: consulted.
#:
#: ⚠️ THE EXPECTED REASON IS NOT THE ASSERTION. The assertion is that the
#: decision's REFUSAL agrees with SEAN — the reason is carried so a change of
#: reason shows up as a change and not as a silent re-attribution.
SEANS_CROPS = (
    (1, "glyph/4/0/9/1/7", False, 4.960, 0.240, (2.060,), "inside_the_staff"),
    (2, "glyph/4/0/9/5/14", False, 1.490, 0.210, (4.205,),
     "inside_the_staff"),
    (3, "glyph/4/1/7/5/21", True, -6.720, 0.280, (-0.515,), "ledger_line"),
    (4, "glyph/1/0/2/15/3", False, 5.550, 0.230, (0.245,), "inside_the_staff"),
    (5, "glyph/2/0/10/14/10", False, 2.140, 0.360, (1.050,),
     "inside_the_staff"),
    (6, "glyph/3/0/2/14/1", False, 5.650, 0.190, (), "inside_the_staff"),
    (7, "glyph/3/0/5/13/5", False, 0.150, 0.350, (2.725,), "inside_the_staff"),
    (8, "glyph/2/0/1/4/12", False, -6.040, 0.620, (-2.975,),
     "tall_not_a_rung"),
    (9, "glyph/4/1/2/5/14", True, 12.580, 0.680, (-0.085, 0.505),
     "ledger_line"),
    (10, "glyph/4/1/9/11/17", False, 4.320, 0.520, (0.415,),
     "inside_the_staff"),
    (11, "glyph/3/0/7/6/14", True, -1.850, 0.350, (1.210,), "ledger_line"),
    (12, "glyph/3/0/7/7/8", True, -1.900, 0.400, (1.125,), "ledger_line"),
    (13, "glyph/4/1/2/3/19", True, 10.220, 0.340, (-0.585, 1.145),
     "ledger_line"),
)


class TestSeansThirteenCrops(unittest.TestCase):
    """⚠️⚠️ THE GATE OF ROADMAP 3.4g-2: the rule agrees with the man.

    Thirteen `ledgerLine` boxes, cut from the plate at the gather's own DPI
    behind a frame control, shown to Sean in chat and answered one by one.
    Under the rules of 3.4g he was right and the machine was wrong twice —
    crop 9 (a real rung refused `tall_not_a_rung`) and crop 3 (a real rung
    the held-back `not_at_a_rung_step` would have refused, which is why it
    stayed held back). Both must now be KEPT, and none of the eleven he
    called *nothing* may be.

    ⚠️ A REFUSAL BATTERY PASSES BY REFUSING EVERYTHING, so the five he
    called REAL are the positive control and they are inside this same table
    rather than in a test of their own.
    """

    def _crop(self, row):
        _n, _subject, _real, step, h_spaces, heads, _reason = row
        return _ledger_verdict(
            step=step, h_c=h_spaces * SPACING_CANONICAL,
            heads_outward=list(heads))

    def test_every_crop_agrees_with_sean(self):
        for row in SEANS_CROPS:
            n, subject, real, _s, _h, _d, _r = row
            with self.subTest(crop=n, subject=subject):
                v = self._crop(row)
                self.assertEqual(v.outcome, Outcome.DECIDED)
                # `value is True` means REFUSED — *this is not a ledger line*
                self.assertIs(v.value, not real)

    def test_every_crop_gets_the_reason_this_lane_measured(self):
        for row in SEANS_CROPS:
            n, subject, _real, _s, _h, _d, reason = row
            with self.subTest(crop=n, subject=subject):
                self.assertEqual(self._crop(row).reason, reason)

    def test_the_two_real_rungs_the_old_rules_refused_are_KEPT(self):
        """Crop 9 (`tall_not_a_rung`, shipped) and crop 3 (the held-back
        rung-step rule). ⚠️ NAMED rather than counted, so a table edited to
        make this pass reads as the edit it is."""
        for n in (3, 9):
            row = next(r for r in SEANS_CROPS if r[0] == n)
            with self.subTest(crop=n, subject=row[1]):
                v = self._crop(row)
                self.assertIs(v.value, False)
                self.assertEqual(v.reason, "ledger_line")

    def test_crop_6_is_condemned_by_BOTH_conventions_and_the_record_says_so(
            self):
        """⚠️ SEAN GAVE A WHOLE-REST BAR AS HIS REASON for crops 4, 6 and 7
        (*"there are never ledger lines when there are no notes in the
        measure"*), and all three are ALSO inside the band. The decision
        records ONE reason — position first, because the head tolerance was
        measured OUTSIDE the band — and the head facts on every box, so the
        second convention's verdict is on the row and not lost. Crop 6 has
        no head in its cell at all."""
        v = self._crop(next(r for r in SEANS_CROPS if r[0] == 6))
        self.assertEqual(v.reason, "inside_the_staff")
        self.assertEqual(v.detail["heads_x_overlapping"], 0)
        self.assertIsNone(v.detail["head_distance_spaces"])

    def test_the_positive_control_five_he_called_real(self):
        real = [r for r in SEANS_CROPS if r[2]]
        self.assertEqual(len(real), 5)          # reach, before accuracy
        for row in real:
            with self.subTest(crop=row[0]):
                self.assertIs(self._crop(row).value, False)

    def test_the_table_is_the_adjudication_file(self):
        """⚠️ THE TABLE ABOVE IS A COPY AND THIS IS THE JOIN THAT KEEPS IT
        HONEST. `ADJUDICATION-sean-2026-09-24.json` is the record of what he
        said; if it is on disk, every verdict in it must appear here with
        the same answer. The file is a benchmark artefact and a checkout
        without it SKIPS rather than passes silently."""
        import json
        import os
        import re
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))))),
            "benchmarks", "omr-family-refusals-2026-09", "out", "print",
            "ADJUDICATION-sean-2026-09-24.json")
        if not os.path.exists(path):        # pragma: no cover - artefact
            self.skipTest("the adjudication file is not in this checkout")
        said = json.load(open(path, encoding="utf-8"))["verdicts"]
        self.assertEqual(len(said), len(SEANS_CROPS))
        mine = {r[0]: (r[1], r[2]) for r in SEANS_CROPS}
        for v in said:
            m = re.match(r".*-p(\d+)-s(\d+)-st(\d+)-c(\d+)-g(\d+)-",
                         v["crop"])
            subject = "glyph/" + "/".join(m.groups())
            self.assertEqual(mine[v["n"]], (subject, v["is_ledger_line"]))


class TestARefusedRungIsNotCountedInTheLadder(unittest.TestCase):
    """ROADMAP 3.4g item 3 — the one ladder where the join EXISTS.

    ⚠️ GATHER's own `Q.GLYPH_LADDER` records `expected`/`found` as COUNTS and
    names no rung glyph, so no ADJUDICATE refusal can reach it. ADJUDICATE's
    own search reads the rung GLYPHS, and that is what this pins.
    """

    def _signal(self, *, refuse_the_rung):
        log = Log()
        _staff_geometry(log)
        log.observe(CELL, Q.CELL_BOX, [400.0, 900.0, 800.0, 1200.0],
                    reader=READERS.GEOMETRY, frame="cell:0")
        # a low-confidence head one space below the staff, and its rung
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.GLYPH_BOX,
                    ("noteheadBlackOnLine", 200.0, 300.0, 140.0, 100.0),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.5,
                    category="notehead",
                    bbox_page_px=_page_box_at_step(-2.0))
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.5)
        log.observe(g, Q.GLYPH_CONF, 0.5, reader=READERS.DETECTOR,
                    frame="cell:0", score=0.5)
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, 10.0,
                    reader=READERS.GEOMETRY, frame="cell:0")
        rung = R.glyph(0, 0, 0, 0, 1)
        log.observe(rung, Q.GLYPH_BOX,
                    ("ledgerLine", 190.0, 340.0, 160.0, 20.0),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.6,
                    category="ledger", bbox_page_px=_page_box_at_step(-2.0))
        if refuse_the_rung:
            _human(log, rung, "not_a_symbol")
        _run(log, Q.LEDGER_IS_NOT_A_LEDGER, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD)
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)
        return log, v.detail.get("unladdered_signal")

    def test_a_kept_rung_is_counted(self):
        """THE POSITIVE CONTROL: without it a zero would mean only that the
        ladder search never found anything in this fixture."""
        _log, sig = self._signal(refuse_the_rung=False)
        self.assertIsNotNone(sig)
        self.assertEqual(sig["ledger_found"], 1)

    def test_a_refused_rung_is_not_counted(self):
        _log, sig = self._signal(refuse_the_rung=True)
        self.assertEqual(sig["ledger_found"], 0)

    def test_gather_s_own_ladder_row_NAMES_NO_RUNG_GLYPH(self):
        """⚠️⚠️ THE FINDING, PINNED BEHAVIOURALLY. `gather._observe_ladder`
        is called here for real and the row it files is read: it carries
        `expected` and `found` as COUNTS and NOTHING that names the ledger
        glyphs it matched — so no ADJUDICATE refusal can discount a
        GATHER-counted rung, and `glyph_owner`'s ladder tier is out of this
        lane's reach without a GATHER change. The day that row names its
        rungs, this goes red and the discount can move there too.
        """
        from tools.omr.staged import gather
        log = Log()
        # a head one space below the bottom line, with a rung under it
        box = _page_box_at_step(-2.0)
        rungs = {(0, 0): [(box[0] - 5.0, box[2] + 5.0,
                           (box[1] + box[3]) / 2.0)]}
        gather._observe_ladder(log, R.glyph(0, 0, 0, 0, 0), box,
                               STAFF.to_key(), LINE_YS, SPACING_PAGE, rungs)
        rows = [r for r in log.all_rows() if r.quantity == Q.GLYPH_LADDER]
        self.assertEqual(len(rows), 1)          # the positive control
        self.assertEqual(rows[0].detail.get("found"), 1)
        named = [k for k, v in (rows[0].detail or {}).items()
                 if isinstance(v, str) and v.startswith("glyph/")]
        self.assertEqual(named, [])


# ─────────────────────────────────────────────────────────────────────────────
# the consumers
# ─────────────────────────────────────────────────────────────────────────────

class TestTheExportConsumers(unittest.TestCase):

    def _rest_record(self, *, refuse):
        log = Log()
        _staff_geometry(log)
        g = _box(log, 0, "restQuarter", quantity=Q.REST,
                 page_box=_page_box_at_step(4.0))
        if refuse:
            _human(log, g, "not_a_symbol")
        _run(log, Q.REST_IS_NOT_A_REST)
        return SX.Record({"record": log.to_json()}), g

    def test_a_refused_rest_is_dropped_and_NAMED_by_the_exporter(self):
        """⚠️ `_place_notes` IS CALLED, not read. Its `runs` map is empty, so
        every rest that survives the refusal falls through to a LATER
        reason — which is exactly what makes the two cases tell apart."""
        rec, _g = self._rest_record(refuse=True)
        dropped = SX._place_notes(rec, {})
        self.assertEqual(dropped.get("not_a_rest:human_not_a_symbol"), 1)

    def test_a_rest_with_no_human_row_is_NOT_dropped_as_not_a_rest(self):
        """THE POSITIVE CONTROL: without it the assertion above would pass on
        an exporter that refused every rest it saw."""
        rec, _g = self._rest_record(refuse=False)
        dropped = SX._place_notes(rec, {})
        self.assertEqual(
            [k for k in dropped if k.startswith("not_a_rest:")], [])

    def test_the_family_census_balances(self):
        rec, _g = self._rest_record(refuse=True)
        block = SX._family_refusals(rec)
        self.assertEqual(sorted(block), sorted(FP.FAMILY_REFUSALS))
        for quantity, row in block.items():
            with self.subTest(quantity):
                self.assertTrue(row["balanced"])
        self.assertEqual(block[Q.REST_IS_NOT_A_REST]["refused"],
                         {"human_not_a_symbol": 1})

    def test_the_census_counts_a_kept_box_as_kept(self):
        """THE POSITIVE CONTROL for the census: a partition that only ever
        reported refusals could not tell an empty page from a clean one."""
        rec, _g = self._rest_record(refuse=False)
        row = SX._family_refusals(rec)[Q.REST_IS_NOT_A_REST]
        self.assertEqual(row["refused_total"], 0)
        self.assertEqual(row["kept"], 1)

    def test_the_census_reaches_the_coverage_report(self):
        rec, _g = self._rest_record(refuse=True)
        report = SX.coverage({"record": rec.result["record"]})
        self.assertIn("family_refusals", report)
        self.assertEqual(
            report["family_refusals"][Q.REST_IS_NOT_A_REST]["refused_total"],
            1)


class TestTheDynamicConsumer(unittest.TestCase):
    """A refused letter must not be spelled into a word."""

    def _word(self, *, refuse_the_second):
        log = Log()
        _staff_geometry(log)
        for i, x in enumerate((500.0, 530.0)):
            g = R.glyph(0, 0, 0, 0, i)
            log.observe(g, Q.GLYPH_BOX, ("dynamicF", 200.0 + i * 30, 300.0,
                                         26.0, 30.0),
                        reader=READERS.DETECTOR, frame="cell:0", score=0.8,
                        category="dynamic",
                        bbox_page_px=[x, 1100.0, x + 26.0, 1130.0])
            log.observe(g, Q.DYNAMIC_LETTER, "dynamicF",
                        reader=READERS.DETECTOR, frame="staff:0", score=0.8,
                        letter="f", bbox_page_px=[x, 1100.0, x + 26.0, 1130.0])
            if refuse_the_second and i == 1:
                _human(log, g, "not_a_symbol")
        _run(log, Q.DYNAMIC_IS_NOT_A_DYNAMIC, Q.DYNAMIC)
        return log.verdict(Q.DYNAMIC, CELL)

    def test_two_letters_spell_ff(self):
        """THE POSITIVE CONTROL, and it is the one that matters here: if the
        pair did not spell `ff` the refusal test below would pass on a
        fixture that never assembled a word at all."""
        self.assertEqual(self._word(refuse_the_second=False).value, ["ff"])

    def test_a_refused_letter_leaves_f(self):
        v = self._word(refuse_the_second=True)
        self.assertEqual(v.value, ["f"])
        self.assertEqual(v.detail["letters_refused_as_not_a_dynamic"], 1)

    def test_the_refusal_runs_before_the_spelling(self):
        order = adjudicate.ORDER
        self.assertLess(order.index(Q.DYNAMIC_IS_NOT_A_DYNAMIC),
                        order.index(Q.DYNAMIC))

    def test_the_spelling_declares_the_refusal(self):
        self.assertIn(Q.DYNAMIC_IS_NOT_A_DYNAMIC,
                      adjudicate.REGISTRY[Q.DYNAMIC].wants)


# ─────────────────────────────────────────────────────────────────────────────
# the sidecar's new answer
# ─────────────────────────────────────────────────────────────────────────────

class TestTheSidecarLearnsOtherStaff(unittest.TestCase):

    def _record_with_one_box(self):
        log = Log()
        _staff_geometry(log)
        _box(log, 0, "accidentalFlat", page_box=_page_box_at_step(4.0))
        log.freeze()
        return log.to_json()

    def _ingest(self, staff_value):
        rec = self._record_with_one_box()
        sidecar = {"record": "x", "staff": STAFF.to_key(), "actions": [
            {"id": "act-0001", "stage": "gather", "kind": "own_box",
             "glyph": R.glyph(0, 0, 0, 0, 0).to_key(),
             "staff": staff_value}]}
        return HE.ingest(rec, sidecar, sidecar_path="t.json")

    def test_other_is_ingested_as_owner_other(self):
        ing = self._ingest(HE.OWNER_OTHER)
        self.assertIsNone(ing.actions[0].refused)
        rows = [o for o in ing.record["observations"]
                if o["quantity"] == Q.HUMAN_BOX_VERDICT]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["value"], f"owner:{HE.OWNER_OTHER}")
        self.assertIsNone(rows[0]["detail"]["owner_named"])
        self.assertNotIn("twin_on_the_named_staff", rows[0]["detail"])

    def test_a_named_staff_still_ingests_as_before(self):
        """THE POSITIVE CONTROL: the addition must not swallow the old form."""
        ing = self._ingest(R.staff(0, 0, 1).to_key())
        self.assertIsNone(ing.actions[0].refused)
        rows = [o for o in ing.record["observations"]
                if o["quantity"] == Q.HUMAN_BOX_VERDICT]
        self.assertEqual(rows[0]["value"], "owner:staff/0/0/1")
        self.assertEqual(rows[0]["detail"]["owner_named"], "staff/0/0/1")

    def test_a_part_name_is_still_refused(self):
        """⚠️ `other` is the ONE non-subject that is admitted. Every other
        one must still be refused, or the addition would have opened the
        door the original check closed."""
        ing = self._ingest("Violin II")
        self.assertIsNotNone(ing.actions[0].refused)

    def test_the_label_table_offers_it(self):
        vals = [e["value"] for e in HE.HUMAN_BOX_LABELS]
        self.assertIn(f"owner:{HE.OWNER_OTHER}", vals)
        entry = next(e for e in HE.HUMAN_BOX_LABELS
                     if e["value"] == f"owner:{HE.OWNER_OTHER}")
        self.assertEqual(entry["kind"], "own_box")
        self.assertEqual(entry["keys"], "o")

    def test_the_parser_reads_it(self):
        self.assertEqual(HE.human_says(f"owner:{HE.OWNER_OTHER}"),
                         ("owner", HE.OWNER_OTHER))


# ─────────────────────────────────────────────────────────────────────────────
# ONE NAMED TEST PER FAMILY
#
# ⚠️ NOT A DUPLICATE OF THE PARAMETRISED CLASS ABOVE, AND `staged.health` IS
# WHY. That tool scans each test FUNCTION's AST for the `Q.` names it
# mentions, so a loop over a module-level table covers seven decisions and
# names none of them — every one reads as `NO staged test names it at all`,
# which is a derived check silently disabled by a code-style choice. The
# parametrised class is the sweep; these are the named cells, each asserting
# what the decision DECIDES, what it RECORDS and which REASON it gives.
# ─────────────────────────────────────────────────────────────────────────────

class TestEachFamilyByName(unittest.TestCase):

    def _pair(self, quantity, cls, extra):
        """`(the refused verdict, the kept control)` for one family."""
        out = []
        for value in (f"owner:{HE.OWNER_OTHER}", None):
            log = Log()
            _staff_geometry(log)
            # ⚠️ THE HEAD IS HERE FOR THE LEDGER'S SAKE (3.4g-2): without one
            # the kept CONTROL would be refused `no_head_on_the_rung` and the
            # positive control in this family would be testing the wrong rule.
            _box(log, 9, "noteheadBlackOnLine", quantity=Q.NOTEHEAD_CLASS,
                 page_box=_page_box_at_step(-2.0), w_c=26.0, h_c=18.0,
                 x_c=LEDGER_X_CANONICAL, y_c=LEDGER_Y_CANONICAL)
            g = _box(log, 0, cls, quantity=extra,
                     x_c=LEDGER_X_CANONICAL, y_c=LEDGER_Y_CANONICAL,
                     page_box=_page_box_at_step(-2.0))
            if value is not None:
                _human(log, g, value)
            _run(log, quantity)
            out.append(log.verdict(quantity, g))
        return out[0], out[1]

    def test_ledger_is_not_a_ledger(self):
        refused, kept = self._pair(Q.LEDGER_IS_NOT_A_LEDGER, "ledgerLine", None)
        self.assertEqual(refused.outcome, Outcome.DECIDED)
        self.assertIs(refused.value, True)
        self.assertEqual(refused.reason, "human_other_staff")
        # ⚠️ WHAT IT RECORDS, not merely what it decided.
        self.assertEqual(refused.detail["class"], "ledgerLine")
        self.assertEqual(refused.detail["human_reader"], READERS.SEAN)
        self.assertEqual(len(refused.used), 1)
        self.assertIn(refused.used[0], refused.basis)
        # the positive control, in the same class
        self.assertEqual(kept.outcome, Outcome.DECIDED)
        self.assertIs(kept.value, False)
        self.assertEqual(kept.reason, "ledger_line")
        self.assertEqual(kept.detail["class"], "ledgerLine")

    def test_accidental_is_not_an_accidental(self):
        refused, kept = self._pair(Q.ACCIDENTAL_IS_NOT_AN_ACCIDENTAL, "accidentalFlat", None)
        self.assertEqual(refused.outcome, Outcome.DECIDED)
        self.assertIs(refused.value, True)
        self.assertEqual(refused.reason, "human_other_staff")
        # ⚠️ WHAT IT RECORDS, not merely what it decided.
        self.assertEqual(refused.detail["class"], "accidentalFlat")
        self.assertEqual(refused.detail["human_reader"], READERS.SEAN)
        self.assertEqual(len(refused.used), 1)
        self.assertIn(refused.used[0], refused.basis)
        # the positive control, in the same class
        self.assertEqual(kept.outcome, Outcome.DECIDED)
        self.assertIs(kept.value, False)
        self.assertEqual(kept.reason, "accidental")
        self.assertEqual(kept.detail["class"], "accidentalFlat")

    def test_rest_is_not_a_rest(self):
        refused, kept = self._pair(Q.REST_IS_NOT_A_REST, "restQuarter", Q.REST)
        self.assertEqual(refused.outcome, Outcome.DECIDED)
        self.assertIs(refused.value, True)
        self.assertEqual(refused.reason, "human_other_staff")
        # ⚠️ WHAT IT RECORDS, not merely what it decided.
        self.assertEqual(refused.detail["class"], "restQuarter")
        self.assertEqual(refused.detail["human_reader"], READERS.SEAN)
        self.assertEqual(len(refused.used), 1)
        self.assertIn(refused.used[0], refused.basis)
        # the positive control, in the same class
        self.assertEqual(kept.outcome, Outcome.DECIDED)
        self.assertIs(kept.value, False)
        self.assertEqual(kept.reason, "rest")
        self.assertEqual(kept.detail["class"], "restQuarter")

    def test_arpeggiato_is_not_an_arpeggiato(self):
        refused, kept = self._pair(Q.ARPEGGIATO_IS_NOT_AN_ARPEGGIATO, "arpeggiato", None)
        self.assertEqual(refused.outcome, Outcome.DECIDED)
        self.assertIs(refused.value, True)
        self.assertEqual(refused.reason, "human_other_staff")
        # ⚠️ WHAT IT RECORDS, not merely what it decided.
        self.assertEqual(refused.detail["class"], "arpeggiato")
        self.assertEqual(refused.detail["human_reader"], READERS.SEAN)
        self.assertEqual(len(refused.used), 1)
        self.assertIn(refused.used[0], refused.basis)
        # the positive control, in the same class
        self.assertEqual(kept.outcome, Outcome.DECIDED)
        self.assertIs(kept.value, False)
        self.assertEqual(kept.reason, "arpeggiato")
        self.assertEqual(kept.detail["class"], "arpeggiato")

    def test_arc_is_not_an_arc(self):
        refused, kept = self._pair(Q.ARC_IS_NOT_AN_ARC, "slur", Q.ARC_BOX)
        self.assertEqual(refused.outcome, Outcome.DECIDED)
        self.assertIs(refused.value, True)
        self.assertEqual(refused.reason, "human_other_staff")
        # ⚠️ WHAT IT RECORDS, not merely what it decided.
        self.assertEqual(refused.detail["class"], "slur")
        self.assertEqual(refused.detail["human_reader"], READERS.SEAN)
        self.assertEqual(len(refused.used), 1)
        self.assertIn(refused.used[0], refused.basis)
        # the positive control, in the same class
        self.assertEqual(kept.outcome, Outcome.DECIDED)
        self.assertIs(kept.value, False)
        self.assertEqual(kept.reason, "arc")
        self.assertEqual(kept.detail["class"], "slur")

    def test_dynamic_is_not_a_dynamic(self):
        refused, kept = self._pair(Q.DYNAMIC_IS_NOT_A_DYNAMIC, "dynamicF", Q.DYNAMIC_LETTER)
        self.assertEqual(refused.outcome, Outcome.DECIDED)
        self.assertIs(refused.value, True)
        self.assertEqual(refused.reason, "human_other_staff")
        # ⚠️ WHAT IT RECORDS, not merely what it decided.
        self.assertEqual(refused.detail["class"], "dynamicF")
        self.assertEqual(refused.detail["human_reader"], READERS.SEAN)
        self.assertEqual(len(refused.used), 1)
        self.assertIn(refused.used[0], refused.basis)
        # the positive control, in the same class
        self.assertEqual(kept.outcome, Outcome.DECIDED)
        self.assertIs(kept.value, False)
        self.assertEqual(kept.reason, "dynamic")
        self.assertEqual(kept.detail["class"], "dynamicF")

    def test_articulation_is_not_an_articulation(self):
        refused, kept = self._pair(Q.ARTICULATION_IS_NOT_AN_ARTICULATION, "articStaccatoAbove", Q.ARTICULATION_MARK)
        self.assertEqual(refused.outcome, Outcome.DECIDED)
        self.assertIs(refused.value, True)
        self.assertEqual(refused.reason, "human_other_staff")
        # ⚠️ WHAT IT RECORDS, not merely what it decided.
        self.assertEqual(refused.detail["class"], "articStaccatoAbove")
        self.assertEqual(refused.detail["human_reader"], READERS.SEAN)
        self.assertEqual(len(refused.used), 1)
        self.assertIn(refused.used[0], refused.basis)
        # the positive control, in the same class
        self.assertEqual(kept.outcome, Outcome.DECIDED)
        self.assertIs(kept.value, False)
        self.assertEqual(kept.reason, "articulation")
        self.assertEqual(kept.detail["class"], "articStaccatoAbove")

    def test_only_the_ledger_can_abstain_and_it_does(self):
        """⚠️ THE ASYMMETRY, STATED AS A TEST. `Q.LEDGER_IS_NOT_A_LEDGER` is
        the one family with a geometric rule, so it is the one that can lack
        the geometry to run it (`ABSTAIN.NO_STAFF_GEOMETRY`). The other six
        refuse on a human witness and nothing else, and a human who left no
        row is the ABSENCE OF A REFUSAL — a fact about the box — not a
        measurement that went missing. Each of the six is asserted here to
        DECIDE rather than abstain, and the reason words below are what
        `Q.ARC_IS_NOT_AN_ARC`, `Q.DYNAMIC_IS_NOT_A_DYNAMIC`,
        `Q.REST_IS_NOT_A_REST`, `Q.ACCIDENTAL_IS_NOT_AN_ACCIDENTAL`,
        `Q.ARPEGGIATO_IS_NOT_AN_ARPEGGIATO` and
        `Q.ARTICULATION_IS_NOT_AN_ARTICULATION` say instead.
        """
        log = Log()
        g = _box(log, 0, "ledgerLine", page_box=None)
        _run(log, Q.LEDGER_IS_NOT_A_LEDGER)
        v = log.verdict(Q.LEDGER_IS_NOT_A_LEDGER, g)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, ABSTAIN.NO_STAFF_GEOMETRY)
        for quantity, cls, word, extra in FAMILIES:
            if quantity == Q.LEDGER_IS_NOT_A_LEDGER:
                continue
            with self.subTest(quantity):
                log = Log()
                g = _box(log, 0, cls, quantity=extra, page_box=None)
                _run(log, quantity)
                other = log.verdict(quantity, g)
                self.assertEqual(other.outcome, Outcome.DECIDED)
                self.assertEqual(other.reason, word)


if __name__ == "__main__":       # pragma: no cover
    unittest.main()
