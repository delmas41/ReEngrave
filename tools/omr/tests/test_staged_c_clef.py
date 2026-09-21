"""The staged gatherer dropped every C clef the detector reads.

`gather._CLEF_CLASSES` admitted `{clefG, clefF, clefC, clefUnpitchedPercussion}`.
`clefC` is the COARSE spelling (id 142) of a vocabulary whose whole coarse
block `class_aliases` records firing ZERO times -- and the detector emits the
FINE `clefCAlto` (id 6) and `clefCTenor` (id 7), which were in neither that
set nor anything downstream of it. So the set admitted the one spelling that
never occurs and dropped the two that do: measured over both shared records,
16 C-clef detections on 9 staves, discarded with no row and no abstention.

⚠️ COHERENCE, NOT ACCURACY. Nothing here says a `clefCAlto` detection is
RIGHT. It says the claim it can honestly make -- "a C clef is present" --
reaches the decision instead of being thrown away, and that the claim it
cannot make -- WHICH C clef -- is still refused.

Reach and the A/B: `benchmarks/omr-staged-c-clef-2026-09/FINDINGS.md`.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import gather as gather_mod
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import clef as clef_mod
from tools.omr.staged.record import Log, Outcome, Q, READERS

SUB = R.staff(0, 0, 0)


def _log():
    return Log()


class _Cell:
    """The least a cell needs to reach `gather_clef` and `_cell_grid`."""

    def __init__(self, staff_index=0, page_index=0, measure_index=0):
        self.staff_index = staff_index
        self.page_index = page_index
        self.measure_index = measure_index
        # five lines, 40 canonical px apart -> half_step 20.0
        self.staff_line_ys_canonical = [100, 140, 180, 220, 260]


class _Det:
    def __init__(self, smufl_name, category="clef", y_center=180.0,
                 x_center=50.0, confidence=0.9):
        self.smufl_name = smufl_name
        self.category = category
        self.y_center = y_center
        self.x_center = x_center
        self.confidence = confidence


def _gather(dets):
    """Drive `gather_clef` over one synthetic staff-head cell."""
    log = _log()
    cell = _Cell()
    cell_key = R.cell(0, 0, 0, 0).to_key()
    gather_mod.gather_clef(log, [cell], {0: (0, 0)}, {cell_key: list(dets)})
    return log


def _glyph_values(log):
    return [o.value for o in log.rows(Q.CLEF_GLYPH, SUB)]


def _glyph_refusals(log):
    return list(log.refusals(Q.CLEF_GLYPH, SUB))


class TestTheGathererAdmitsTheFineCClefs(unittest.TestCase):
    """The wiring half: the rows exist at all."""

    def test_clefCAlto_is_GATHERED(self):
        self.assertEqual(_glyph_values(_gather([_Det("clefCAlto")])),
                         ["clefCAlto"])

    def test_clefCTenor_is_GATHERED(self):
        self.assertEqual(_glyph_values(_gather([_Det("clefCTenor")])),
                         ["clefCTenor"])

    def test_the_incumbent_set_would_have_dropped_BOTH(self):
        """⚠️ THE CONTROL THAT MAKES THE TWO ABOVE MEAN SOMETHING. Without it
        they would pass just as happily against a rule that admits every
        detection on the page."""
        self.assertNotIn("clefCAlto", gather_mod._CLEF_CLASSES_INCUMBENT)
        self.assertNotIn("clefCTenor", gather_mod._CLEF_CLASSES_INCUMBENT)

    def test_a_staff_with_only_a_C_clef_no_longer_abstains_NO_DETECTIONS(self):
        """The measured consequence: 9 staves over two documents held a C
        clef and recorded that they held nothing."""
        self.assertEqual(_glyph_refusals(_gather([_Det("clefCAlto")])), [])

    def test_the_grid_row_travels_with_it(self):
        """`Q.CLEF_POSITION` is the SECOND witness and is what the on-staff
        term cites; a gathered glyph with no position row is half wired."""
        log = _gather([_Det("clefCAlto", y_center=180.0)])
        pos = list(log.rows(Q.CLEF_POSITION, SUB))
        self.assertEqual(len(pos), 1)
        # top line 100, half_step 20 -> (180-100)/20 == 4.0 steps down
        self.assertAlmostEqual(float(pos[0].value), 4.0)


class TestAnOctaveMarkIsNotAClef(unittest.TestCase):
    """⚠️ `clef8` / `clef15` MODIFY a clef, so admitting them would let one
    compete as a clef in its own right. Excluded deliberately, not by
    omission -- and they fire 0 times on both shared records, so this is a
    structural guard rather than a measured saving."""

    def test_clef8_is_NOT_gathered(self):
        self.assertEqual(_glyph_values(_gather([_Det("clef8")])), [])

    def test_clef15_is_NOT_gathered(self):
        self.assertEqual(_glyph_values(_gather([_Det("clef15")])), [])

    def test_a_staff_holding_only_an_octave_mark_still_abstains(self):
        self.assertEqual(len(_glyph_refusals(_gather([_Det("clef8")]))), 1)


class TestTheCategoryTestIsLoadBearing(unittest.TestCase):
    """⚠️⚠️ `clef_family` reads the leading letter of the class name's core,
    so WITHOUT the category test it calls `flag8thUp` a BASS clef and
    `graceNoteAcciaccatura` a treble one. `class_aliases` records that trap as
    "unreachable: every caller filters `category != 'clef'` first" -- and this
    call site did not filter, it matched a literal set. Measured over the
    committed 208-name vocabulary, 27 classes would be admitted as clefs."""

    def test_a_flag_is_not_a_bass_clef(self):
        self.assertFalse(gather_mod._is_clef_class("flag8thUp", "flag"))
        self.assertEqual(_glyph_values(_gather([_Det("flag8thUp", "flag")])), [])

    def test_a_grace_note_is_not_a_treble_clef(self):
        self.assertFalse(
            gather_mod._is_clef_class("graceNoteAcciaccatura", "ornament"))

    def test_a_fingering_is_not_a_clef(self):
        self.assertFalse(gather_mod._is_clef_class("fingering3", "ornament"))

    def test_the_family_rule_ALONE_really_does_admit_all_three(self):
        """⚠️ THE POSITIVE CONTROL FOR THE THREE REFUSALS ABOVE. A test that
        only asserts False passes against a predicate that refuses
        everything; this shows the category test is what is doing the work."""
        from tools.omr.clef_geometry import clef_family
        for name in ("flag8thUp", "graceNoteAcciaccatura", "fingering3"):
            self.assertIsNotNone(clef_family(name), name)

    def test_a_real_clef_with_a_clef_category_IS_admitted(self):
        self.assertTrue(gather_mod._is_clef_class("clefG", "clef"))


class TestAClassNameStillCannotNameWhichCClef(unittest.TestCase):
    """⚠️⚠️ THE REFUSAL SURVIVES THE WIRING, AND THAT IS THE DESIGN.

    `clefCAlto` looks like it names its line, so putting it in
    `_GLYPH_TO_CLEF` reads like a free repair. Measured, it is not: on
    Brahms 1 p3/s1/st11 the detector fires `clefCTenor` where the locator
    measures ALTO twice at 0.91, and the detector's 3.0 would beat the
    locator's 2.0 and flip a staff that is right today."""

    def test_clefCAlto_alone_ABSTAINS_rather_than_naming_alto(self):
        log = _log()
        log.observe(SUB, Q.CLEF_GLYPH, "clefCAlto", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.95)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_candidates")

    def test_neither_fine_C_clef_is_in_the_naming_table(self):
        self.assertNotIn("clefCAlto", clef_mod._GLYPH_TO_CLEF)
        self.assertNotIn("clefCTenor", clef_mod._GLYPH_TO_CLEF)

    def test_the_detector_CANNOT_overturn_the_locator_on_which_C_clef(self):
        """⚠️ THE MEASURED CASE, AS A TEST. Brahms 1 p3/s1/st11: detector
        `clefCTenor`, locator `alto` twice. The staff must stay ALTO."""
        log = _log()
        log.observe(SUB, Q.CLEF_GLYPH, "clefCTenor", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.95)
        for frame in ("header_window", "cell:0"):
            log.observe(SUB, Q.CLEF_LOCATED, "alto", reader=READERS.CV_LOCATOR,
                        frame=frame, score=0.91, family="C", line=3)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertEqual(v.value, "alto")


