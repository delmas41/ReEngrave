"""Every fact carries what KIND of claim it makes.

Sean, 2026-09-17: *"yes every fact should carry what kind of claim."*

⚠️⚠️ EVERY ASSERTION HERE HAS A POSITIVE CONTROL, and that is not decoration.
This is a check of DECLARATIONS against DECLARATIONS, which passes vacuously
with alarming ease — the flag-direction guard's first version descended
THROUGH `environ.get` onto `os.environ`, matched nothing, and both its real
assertions passed. So each test that says "nothing is wrong" first proves the
question has a non-empty population, and each rule is exercised by INJECTING a
violation and requiring it to be caught.
"""
from __future__ import annotations

import dataclasses
import json
import unittest

from tools.omr.staged import capture
from tools.omr.staged.record import (
    CLAIM, CLAIM_OF_UNSCORED, CLAIMS, Log, Observation, Q, Verdict,
    claim_of, claims_of, claims_unaccounted, glyph, staff)
from tools.omr import positional_store as PS


def _q_names() -> set:
    return {k for k, v in vars(Q).items()
            if not k.startswith("_") and isinstance(v, str)}


class TestEveryQuantityDeclaresOne(unittest.TestCase):
    """The HARD tier: a quantity cannot enter `Q` without saying what kind of
    claim it makes."""

    def test_the_roster_is_not_empty(self):
        """⚠️ THE POSITIVE CONTROL FOR EVERY TEST BELOW. A derivation that
        silently returns nothing makes `claims_unaccounted() == []` mean
        "there are no quantities", which reads identically to "all of them
        are declared"."""
        self.assertGreater(len(_q_names()), 80)
        self.assertEqual(len(CLAIMS), len(_q_names()))

    def test_hard_tier_is_at_zero(self):
        self.assertEqual(claims_unaccounted(), [])

    def test_every_declaration_is_a_real_claim_word(self):
        words = set()
        for q in CLAIMS:
            words |= set(claims_of(q))
        self.assertTrue(words <= CLAIM.all())
        # and every word is USED — an unused word is a vocabulary that has
        # stopped describing the code.
        self.assertEqual(words, CLAIM.all())

    def test_a_reader_split_declaration_that_splits_NOTHING_is_CAUGHT(self):
        """⚠️ A split whose readers all say the same thing implies a
        distinction the pipeline does not have — the mirror of declaring one
        word where two are needed, and just as misleading to a consumer."""
        original = dict(CLAIMS)
        try:
            CLAIMS["DIRECTION_WORD"] = {"surya": CLAIM.IDENTIFICATION,
                                        "tesseract": CLAIM.IDENTIFICATION}
            found = claims_unaccounted()
            self.assertTrue(any("DIRECTION_WORD" in f for f in found), found)
        finally:
            CLAIMS.clear()
            CLAIMS.update(original)
        self.assertEqual(claims_unaccounted(), [])

    def test_an_undeclared_quantity_is_CAUGHT(self):
        """Inject the exact omission the check exists for."""
        original = dict(CLAIMS)
        try:
            del CLAIMS["GLYPH_BOX"]
            found = claims_unaccounted()
            self.assertTrue(any("GLYPH_BOX" in f for f in found), found)
        finally:
            CLAIMS.clear()
            CLAIMS.update(original)
        self.assertEqual(claims_unaccounted(), [])

    def test_a_declaration_naming_no_quantity_is_CAUGHT(self):
        original = dict(CLAIMS)
        try:
            CLAIMS["NOT_A_QUANTITY"] = CLAIM.MEASUREMENT
            found = claims_unaccounted()
            self.assertTrue(any("NOT_A_QUANTITY" in f for f in found), found)
        finally:
            CLAIMS.clear()
            CLAIMS.update(original)
        self.assertEqual(claims_unaccounted(), [])

    def test_a_misspelled_claim_word_is_CAUGHT(self):
        original = dict(CLAIMS)
        try:
            CLAIMS["GLYPH_BOX"] = "identifcation"      # one letter gone
            found = claims_unaccounted()
            self.assertTrue(any("identifcation" in f for f in found), found)
        finally:
            CLAIMS.clear()
            CLAIMS.update(original)
        self.assertEqual(claims_unaccounted(), [])


