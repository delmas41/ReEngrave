"""ROADMAP 2.47b — a cautionary clef/key/meter printed after a system's own
last barline is not a bar (CLAUDE.md section 10).

Brahms 1/i, Breitkopf 317803, PDF page 0, system 0: `measure_extractor.
_measure_x_boundaries` keeps a barline column only inside the system's own
edges; whatever is left over after the final one ("the tail") becomes its
own cell purely because its WIDTH clears `median_measure_width * 0.20` --
113px against a 111.8px threshold, a 1% margin
(`benchmarks/omr-measure-partition-2026-09/FINDINGS.md` section 0a). Crop-
verified against the print: that 113px strip holds nothing but a cautionary
clef + time signature for the NEXT system, not a short eighth bar. The width
rule has no way to look inside the cell; `adjudicate_measure_partition` now
does, after the detector has run.

⚠️ RED confirmed by reverting `structure.py` to `git show HEAD:...` (the pre-
fix tree only reads `Q.BARLINE_COLUMN` and never looks at the cell's own
content) and re-running this file: `test_cautionary_tail_is_not_counted_as_
a_bar` failed (asserted 8, got 7) before the fix and the whole-page shape
test failed likewise. Every other test here is a CONTROL that must be able
to fail the other way (rule 7): a real note/rest in the tail keeps it a bar,
an empty tail changes nothing, and a system with no barline at all (a single
cell) is never touched.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import structure as _structure
from tools.omr.staged.record import Log, Outcome, Q, READERS


def _decide(log, quantity, subject):
    return adjudicate.adjudicate_one(log, adjudicate.REGISTRY[quantity], subject)


def _barline_column(log, staff_sub, n_cells):
    log.observe(staff_sub, Q.BARLINE_COLUMN, n_cells, reader=READERS.GEOMETRY,
                frame="page", note="n_cells cut for this staff")


def _glyph(log, p, sys_idx, st_idx, cell_idx, glyph_idx, smufl_name):
    g = R.glyph(p, sys_idx, st_idx, cell_idx, glyph_idx)
    log.observe(g, Q.GLYPH_BOX, (smufl_name, 0.0, 0.0, 1.0, 1.0),
                reader=READERS.DETECTOR, frame="cell:%d" % cell_idx,
                score=0.9, category=smufl_name)
    return g


class TestCautionaryTailDemoted(unittest.TestCase):
    """The headline case: Brahms p0 system 0, 8 staves read (shrunk from the
    real page's 14 for the test, the shape is identical), every staff's
    8th/final cell holding only `clefF`/`timeSig4` boxes -- no notehead, no
    rest, on any of them."""

    SYS = 0
    PAGE = 0
    N_STAVES = 3

    def _build(self, log, *, tail_classes_by_staff):
        """`tail_classes_by_staff[st_idx]` is the list of smufl names
        detected in that staff's OWN final cell (index 7, an 8-cell system
        -- 7 real bars + 1 contested tail, matching the real page's shape)."""
        for st_idx in range(self.N_STAVES):
            staff_sub = R.staff(self.PAGE, self.SYS, st_idx)
            _barline_column(log, staff_sub, 8)
            # A real bar's worth of ink in every one of the 7 real cells, so
            # the only thing distinguishing "cautionary" from "real" in this
            # test is cell 7's own content.
            for cell_idx in range(7):
                _glyph(log, self.PAGE, self.SYS, st_idx, cell_idx, 0,
                       "noteheadBlackOnLine")
            for gi, name in enumerate(tail_classes_by_staff[st_idx]):
                _glyph(log, self.PAGE, self.SYS, st_idx, 7, gi, name)

    def test_cautionary_tail_is_not_counted_as_a_bar(self):
        log = Log()
        tails = {st: ["clefF", "timeSig4"] for st in range(self.N_STAVES)}
        self._build(log, tail_classes_by_staff=tails)
        log.freeze()
        for st_idx in range(self.N_STAVES):
            v = _decide(log, Q.MEASURE_PARTITION, R.staff(self.PAGE, self.SYS, st_idx))
            self.assertEqual(v.outcome, Outcome.DECIDED)
            self.assertEqual(v.value, 7, f"staff {st_idx}")
            self.assertEqual(v.reason, "cautionary_tail_not_a_bar")

    def test_RED_a_real_note_in_the_tail_on_ONE_staff_keeps_it_a_bar_for_ALL(self):
        """CLAUDE.md section 10: a system-wide fact is printed at one bar on
        EVERY staff. One staff with a genuine short final bar (a real
        notehead in cell 7) means the system has not yet closed -- the tail
        is real for the whole system, not just that staff. Must be able to
        fail: reverting the cross-staff read to "only this staff's own cell"
        would wrongly demote staves 1 and 2 here."""
        log = Log()
        tails = {0: ["clefF", "timeSig4"],
                 1: ["noteheadBlackOnLine"],
                 2: ["clefG", "timeSig4"]}
        self._build(log, tail_classes_by_staff=tails)
        log.freeze()
        for st_idx in range(self.N_STAVES):
            v = _decide(log, Q.MEASURE_PARTITION, R.staff(self.PAGE, self.SYS, st_idx))
            self.assertEqual(v.value, 8, f"staff {st_idx}")
            self.assertEqual(v.reason, "read")


class TestControls(unittest.TestCase):
    PAGE, SYS, STAFF = 1, 0, 0

    def _staff(self):
        return R.staff(self.PAGE, self.SYS, self.STAFF)

    def test_a_short_final_bar_with_a_rest_stays_a_bar(self):
        """Control: a real rest (not a note) in the final cell is just as
        disqualifying as a notehead -- it is still a musical event, not
        cautionary ink."""
        log = Log()
        _barline_column(log, self._staff(), 3)
        _glyph(log, self.PAGE, self.SYS, self.STAFF, 0, 0, "noteheadBlackOnLine")
        _glyph(log, self.PAGE, self.SYS, self.STAFF, 1, 0, "noteheadBlackOnLine")
        _glyph(log, self.PAGE, self.SYS, self.STAFF, 2, 0, "restQuarter")
        log.freeze()
        v = _decide(log, Q.MEASURE_PARTITION, self._staff())
        self.assertEqual(v.value, 3)
        self.assertEqual(v.reason, "read")

    def test_a_system_with_no_trailing_strip_is_unchanged(self):
        """No barline at all -- `_measure_x_boundaries` reads one cell for
        the whole system. `n_cells == 1` must never be treated as "a tail
        past the last rule": there is no last rule."""
        log = Log()
        _barline_column(log, self._staff(), 1)
        _glyph(log, self.PAGE, self.SYS, self.STAFF, 0, 0, "clefG")
        _glyph(log, self.PAGE, self.SYS, self.STAFF, 0, 1, "noteheadBlackOnLine")
        log.freeze()
        v = _decide(log, Q.MEASURE_PARTITION, self._staff())
        self.assertEqual(v.value, 1)
        self.assertEqual(v.reason, "read")

    def test_an_empty_trailing_cell_keeps_todays_behaviour(self):
        """Rule 8: "we found nothing" is not evidence either way. An empty
        final cell (the detector abstained or found nothing there) must NOT
        be demoted -- today's geometry-only count stands, unchanged."""
        log = Log()
        _barline_column(log, self._staff(), 2)
        _glyph(log, self.PAGE, self.SYS, self.STAFF, 0, 0, "noteheadBlackOnLine")
        # Cell 1 (the tail) gets no Q.GLYPH_BOX row at all.
        log.freeze()
        v = _decide(log, Q.MEASURE_PARTITION, self._staff())
        self.assertEqual(v.value, 2)
        self.assertEqual(v.reason, "read")

    def test_a_pedal_mark_alone_in_the_tail_does_not_pass_as_a_key_signature(self):
        """`keyboardPedalPed`/`keyboardPedalUp` share the `"key"` prefix
        with `keyFlat`/`keySharp`/`keyNatural` -- the one collision in the
        208-class space. Must be able to fail: a naive `startswith("key")`
        classifier would wrongly demote this tail."""
        log = Log()
        _barline_column(log, self._staff(), 2)
        _glyph(log, self.PAGE, self.SYS, self.STAFF, 0, 0, "noteheadBlackOnLine")
        _glyph(log, self.PAGE, self.SYS, self.STAFF, 1, 0, "keyboardPedalPed")
        log.freeze()
        v = _decide(log, Q.MEASURE_PARTITION, self._staff())
        self.assertEqual(v.value, 2)
        self.assertEqual(v.reason, "read")

    def test_no_barline_column_still_abstains(self):
        log = Log()
        log.freeze()
        v = _decide(log, Q.MEASURE_PARTITION, self._staff())
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_barline")


class TestSignatureGlyphClassifier(unittest.TestCase):
    """Unit coverage for the classifier itself, isolated from the decision."""

    def test_clef_key_and_time_sig_classes_are_signature_ink(self):
        for name in ("clefG", "clefF", "clefCAlto", "clefUnpitchedPercussion",
                     "clef8", "clef15", "keyFlat", "keySharp", "keyNatural",
                     "timeSig4", "timeSigCommon", "timeSigCutCommon"):
            self.assertTrue(_structure._is_signature_glyph_class(name), name)

    def test_notehead_rest_and_pedal_classes_are_not(self):
        for name in ("noteheadBlackOnLine", "noteheadHalfInSpace",
                     "restQuarter", "restWhole", "keyboardPedalPed",
                     "keyboardPedalUp", "stem", "dynamicForte",
                     "accidentalSharp"):
            self.assertFalse(_structure._is_signature_glyph_class(name), name)


if __name__ == "__main__":
    unittest.main()
