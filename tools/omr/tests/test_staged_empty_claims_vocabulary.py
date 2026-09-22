"""`no_ink` is a claim about the PAGE, and three readers made it about THEMSELVES.

⚠️⚠️ THE FAULT, measured by `trace --empty-claims` on the one record carrying
an ink witness (Litolff Beethoven 5 pp.1-4, `Q.INK` default-ON): **2,476
`no_ink` claims, ZERO of them the ink reader's own, 2,377 standing on a cell
`Q.INK` sees ink in** -- `dynamic_letter` 997, `beam_stroke` 980, `stem` 400,
and those three sum to the contradicted total exactly.

The three populations do NOT share a cause, which is why they do not share a
word:

  dynamic_letter   a FAMILY FILTER over a NON-EMPTY detection list
                   (997 of 997 stood on a cell that HAD detections)
  stem             `detect_stems` NAMES AND FILTERS IN ONE ACT
  beam_stroke      a reader whose INPUT IS THE STEM SET -- and 665 of its 980
                   claims stand on a cell with fewer than two stems, where no
                   beam can be joined whatever the page holds

⚠️ EVERY TEST HERE DRIVES THE REAL GATHERER. A fixture that does not match
GATHER tests the test -- this repo has been bitten by that twice, once when a
`Q.METER_GLYPH` fixture filed a row on the wrong KIND so a rule read no boxes
on any real page while five unit tests stayed green.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged import trace as T
from tools.omr.staged.record import ABSTAIN, Log, Q, Scope


class _Det:
    def __init__(self, name, x, y, w=10.0, h=10.0, conf=0.8, category="dynamic"):
        self.smufl_name = name
        self.x_canonical, self.y_canonical = x, y
        self.width_canonical, self.height_canonical = w, h
        self.confidence, self.category = conf, category
        self.x_center, self.y_center = x + w / 2, y + h / 2


def _staff(idx, line_ys, sys_idx=0):
    return SimpleNamespace(staff_index=idx, system_index=sys_idx,
                           line_ys=list(line_ys), top_y=min(line_ys),
                           x_start=0, x_end=1000, line_thickness_px=None,
                           line_wander_px=None)


def _cell(staff_index, measure_index, bbox, upscale):
    return SimpleNamespace(staff_index=staff_index, page_index=0,
                           measure_index=measure_index, bbox_page_px=bbox,
                           upscale_factor=upscale, image_no_staff=None)


def _pws(staves, binary=None):
    return SimpleNamespace(page=SimpleNamespace(page_index=0, binary=binary),
                           staves=staves)


def _refusal(log, quantity, cell):
    """The ONE `Abstention` this family wrote for this cell.

    ⚠️ `Log.rows` returns OBSERVATIONS and `Log.refusals` returns
    ABSTENTIONS -- they are different collections, and asking the wrong one
    for a refusal returns an empty tuple, which reads exactly like a reader
    that never ran. Asserting the arity is what turns that into a failure.
    """
    out = log.refusals(quantity, cell, scope=Scope.SELF_AND_DESCENDANTS)
    assert len(out) == 1, f"{quantity}: expected one refusal, got {len(out)}"
    return out[0]


def _reason(log, quantity, cell):
    return _refusal(log, quantity, cell).reason


class TestADetectionThatIsNotOfThisFamilyIsNotAnEmptyPage(unittest.TestCase):
    """The 997, and the POSITIVE CONTROL that the gatherer still reads a letter.

    ⚠️ Without the second test the first passes for a gatherer that has
    stopped working altogether -- a refusal test suite passes by refusing
    everything, which is why this file pairs every refusal with an acceptance.
    """

    def _run(self, dets):
        st = _staff(0, [50, 60, 70, 80, 90])
        cell = _cell(0, 0, [0.0, 10.0, 500.0, 200.0], 1.0)
        log = Log()
        G.gather_dynamic_letters(log, _pws([st]), [cell], {0: (0, 0)},
                                 {R.cell(0, 0, 0, 0).to_key(): dets})
        return log

    def test_a_cell_of_noteheads_says_NO_GLYPH_OF_THIS_KIND_not_no_ink(self):
        log = self._run([_Det("noteheadBlackOnLine", 100.0, 70.0,
                              category="notehead")])
        cell = R.cell(0, 0, 0, 0)
        self.assertEqual(_reason(log, Q.DYNAMIC_LETTER, cell),
                         ABSTAIN.NO_GLYPH_OF_THIS_KIND)

    def test_it_records_HOW_MANY_detections_it_looked_past(self):
        """The count is what makes the claim checkable by a later reader."""
        log = self._run([_Det("noteheadBlackOnLine", 100.0, 70.0,
                              category="notehead"),
                         _Det("restQuarter", 200.0, 70.0, category="rest")])
        self.assertEqual(
            _refusal(log, Q.DYNAMIC_LETTER, R.cell(0, 0, 0, 0))
            .detail["cell_n_detections"], 2)

    def test_POSITIVE_CONTROL_a_real_letter_is_still_observed(self):
        log = self._run([_Det("dynamicF", 100.0, 100.0)])
        cell = R.cell(0, 0, 0, 0)
        self.assertEqual(
            len(log.rows(Q.DYNAMIC_LETTER, cell,
                         scope=Scope.SELF_AND_DESCENDANTS)), 1)
        self.assertEqual(
            len(log.refusals(Q.DYNAMIC_LETTER, cell,
                             scope=Scope.SELF_AND_DESCENDANTS)), 0)


class TestTheBeamReadersInputIsTheStemSet(unittest.TestCase):
    """The 665, and it is the finding rather than the repair.

    A BEAM JOINS STEM TIPS. `detect_beams` takes the strokes `detect_stems`
    returned, so a cell with fewer than two of them cannot carry a beam joined
    within it -- and on the measured record the 400 cells with NO stem are
    EXACTLY the 400 cells `stem` itself refused, set for set. That silence is
    DERIVED, and `no_ink` attributed it to the page.

    ⚠️ THE WORD IS A CLAIM ABOUT OUR STEM READING, NOT ABOUT THE PRINT. Where
    a beam IS printed and its stems were missed, `no_stems_to_join` says
    exactly that, which is the point of it.
    """

    def _run(self, n_stems, n_beams):
        st = _staff(0, [50, 60, 70, 80, 90])
        cell = _cell(0, 0, [0.0, 10.0, 500.0, 200.0], 1.0)
        log = Log()

        def fake_detect_lines(c, candidates_out=None, noteheads=None):
            # the five fields `gather_cv_lines`' observe path reads off a
            # stroke, derived by grepping that block rather than guessed
            mk = lambda i: SimpleNamespace(
                x_canonical=10.0 * i, y_canonical=20.0,
                width_canonical=2.0, height_canonical=40.0,
                y_center=40.0)
            return {"stems": [mk(i) for i in range(n_stems)],
                    "beams": [mk(i) for i in range(n_beams)]}

        # ⚠️ `gather_cv_lines` imports `detect_lines` INSIDE the function
        # (`from ..line_detection import detect_lines`), so the name that has
        # to move is the one on `line_detection`, not one on `gather`. Patching
        # the wrong module leaves the real reader running and the test passes
        # or fails for a reason that has nothing to do with the fixture.
        from tools.omr import line_detection as LD
        real = LD.detect_lines
        LD.detect_lines = fake_detect_lines
        try:
            G.gather_cv_lines(log, [cell], {0: (0, 0)}, {})
        finally:
            LD.detect_lines = real
        return log

    def test_no_stem_at_all_says_NO_STEMS_TO_JOIN(self):
        log = self._run(n_stems=0, n_beams=0)
        self.assertEqual(_reason(log, Q.BEAM_STROKE, R.cell(0, 0, 0, 0)),
                         ABSTAIN.NO_STEMS_TO_JOIN)

    def test_ONE_stem_also_says_NO_STEMS_TO_JOIN_because_a_beam_needs_two(self):
        log = self._run(n_stems=1, n_beams=0)
        self.assertEqual(_reason(log, Q.BEAM_STROKE, R.cell(0, 0, 0, 0)),
                         ABSTAIN.NO_STEMS_TO_JOIN)

    def test_TWO_stems_and_no_beam_is_the_readers_OWN_silence(self):
        """The 315. Here the reader could have spoken and did not, so the
        word must NOT blame the stem set."""
        log = self._run(n_stems=2, n_beams=0)
        self.assertEqual(_reason(log, Q.BEAM_STROKE, R.cell(0, 0, 0, 0)),
                         ABSTAIN.NO_LINE_ACCEPTED)

    def test_the_stem_family_never_says_NO_STEMS_TO_JOIN_about_itself(self):
        log = self._run(n_stems=0, n_beams=0)
        self.assertEqual(_reason(log, Q.STEM, R.cell(0, 0, 0, 0)),
                         ABSTAIN.NO_LINE_ACCEPTED)

    def test_the_stem_count_is_on_the_row_so_the_claim_is_checkable(self):
        log = self._run(n_stems=1, n_beams=0)
        self.assertEqual(
            _refusal(log, Q.BEAM_STROKE, R.cell(0, 0, 0, 0))
            .detail["cell_n_stems"], 1)

    def test_POSITIVE_CONTROL_a_real_beam_is_still_observed(self):
        log = self._run(n_stems=2, n_beams=1)
        cell = R.cell(0, 0, 0, 0)
        self.assertEqual(
            len(log.rows(Q.BEAM_STROKE, cell,
                         scope=Scope.SELF_AND_DESCENDANTS)), 1)
        self.assertEqual(
            len(log.refusals(Q.BEAM_STROKE, cell,
                             scope=Scope.SELF_AND_DESCENDANTS)), 0)


class TestNoneOfTheThreeWordsClaimsInk(unittest.TestCase):
    """The property the repair exists for, asserted against the DERIVED check.

    `trace.ink_claiming_reasons()` derives its set from `ABSTAIN` on the token
    "ink", so this cannot be satisfied by a hand list going stale.
    """

    def test_the_three_words_are_not_ink_claiming(self):
        claiming = T.ink_claiming_reasons()
        for word in (ABSTAIN.NO_GLYPH_OF_THIS_KIND, ABSTAIN.NO_LINE_ACCEPTED,
                     ABSTAIN.NO_STEMS_TO_JOIN):
            self.assertNotIn(word, claiming)

    def test_NO_INK_ITSELF_IS_STILL_INK_CLAIMING(self):
        """⚠️ The control that stops the test above passing vacuously: if the
        derivation broke and returned nothing, every word would 'pass'."""
        self.assertIn(ABSTAIN.NO_INK, T.ink_claiming_reasons())

    def test_the_three_words_STAY_IN_THE_REPORT(self):
        """⚠️ A repair must not be able to hide its own population. Dropping
        out of `contradicted` is correct; dropping out of the report entirely
        is this repo's *the inventory that closed the check that produced
        it*."""
        for word in (ABSTAIN.NO_GLYPH_OF_THIS_KIND, ABSTAIN.NO_LINE_ACCEPTED,
                     ABSTAIN.NO_STEMS_TO_JOIN):
            self.assertIn(word, T._HONEST_EMPTY)


if __name__ == "__main__":
    unittest.main()