class TestTheJudgementCallsAreMarked(unittest.TestCase):
    """⚠️ `claims_unaccounted`'s docstring says the judgement calls are marked
    at their own entries. A claim about the code, made IN the code, is exactly
    the shape CLAUDE.md calls *a rule described in a docstring and never
    built* — so it is asserted rather than trusted.

    ⚠️ The first draft of that docstring named a table
    (`capture.CLAIM_JUDGEMENT_CALLS`) that did not exist. Caught by grep, not
    by review.
    """

    MARKER = "A JUDGEMENT CALL, NAMED"

    def _source(self) -> str:
        import inspect
        from tools.omr.staged import record
        return inspect.getsource(record)

    def test_the_docstring_names_the_marker_that_is_actually_used(self):
        import tools.omr.staged.record as record
        doc = record.claims_unaccounted.__doc__ or ""
        self.assertIn(self.MARKER, doc)
        self.assertNotIn("CLAIM_JUDGEMENT_CALLS", doc)

    def test_the_marker_is_on_real_entries(self):
        src = self._source()
        # one use in the docstring, the rest on entries
        n = src.count(self.MARKER)
        self.assertGreaterEqual(n, 6, "the docstring claims entries are "
                                      "marked; too few carry the marker")

    def test_no_table_named_by_the_docstring_is_missing(self):
        """The dangling-reference check, generalised: every `capture.X` the
        docstring names must exist."""
        import re
        import tools.omr.staged.record as record
        from tools.omr.staged import capture
        doc = record.claims_unaccounted.__doc__ or ""
        for name in re.findall(r"`capture\.([A-Za-z_]+)`", doc):
            self.assertTrue(hasattr(capture, name),
                            f"the docstring names capture.{name}, "
                            f"which does not exist")


class TestClaimOf(unittest.TestCase):

    def test_it_takes_either_spelling(self):
        self.assertEqual(claim_of("glyph_box"), claim_of("GLYPH_BOX"))
        self.assertEqual(claim_of(Q.NOTEHEAD_STAFF_POSITION),
                         CLAIM.MEASUREMENT)

    def test_the_reader_split_case_answers_per_reader(self):
        """⚠️⚠️ `Q.MARGIN_LABEL` IS THE ONE QUANTITY WHOSE CLAIM DEPENDS ON
        ITS READER. The PDF's own text layer reads no ink and cannot be wrong
        because the plate is bad; Surya, Tesseract and Vision are OCR of this
        raster and fail exactly when it degrades. That is the `source_kind`
        doctrine's distinction, INSIDE one quantity."""
        self.assertEqual(claim_of(Q.MARGIN_LABEL, "text_layer"),
                         CLAIM.EXTERNAL)
        for ocr in ("surya", "tesseract", "vision"):
            self.assertEqual(claim_of(Q.MARGIN_LABEL, ocr),
                             CLAIM.IDENTIFICATION, ocr)

    def test_a_split_quantity_asked_WITHOUT_a_reader_RAISES(self):
        """⚠️ It must not pick one. Answering EXTERNAL where the row may be
        OCR would hand a consumer the `source_kind` guarantee on a reading
        that does fall silent with the plate — the exact pooling this axis
        exists to stop."""
        with self.assertRaises(ValueError) as cm:
            claim_of(Q.MARGIN_LABEL)
        self.assertIn("depending on which reader", str(cm.exception))

    def test_a_reader_missing_from_a_split_declaration_RAISES(self):
        with self.assertRaises(ValueError) as cm:
            claim_of(Q.MARGIN_LABEL, "geometry")
        self.assertIn("declares no claim for reader", str(cm.exception))

    def test_a_row_of_the_split_quantity_answers_from_its_own_reader(self):
        log = Log()
        free = log.observe(staff(0, 0, 0), Q.MARGIN_LABEL, "Fl.",
                           reader="text_layer", frame="system_margin")
        ocr = log.observe(staff(0, 0, 1), Q.MARGIN_LABEL, "Ob.",
                          reader="surya", frame="system_margin")
        self.assertEqual(free.claim, CLAIM.EXTERNAL)
        self.assertEqual(ocr.claim, CLAIM.IDENTIFICATION)
        self.assertNotEqual(free.claim, ocr.claim)

    def test_an_unknown_quantity_RAISES_rather_than_defaulting(self):
        """⚠️ A fallback here would convert "nobody said" into a definite
        answer — the failure this repo has paid for at three levels in one
        day, and the one thing that would make the field worthless."""
        with self.assertRaises(ValueError) as cm:
            claim_of("no_such_quantity")
        self.assertIn("declares no claim kind", str(cm.exception))