class TestTheFineCClefsSUPPORTTheClefTheLocatorNamed(unittest.TestCase):
    """The consumer half: `_c_family_support` matched the literal `"clefC"`,
    so the mechanism built for exactly this was keyed on a name that never
    arrives."""

    def test_clefCAlto_supports_the_locators_C_clef(self):
        log = _log()
        log.observe(SUB, Q.CLEF_GLYPH, "clefCAlto", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.95)
        log.observe(SUB, Q.CLEF_LOCATED, "tenor", reader=READERS.CV_LOCATOR,
                    frame="header_window", score=0.88, family="C", line=4)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertEqual(v.value, "tenor")
        # ⚠️ THE SCORE, NOT A SUBSTRING. `tenor` must carry the locator's
        # W_LOCATOR *plus* W_C_FAMILY -- a name check would pass on a verdict
        # the support never reached, which is the fault this lane is about.
        self.assertAlmostEqual(v.detail["scores"]["tenor"],
                               clef_mod.W_LOCATOR + clef_mod.W_C_FAMILY)

    def test_WITHOUT_the_C_clef_the_same_staff_scores_the_locator_alone(self):
        """⚠️ THE CONTROL THAT GIVES THE NUMBER ABOVE ITS MEANING. Identical
        log minus the detector row: if this also read 3.5, the assertion
        above would be measuring nothing."""
        log = _log()
        log.observe(SUB, Q.CLEF_LOCATED, "tenor", reader=READERS.CV_LOCATOR,
                    frame="header_window", score=0.88, family="C", line=4)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertAlmostEqual(v.detail["scores"]["tenor"], clef_mod.W_LOCATOR)

    def test_a_G_clef_is_NOT_C_family_support(self):
        """⚠️ POSITIVE CONTROL: a support rule that returned every row would
        satisfy the test above just as well. A `clefG` beside a located
        `tenor` must leave tenor on the locator's weight alone."""
        log = _log()
        log.observe(SUB, Q.CLEF_GLYPH, "clefG", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.95)
        log.observe(SUB, Q.CLEF_LOCATED, "tenor", reader=READERS.CV_LOCATOR,
                    frame="header_window", score=0.88, family="C", line=4)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertAlmostEqual(v.detail["scores"]["tenor"], clef_mod.W_LOCATOR)


