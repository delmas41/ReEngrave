"""Roadmap 2.11b -- `adjudicate_clef` reads `Q.CLEF_POSITION` and discounts a
detector clef box that sits OFF the staff.

2.11 found the case (`benchmarks/omr-clef-geometry-2026-09/FINDINGS.md`
Sec.4c): on Brahms 1 p.6 `staff/6/1/3` a single `clefG` detector box at
`Q.CLEF_POSITION` 19.36 -- about 5.7 staff spaces BELOW the bottom line, a
neighbouring staff's clef bleeding into this staff's padded measure cell --
decided `treble` UNOPPOSED. `Q.CLEF_POSITION` was gathered, was on the
record, and `adjudicate_clef` never read it to discount the box: "the value
existed and nothing read it."

`_detector_terms` already computed `_stands_on_this_staff` for the
`stands_on_this_staff` BONUS term (roadmap A-CLEF-8), so the position was
already read -- just never used to withhold the base term. This change
adds exactly that: a detector clef box whose OWN position is measurably off
its family's on-staff band (`ON_STAFF_MIN_STEPS`..`ON_STAFF_MAX_STEPS`,
freshly re-measured per family across the three acceptance documents in
`clef.py`'s own module docstring, roadmap 2.11b) is DISCOUNTED -- it stays
in `basis` (still read), it is never `used`, and it is named
`clef_box_off_the_staff` in `detail` so a trace shows why. If it was the
only witness, the staff ABSTAINS `no_candidates` and the existing gap
machinery (roadmap 2.10's `clef_from_other_systems`, then
`infer.fill_clef_gap`) takes over -- never a default to treble (CLAUDE.md
rule 8).

⚠️ RUN RED FIRST. Against the unrepaired tree (`clef.py` at `d01e0282`'s
successor, i.e. `HEAD` before this branch's own commit) `_detector_terms`
returns a single dict, not `(dict, discounted)`, and `Ruling.abstain`'s
`no_candidates` path never returns anything for an off-staff box that is a
staff's only candidate -- it DECIDES, on the "additive, never a filter"
design this roadmap item reverses. See the commit message for the RED
counts.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import clef as clef_mod
from tools.omr.staged.record import Outcome, Q, READERS
from tools.omr.tests._staged_fixtures import fresh_log as _log

SUB = R.staff(0, 0, 0)

#: The measured shape of the real fault (Sec.4c): ~5.7 staff spaces below the
#: bottom line, i.e. 8 (the bottom line, in `Q.CLEF_POSITION` half-step
#: units) plus 5.7 * 2 half-steps -- close to the record's own 19.36.
OFF_STAFF_POSITION = 19.4

#: A normal `clefG` box's measured centre (module docstring, roadmap 2.11b:
#: the pooled G on-staff cluster runs ~2.6..7.6, median ~4.2-4.3 across the
#: three acceptance documents).
NORMAL_G_POSITION = 4.3


class TestALoneOffStaffBoxNoLongerDecidesAlone(unittest.TestCase):
    """The exact shape of the roadmap's own finding: one `clefG` detector
    box, alone, at an off-staff position."""

    def test_it_no_longer_decides_treble(self):
        log = _log()
        log.observe(SUB, Q.CLEF_GLYPH, "clefG", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.688, y_center=500.0)
        log.observe(SUB, Q.CLEF_POSITION, OFF_STAFF_POSITION,
                    reader=READERS.GEOMETRY, frame="cell:0", glyph="clefG",
                    y_center=500.0)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_candidates")

    def test_the_discount_is_named_and_the_row_stays_in_basis_not_used(self):
        log = _log()
        log.observe(SUB, Q.CLEF_GLYPH, "clefG", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.688, y_center=500.0)
        log.observe(SUB, Q.CLEF_POSITION, OFF_STAFF_POSITION,
                    reader=READERS.GEOMETRY, frame="cell:0", glyph="clefG",
                    y_center=500.0)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        glyph_row = log.rows(Q.CLEF_GLYPH, SUB)[0]
        pos_row = log.rows(Q.CLEF_POSITION, SUB)[0]
        discounted = v.detail[clef_mod.OFF_STAFF_REASON]
        self.assertEqual(len(discounted), 1)
        self.assertEqual(discounted[0]["glyph_row"], glyph_row.id)
        self.assertEqual(discounted[0]["reason"],
                          clef_mod.OFF_STAFF_REASON)
        self.assertEqual(discounted[0]["family"], "treble")
        self.assertIn(glyph_row.id, v.basis)
        self.assertIn(pos_row.id, v.basis)
        self.assertNotIn(glyph_row.id, v.used)


class TestThePositiveControlCanFail(unittest.TestCase):
    """The SAME box, at its normal position, still decides -- proving the
    discount is keyed on the position, not on the glyph or the family."""

    def test_the_same_gClef_at_its_normal_position_still_decides_treble(self):
        log = _log()
        log.observe(SUB, Q.CLEF_GLYPH, "clefG", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.688, y_center=500.0)
        log.observe(SUB, Q.CLEF_POSITION, NORMAL_G_POSITION,
                    reader=READERS.GEOMETRY, frame="cell:0", glyph="clefG",
                    y_center=500.0)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, "treble")
        self.assertNotIn(clef_mod.OFF_STAFF_REASON, v.detail)


class TestAnOffStaffBoxBesideANormalOne(unittest.TestCase):
    """Two boxes on one staff: the normal one decides, and the off-staff one
    is discounted and listed, not silently merged into the winner's margin."""

    def test_the_normal_box_decides_and_the_off_staff_one_is_discounted(self):
        log = _log()
        log.observe(SUB, Q.CLEF_GLYPH, "clefG", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.90, y_center=100.0)
        log.observe(SUB, Q.CLEF_POSITION, NORMAL_G_POSITION,
                    reader=READERS.GEOMETRY, frame="cell:0", glyph="clefG",
                    y_center=100.0)
        log.observe(SUB, Q.CLEF_GLYPH, "clefG", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.688, y_center=500.0)
        log.observe(SUB, Q.CLEF_POSITION, OFF_STAFF_POSITION,
                    reader=READERS.GEOMETRY, frame="cell:0", glyph="clefG",
                    y_center=500.0)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, "treble")

        rows = log.rows(Q.CLEF_GLYPH, SUB)
        on_row = next(r for r in rows
                      if r.detail.get("y_center") == 100.0)
        off_row = next(r for r in rows
                       if r.detail.get("y_center") == 500.0)

        discounted = v.detail[clef_mod.OFF_STAFF_REASON]
        self.assertEqual(len(discounted), 1)
        self.assertEqual(discounted[0]["glyph_row"], off_row.id)

        self.assertIn(on_row.id, v.used)
        self.assertNotIn(off_row.id, v.used)
        # ⚠️ BOTH stay in basis -- the harness computes `basis` from every
        # row `Evidence.rows` returned, independent of what a term cites.
        self.assertIn(on_row.id, v.basis)
        self.assertIn(off_row.id, v.basis)