class TestARowCarriesIt(unittest.TestCase):
    """⚠️ DERIVED, NOT STORED — so it cannot be omitted by any construction
    path, not merely by `Log.observe`."""

    def setUp(self):
        self.log = Log()
        self.g = glyph(0, 0, 0, 0, 0)

    def test_an_observation_carries_its_claim(self):
        row = self.log.observe(self.g, Q.GLYPH_BOX, [1, 2, 3, 4],
                               reader="detector", frame="cell:0", score=0.9)
        self.assertEqual(row.claim, CLAIM.IDENTIFICATION)

    def test_a_ruler_reading_and_a_naming_of_ink_DIFFER_on_one_page(self):
        """The distinction has to be visible on rows that really co-occur, or
        the field is a taxonomy nobody's data exercises."""
        box = self.log.observe(self.g, Q.GLYPH_BOX, [1, 2, 3, 4],
                               reader="detector", frame="cell:0", score=0.9)
        pos = self.log.observe(self.g, Q.NOTEHEAD_STAFF_POSITION, 7.38,
                               reader="cv_lines", frame="cell:0")
        self.assertNotEqual(box.claim, pos.claim)
        self.assertEqual(pos.claim, CLAIM.MEASUREMENT)

    def test_it_survives_dataclasses_replace(self):
        """A stored field with a default would be droppable here."""
        row = self.log.observe(self.g, Q.GLYPH_BOX, [1, 2, 3, 4],
                               reader="detector", frame="cell:0", score=0.9)
        self.assertEqual(dataclasses.replace(row, value=[9, 9, 9, 9]).claim,
                         CLAIM.IDENTIFICATION)

    def test_a_hand_built_observation_cannot_omit_it(self):
        row = Observation("obs1", self.g, Q.INK, [0, 0, 1, 1],
                          "cv_ink", "cell:0")
        self.assertEqual(row.claim, CLAIM.MEASUREMENT)

    def test_observe_REFUSES_an_undeclared_quantity_at_the_write(self):
        """⚠️ The check is at the WRITE, not at serialisation: otherwise an
        undeclared quantity would raise the first time somebody READ the
        field, arbitrarily far from the gather site — possibly never."""
        original = dict(CLAIMS)
        try:
            del CLAIMS["GLYPH_BOX"]
            with self.assertRaises(ValueError):
                self.log.observe(self.g, Q.GLYPH_BOX, [1, 2, 3, 4],
                                 reader="detector", frame="cell:0", score=0.9)
        finally:
            CLAIMS.clear()
            CLAIMS.update(original)
        # positive control: with the declaration back, the same call works
        self.assertTrue(self.log.observe(self.g, Q.GLYPH_BOX, [1, 2, 3, 4],
                                         reader="detector", frame="cell:0",
                                         score=0.9).claim)

    def test_a_verdict_carries_its_quantitys_claim_not_its_row_types(self):
        """⚠️ A verdict is not automatically INTERPRETATION. The claim is a
        property of the QUANTITY; "produced in ADJUDICATE" is already on the
        record structurally, and keying on the row type would make the field a
        second, weaker copy of that fact.

        ⚠️⚠️ THE DISCRIMINATING CASE IS A VERDICT ON A NON-INTERPRETATION
        QUANTITY. Asserting only that `Q.CLEF` comes out INTERPRETATION is
        satisfied by a property that returns INTERPRETATION unconditionally —
        the first draft of this test did exactly that, and the mutation arm
        that should have killed it would have survived.
        """
        from tools.omr.staged.record import Outcome
        clef = Verdict("vrd1", staff(0, 0, 0), Q.CLEF, Outcome.DECIDED,
                       "treble", "adjudicate_clef", "read")
        self.assertEqual(clef.claim, CLAIM.INTERPRETATION)

        box = Verdict("vrd2", staff(0, 0, 0), Q.GLYPH_BOX, Outcome.DECIDED,
                      [1, 2, 3, 4], "probe", "read")
        self.assertEqual(box.claim, CLAIM.IDENTIFICATION)
        self.assertNotEqual(box.claim, clef.claim)