class TestTheIncumbentSetAdmittedASpellingThatNeverFires(unittest.TestCase):
    """The shape of the fault, pinned so it reads as a finding rather than as
    an oversight."""

    def test_clefC_the_admitted_name_is_the_COARSE_one(self):
        from tools.omr.class_aliases import FINE_BLOCK_SIZE, vocabulary
        vocab = vocabulary()
        self.assertEqual(vocab.index("clefC"), 142)
        self.assertGreaterEqual(vocab.index("clefC"), FINE_BLOCK_SIZE)

    def test_the_dropped_names_are_the_FINE_ones(self):
        from tools.omr.class_aliases import FINE_BLOCK_SIZE, vocabulary
        vocab = vocabulary()
        for name in ("clefCAlto", "clefCTenor"):
            self.assertLess(vocab.index(name), FINE_BLOCK_SIZE, name)

    def test_the_repaired_rule_admits_every_pitched_clef_of_the_vocabulary(self):
        from tools.omr.class_aliases import vocabulary
        from tools.omr.yolo_detector import _class_name_to_category
        clefs = [n for n in set(vocabulary())
                 if _class_name_to_category(n) == "clef"]
        admitted = {n for n in clefs
                    if gather_mod._is_clef_class(n, "clef")}
        self.assertEqual(admitted, set(clefs) - {"clef8", "clef15"})


if __name__ == "__main__":
    unittest.main()