class TestAHumanRowIsNeverDiscounted(unittest.TestCase):
    """Roadmap 3.4f's population. `_clef_of` names G/F/percussion by class,
    so a human's `clefG`/`clefF` box (`review/human_evidence.py` files the
    SAME two rows for any clef class, not only the C family) reaches
    `_detector_terms`, not `_c_family_support`. Geometry does not get to
    discount a human's own reading any more than it gets to overrule his own
    C-clef class choice (3.4f's manager review) -- the reader-keyed
    exemption `_is_human_clef_reader` already gates is reused here, not
    restated.
    """

    def test_a_human_box_at_an_unusual_position_is_not_discounted(self):
        """⚠️ COHERENCE, NOT ACCURACY: a human's clef score is really always
        `None` (`review/human_evidence.py`'s own note, a different, already
        reported and unrepaired weakness). A deliberately high score here
        isolates ONE thing -- had the reader exemption not been checked,
        this position (off the measured band, identical to the DETECTOR
        case above) would have been discounted exactly as it was there, and
        the staff would ABSTAIN instead of deciding."""
        log = _log()
        log.observe(SUB, Q.CLEF_GLYPH, "clefG", reader=READERS.SEAN,
                    frame="cell:0", score=0.9, y_center=500.0,
                    x_center=50.0)
        log.observe(SUB, Q.CLEF_POSITION, OFF_STAFF_POSITION,
                    reader=READERS.SEAN, frame="cell:0", glyph="clefG",
                    y_center=500.0)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, "treble")
        self.assertNotIn(clef_mod.OFF_STAFF_REASON, v.detail)


if __name__ == "__main__":
    unittest.main()