class TestTheRecordStaysByteIdentical(unittest.TestCase):
    """⚠️⚠️ THE BLAST RADIUS, ASSERTED RATHER THAN ARGUED. A stored field
    would change every record this repo has ever written — the hazard CLAUDE.md
    records paying for `Verdict.single_pass_revision`, which was deliberately
    left out of `to_json` for exactly this reason."""

    def test_no_new_dataclass_field(self):
        for cls in (Observation, Verdict):
            names = [f.name for f in dataclasses.fields(cls)]
            self.assertNotIn("claim", names, cls.__name__)

    def test_to_json_is_unchanged(self):
        log = Log()
        row = log.observe(glyph(0, 0, 0, 0, 0), Q.GLYPH_BOX, [1, 2, 3, 4],
                          reader="detector", frame="cell:0", score=0.9)
        self.assertEqual(
            sorted(row.to_json()),
            ["basis", "detail", "frame", "id", "quantity", "reader",
             "score", "subject", "value"])
        # positive control: the row really does have a claim to omit
        self.assertTrue(row.claim)

    def test_a_json_only_consumer_can_still_derive_it(self):
        """The cost of not serialising, paid explicitly: the claim is
        recoverable from the `quantity` the row already carries."""
        log = Log()
        row = log.observe(glyph(0, 0, 0, 0, 0), Q.GLYPH_BOX, [1, 2, 3, 4],
                          reader="detector", frame="cell:0", score=0.9)
        blob = json.loads(json.dumps(row.to_json()))
        self.assertEqual(claim_of(blob["quantity"]), row.claim)


class TestReconciledWithUNSCORED(unittest.TestCase):
    """⚠️⚠️ TWO AXES, KEPT APART AND MADE UNABLE TO CONTRADICT — never merged,
    and never a fifth hand-written copy of one rule."""

    def test_the_constraint_has_a_population(self):
        """Positive control: the consistency question looks at real rows."""
        self.assertGreaterEqual(len(capture.UNSCORED), 30)
        self.assertEqual(set(CLAIM_OF_UNSCORED),
                         {w for w, _r, _f in capture.UNSCORED.values()})

    def test_neither_axis_determines_the_other(self):
        """The measured reason they are two fields and not one.

        ⚠️ `not_a_mark` holds a CATALOG fact and an OCR reading of this
        raster — the `source_kind` doctrine's own distinction, pooled under
        one word — while `MEASUREMENT` spans four `UNSCORED` words.
        """
        by_word = {}
        for q, (word, _r, _f) in capture.UNSCORED.items():
            by_word.setdefault(word, set()).update(claims_of(q))
        # one UNSCORED word, two claim kinds
        self.assertEqual(by_word["not_a_mark"],
                         {CLAIM.EXTERNAL, CLAIM.IDENTIFICATION})
        # one claim kind, many UNSCORED words
        words = {w for w, cs in by_word.items() if CLAIM.MEASUREMENT in cs}
        self.assertGreaterEqual(len(words), 4, words)

    def test_the_only_disagreement_is_the_accounted_one(self):
        found = capture.claim_consistency()
        self.assertEqual(
            [f for f in found if not f.startswith("CLAIM-DISAGREES "
                                                  "Q.WEDGE_BOX")],
            [])

    def test_a_planted_disagreement_is_CAUGHT(self):
        original = dict(CLAIMS)
        try:
            # NOTEHEAD_STAFF_POSITION is UNSCORED 'staff_grid_position',
            # which admits MEASUREMENT alone.
            CLAIMS["NOTEHEAD_STAFF_POSITION"] = CLAIM.IDENTIFICATION
            found = capture.claim_consistency()
            self.assertTrue(
                any("NOTEHEAD_STAFF_POSITION" in f for f in found), found)
        finally:
            CLAIMS.clear()
            CLAIMS.update(original)
        self.assertEqual(len(capture.claim_consistency()), 1)

    def test_an_UNSCORED_word_with_no_constraint_is_CAUGHT(self):
        original = dict(capture.UNSCORED)
        try:
            capture.UNSCORED["STAFF_LINES"] = (
                "a_brand_new_word", "planted", None)
            found = capture.claim_consistency()
            self.assertTrue(any("a_brand_new_word" in f for f in found), found)
        finally:
            capture.UNSCORED.clear()
            capture.UNSCORED.update(original)

    def test_the_disagreement_is_ACCOUNTED_and_not_widened_away(self):
        """⚠️ It must be reported AND on KNOWN_GAPS — never silenced by
        widening `CLAIM_OF_UNSCORED` until it passes."""
        rep_problems = capture.problems(capture.report())
        hit = [p for p in rep_problems if p.startswith("CLAIM-DISAGREES")]
        self.assertEqual(len(hit), 1, hit)
        self.assertEqual(capture.unaccounted(hit), [])
        self.assertNotIn(CLAIM.IDENTIFICATION, CLAIM_OF_UNSCORED["relation"])

    def test_an_undeclared_quantity_REACHES_capture_check(self):
        """⚠️⚠️ FOUND BY THE MUTATION BATTERY, NOT BY REVIEW. Deleting the
        hard tier's line from `capture.problems()` survived the first run:
        `claims_unaccounted()` is at ZERO, so today that line contributes
        nothing and removing it changes no output — an EQUIVALENT MUTANT under
        current data and a real hole under any other. Nothing asserted that an
        undeclared quantity actually reaches `--check`; the hard tier could
        have been silently unwired and the suite stayed green.
        """
        original = dict(CLAIMS)
        try:
            del CLAIMS["GLYPH_BOX"]
            found = capture.problems(capture.report())
            hit = [p for p in found if p.startswith("CLAIM-UNDECLARED")]
            self.assertTrue(hit, "the hard tier does not reach capture")
            # and it must be UNACCOUNTED, or `--check` would still exit 0
            self.assertTrue(capture.unaccounted(hit), hit)
        finally:
            CLAIMS.clear()
            CLAIMS.update(original)
        # positive control: with the declaration back, it reports nothing
        self.assertEqual(
            [p for p in capture.problems(capture.report())
             if p.startswith("CLAIM-UNDECLARED")], [])

    def test_a_closed_gap_must_LEAVE_the_list(self):
        """The stale-entry direction, on the entry this change adds."""
        stale = capture.stale_gaps(
            [p for p in capture.problems(capture.report())
             if not p.startswith("CLAIM-DISAGREES Q.WEDGE_BOX")])
        self.assertIn("CLAIM-DISAGREES Q.WEDGE_BOX", stale)


