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
from tools.omr.staged.record import Outcome, Q, READERS
from tools.omr.tests._staged_fixtures import fresh_log as _log

SUB = R.staff(0, 0, 0)


def _pagewide_clef(log, sub, kind):
    """ROADMAP 2.324: the page-wide pass's READ header claim of this staff's clef (the CV locator is retired)."""
    log.observe(sub, Q.CLAIMED_AREA, [10.0, 0.0, 40.0, 80.0], reader=READERS.CV_CLAIMED_REGISTER, frame="cell:0",
                cell=0, owner="clef", owner_row=None, owner_glyph=None, unit="area", standing="READ",
                source="clef_pagewide", change=False, kind=kind, family=None, boxes_inside={})


class TestTheCategoryTestIsLoadBearing(unittest.TestCase):
    """⚠️⚠️ `clef_family` reads the leading letter of the class name's core,
    so WITHOUT the category test it calls `flag8thUp` a BASS clef and
    `graceNoteAcciaccatura` a treble one. `class_aliases` records that trap as
    "unreachable: every caller filters `category != 'clef'` first" -- and this
    call site did not filter, it matched a literal set. Measured over the
    committed 208-name vocabulary, 27 classes would be admitted as clefs."""

    def test_a_flag_is_not_a_bass_clef(self):
        self.assertFalse(gather_mod._is_clef_class("flag8thUp", "flag"))

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


class TestTheFineCClefsSUPPORTTheClefThePageNamed(unittest.TestCase):
    """The consumer half: `_c_family_support` matched the literal `"clefC"`,
    so the mechanism built for exactly this was keyed on a name that never
    arrives."""

    def test_clefCAlto_supports_the_pages_C_clef(self):
        log = _log()
        log.observe(SUB, Q.CLEF_GLYPH, "clefCAlto", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.95)
        _pagewide_clef(log, SUB, "tenor")
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertEqual(v.value, "tenor")
        # ⚠️ THE SCORE, NOT A SUBSTRING. `tenor` must carry the page-wide
        # read's W_PAGEWIDE (2.324; was the locator's W_LOCATOR) *plus* W_C_FAMILY -- a name check would pass on a verdict
        # the support never reached, which is the fault this lane is about.
        self.assertAlmostEqual(v.detail["scores"]["tenor"],
                               clef_mod.W_PAGEWIDE + clef_mod.W_C_FAMILY)

    def test_WITHOUT_the_C_clef_the_same_staff_scores_the_page_read_alone(self):
        """⚠️ THE CONTROL THAT GIVES THE NUMBER ABOVE ITS MEANING. Identical
        log minus the detector row: if this also read 3.5, the assertion
        above would be measuring nothing."""
        log = _log()
        _pagewide_clef(log, SUB, "tenor")
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertAlmostEqual(v.detail["scores"]["tenor"], clef_mod.W_PAGEWIDE)

    def test_a_G_clef_is_NOT_C_family_support(self):
        """⚠️ POSITIVE CONTROL: a support rule that returned every row would
        satisfy the test above just as well. A `clefG` beside a located
        `tenor` must leave tenor on the page read's weight alone."""
        log = _log()
        log.observe(SUB, Q.CLEF_GLYPH, "clefG", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.95)
        _pagewide_clef(log, SUB, "tenor")
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertAlmostEqual(v.detail["scores"]["tenor"], clef_mod.W_PAGEWIDE)


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


def test_c_clef_read_flags_default_on(monkeypatch):
    """ROADMAP 2.257 (2026-11-03): OMR_C_CLEF_READ is default ON, deny-list; OMR_WHOLE_REST_OWN_STAFF is default ON too (2.257 round 2, 2026-11-03)."""
    from tools.omr import clef_locator
    from tools.omr.staged.adjudicators import clef as clef_adj, rhythm
    monkeypatch.delenv("OMR_C_CLEF_READ", raising=False)
    assert clef_locator._c_clef_read_on() and clef_adj._c_clef_read_on()
    for v in ("0", "false", "no", "off"):
        monkeypatch.setenv("OMR_C_CLEF_READ", v)
        assert not clef_locator._c_clef_read_on() and not clef_adj._c_clef_read_on()
    assert rhythm.WHOLE_REST_OWN_STAFF_ENV == "OMR_WHOLE_REST_OWN_STAFF"
    monkeypatch.delenv("OMR_WHOLE_REST_OWN_STAFF", raising=False)
    assert rhythm._whole_rest_own_staff_on()
    monkeypatch.setenv("OMR_WHOLE_REST_OWN_STAFF", "0")
    assert not rhythm._whole_rest_own_staff_on()