class TestReconciledWithThePositionalStore(unittest.TestCase):
    """`Membership.kind` is a PROJECTION of `CLAIM`, mapped and not restated."""

    def test_the_mapping_is_total_over_the_stores_own_constants(self):
        declared = {v for k, v in vars(PS).items()
                    if k.startswith("KIND_") and isinstance(v, str)}
        self.assertEqual(set(PS.CLAIM_OF_MEMBERSHIP_KIND), declared)
        self.assertTrue(declared)                      # positive control

    def test_every_mapped_value_is_a_real_claim_word(self):
        self.assertTrue(
            set(PS.CLAIM_OF_MEMBERSHIP_KIND.values()) <= CLAIM.all())

    def test_the_distinction_that_cost_something_survives_the_mapping(self):
        """⚠️ The measured fault: pooling a detector's box with the ink blob
        it merely overlaps read a Litolff notehead at 3.646 staff spaces
        against 1.316 split. The two must not map to one word."""
        self.assertNotEqual(
            PS.CLAIM_OF_MEMBERSHIP_KIND[PS.KIND_DETECTOR_CLASS],
            PS.CLAIM_OF_MEMBERSHIP_KIND[PS.KIND_OVERLAPS])


class TestNoClaimKindDecidesAnything(unittest.TestCase):
    """⚠️⚠️ `A-INK-4`: A FACTOR CONTRIBUTES, IT DOES NOT DECIDE. This change
    adds no rule, veto or threshold. Asserted at the source rather than
    promised in prose, because a later edit that starts gating on a claim
    kind should go red here."""

    def test_no_adjudicator_branches_on_a_claim_kind(self):
        import inspect
        from tools.omr.staged import adjudicate, evaluate, export
        for mod in (adjudicate, evaluate, export):
            src = inspect.getsource(mod)
            for word in CLAIM.all():
                self.assertNotIn(f'"{word}"', src,
                                 f"{mod.__name__} names the claim word "
                                 f"{word!r} — this change is a LABEL, not a "
                                 f"rule")

    def test_the_words_are_reachable_at_all(self):
        """Positive control for the test above: the words exist and a source
        scan could have found them."""
        import inspect
        from tools.omr.staged import record
        src = inspect.getsource(record)
        for word in CLAIM.all():
            self.assertIn(f'"{word}"', src)


if __name__ == "__main__":
    unittest.main()
