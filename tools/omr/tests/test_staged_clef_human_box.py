"""Roadmap 3.4f -- a human clef box reaches the clef decision.

`adjudicate_clef` already reads a human's `Q.CLEF_GLYPH` / `Q.CLEF_POSITION`
rows -- `review/human_evidence.py` files the SAME two rows `gather_clef`
files for a detected clef (roadmap 3.4c) -- and used NEITHER for a C clef:
`_clef_of` maps only G/F/percussion by class name, and `_c_family_support`
only let a `clefC*` row SUPPORT a C clef the CV locator had already named.

Measured on Sean's own `act-0001`
(`benchmarks/omr-stage-review-2026-09/FINDINGS.md` §C7a, `staff/3/0/9`): a
relabel to `clefCAlto` filed `Q.CLEF_POSITION` = 4.0829 (0.083 of a step off
the printed middle line) and the clef stayed ABSTAINED `no_candidates` --
both rows sat in `basis` and neither reached `used`.

⚠️⚠️ MANAGER REVIEW OF THE FIRST CUT (which let geometry decide the line
UNCONDITIONALLY): `review/static/labels.js` offers THREE C-clef choices --
`clefC` ("alto or tenor -- unplaced"), `clefCAlto`, `clefCTenor`. Clicking a
SPECIFIC one is a READING, not a class-only guess, so geometry may not
silently overrule it. `_human_named_c_clef` now reconciles a human's own
class choice against his own measured position, four ways
(`_human_class_name` tells "unplaced" from "specific"):

  * UNPLACED (`clefC`)                    -> geometry alone names the line.
  * specific class, geometry AGREES       -> decide it, citing BOTH rows.
  * specific class, geometry names ANOTHER line
                                           -> CONTRADICTION: name NOTHING,
                                              fall through to plain support,
                                              `CONTRADICTION_REASON` in detail.
  * specific class, position UNSNAPPABLE  -> the class name decides ALONE.

⚠️ RUN RED FIRST, TWICE. The original RED (7 failed, 3 passed) is against the
tree with no reader-keyed branch at all. This file's SECOND wave -- the four
classes below reconciling class against geometry -- was run RED again
against the FIRST (geometry-always-wins) cut of this branch; see the commit
message for those counts. `TestThePositiveControlCanFail.test_the_control_
CAN_FAIL_widen_the_branch_to_every_reader` needs the repair to exist at all
to run (`_is_human_clef_reader` does not exist before it), so it errors
rather than fails on the ORIGINAL unrepaired tree -- recorded as such in the
first commit.
"""

from __future__ import annotations

import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import clef as clef_mod
from tools.omr.staged.record import Log, Outcome, Q, READERS
from tools.omr.tests._staged_fixtures import fresh_log as _log

SUB = R.staff(0, 0, 0)


def _file_clef_box(log: Log, *, reader: str, glyph: str, position: float,
                    y_center: float = 180.0) -> None:
    """The two rows `review/human_evidence.py` files for ONE clef-class box
    in cell 0, reproduced directly at the shape the existing clef tests use
    (`test_staged_c_clef.py`) rather than through the review ingest module,
    which needs a cell/grid/PDF fixture this test has no reason to build.
    """
    log.observe(SUB, Q.CLEF_GLYPH, glyph, reader=reader, frame="cell:0",
                y_center=y_center, x_center=50.0)
    log.observe(SUB, Q.CLEF_POSITION, position, reader=reader, frame="cell:0",
                glyph=glyph, y_center=y_center)


class TestAHumanAltoBoxDecidesAlto(unittest.TestCase):
    """The positive case -- Sean's own act-0001 shape (§C7a): a `clefCAlto`
    box whose measured position is a few hundredths of a step off the
    printed middle line. His class (`alto`) and his own geometry (the middle
    line) AGREE -- the CONFIRMED case."""

    def test_a_human_alto_box_DECIDES_alto(self):
        log = _log()
        _file_clef_box(log, reader=READERS.SEAN, glyph="clefCAlto",
                        position=4.0829)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, "alto")

    def test_the_confirmed_case_cites_BOTH_rows(self):
        """⚠️ CHANGED BY MANAGER REVIEW. The first cut cited the POSITION row
        only (to dodge a correlation risk that turned out to apply to a
        different case). Where his class and his geometry agree, both of his
        own witnesses corroborate one answer and both are cited -- this is
        `clef.py`'s first multi-row term, which is why `adjudicate_clef`'s
        own `used=` construction had to stop taking only `rows[0]`."""
        log = _log()
        _file_clef_box(log, reader=READERS.SEAN, glyph="clefCAlto",
                        position=4.0829)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        pos_row = log.rows(Q.CLEF_POSITION, SUB)[0]
        glyph_row = log.rows(Q.CLEF_GLYPH, SUB)[0]
        self.assertIn(pos_row.id, v.used)
        self.assertIn(glyph_row.id, v.used)


class TestAHumanTenorBoxDecidesTenor(unittest.TestCase):
    """One staff line up from alto --
    `clef_geometry.CLEF_BY_FAMILY_LINE["C"][4] == "tenor"`. His class
    (`tenor`) and his geometry AGREE here too."""

    def test_a_human_box_on_the_tenor_line_DECIDES_tenor(self):
        log = _log()
        _file_clef_box(log, reader=READERS.SEAN, glyph="clefCTenor",
                        position=1.95)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, "tenor")

    def test_clefCTenor_at_the_tenor_line_is_ALSO_the_confirmed_case(self):
        """The manager's own worked example: `clefCTenor` at position 2.0
        (exactly the tenor line) -- class and geometry agree, both cited."""
        log = _log()
        _file_clef_box(log, reader=READERS.SEAN, glyph="clefCTenor",
                        position=2.0)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, "tenor")
        pos_row = log.rows(Q.CLEF_POSITION, SUB)[0]
        glyph_row = log.rows(Q.CLEF_GLYPH, SUB)[0]
        self.assertIn(pos_row.id, v.used)
        self.assertIn(glyph_row.id, v.used)


class TestThePositiveControlCanFail(unittest.TestCase):
    """⚠️ THE CONTROL THAT MUST STILL REFUSE. The DETECTOR's own `clefCAlto`
    box, same position -- the class still cannot name a line, exactly as
    `_clef_of` and `_c_family_support`'s docstrings say it must not. CLAUDE.md
    rule 7: a control must be able to fail, so the second test below widens
    the reader gate to admit every reader and confirms the SAME fixture then
    names alto -- proving the first test is exercising the reader check and
    not passing for some unrelated reason."""

    def test_the_detectors_own_box_still_ABSTAINS(self):
        log = _log()
        _file_clef_box(log, reader=READERS.DETECTOR, glyph="clefCAlto",
                        position=4.0829)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_candidates")

    def test_the_control_CAN_FAIL_widen_the_branch_to_every_reader(self):
        """Patched and reverted within the `with` block; nothing here is
        left widened afterwards."""
        log = _log()
        _file_clef_box(log, reader=READERS.DETECTOR, glyph="clefCAlto",
                        position=4.0829)
        with mock.patch.object(clef_mod, "_is_human_clef_reader",
                               lambda reader: True):
            adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, "alto")
        # ⚠️ AND THE GATE IS BACK OFF, the same DETECTOR fixture abstains
        # again -- so the widening above was not a permanent side effect of
        # importing the module.
        log2 = _log()
        _file_clef_box(log2, reader=READERS.DETECTOR, glyph="clefCAlto",
                        position=4.0829)
        adjudicate.run(log2)
        v2 = log2.verdict(Q.CLEF, SUB)
        self.assertIs(v2.outcome, Outcome.ABSTAINED)


class TestUnplacedClefCLeavesGeometryToDecide(unittest.TestCase):
    """`clefC` -- "C clef (alto or tenor -- unplaced)" in the review palette
    -- is exactly as unplaced as a detector's own `clefC` box. He named a C
    clef and nothing more, so geometry alone may name the line, exactly as
    for the CV locator."""

    def test_unplaced_clefC_on_the_tenor_line_DECIDES_tenor(self):
        log = _log()
        _file_clef_box(log, reader=READERS.SEAN, glyph="clefC", position=2.0)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, "tenor")
        # Geometry alone names it -- the POSITION row, not the glyph row
        # (`_locator_terms`'s own idiom), because the class claimed nothing.
        pos_row = log.rows(Q.CLEF_POSITION, SUB)[0]
        glyph_row = log.rows(Q.CLEF_GLYPH, SUB)[0]
        self.assertIn(pos_row.id, v.used)
        self.assertNotIn(glyph_row.id, v.used)


class TestAContradictionNamesNothing(unittest.TestCase):
    """⚠️ THE CASE THE FIRST CUT GOT WRONG. `clefCAlto` at position 2.0 is
    the TENOR line, not the alto line his class reading claims -- two of his
    own witnesses disagree. Geometry does not get to overrule the class he
    read (the first cut's bug: this used to decide `tenor`), and the class
    does not get to overrule the position he measured either: NAME NOTHING,
    fall through to plain support, and say why."""

    def test_clefCAlto_on_the_tenor_line_names_NOTHING(self):
        log = _log()
        _file_clef_box(log, reader=READERS.SEAN, glyph="clefCAlto",
                        position=2.0)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_candidates")
        self.assertNotEqual(v.value, "tenor")
        self.assertNotEqual(v.value, "alto")

    def test_the_contradiction_is_VISIBLE_in_detail_so_trace_shows_it(self):
        """CLAUDE.md rule 8: a fallback never turns "cannot tell" into an
        answer -- and it must not turn it into SILENCE either. The reason
        belongs in `detail` even though the verdict abstained, because an
        abstention that hides WHY a human's own row named nothing would be
        exactly the silence the rule forbids."""
        log = _log()
        _file_clef_box(log, reader=READERS.SEAN, glyph="clefCAlto",
                        position=2.0)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        glyph_row = log.rows(Q.CLEF_GLYPH, SUB)[0]
        entries = v.detail[clef_mod.CONTRADICTION_REASON]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["glyph_row"], glyph_row.id)
        self.assertEqual(entries[0]["reason"], clef_mod.CONTRADICTION_REASON)

    def test_a_contradicting_row_STILL_supports_a_name_someone_else_gave(self):
        """Falling through means falling through to the SAME support-only
        path a detector's row takes -- not disappearing. The locator names
        `tenor` independently; the human's contradicting row still adds
        `W_C_FAMILY` to it, exactly as an ordinary detector `clefC*` row
        would."""
        log = _log()
        _file_clef_box(log, reader=READERS.SEAN, glyph="clefCAlto",
                        position=2.0)
        log.observe(SUB, Q.CLEF_LOCATED, "tenor", reader=READERS.CV_LOCATOR,
                    frame="header_window", score=0.88, family="C", line=4)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertEqual(v.value, "tenor")
        self.assertAlmostEqual(
            v.detail["scores"]["tenor"],
            clef_mod.W_LOCATOR + clef_mod.W_C_FAMILY)


class TestASpecificClassNamesAloneWhenUnconfirmable(unittest.TestCase):
    """A box exactly midway between two staff lines (`clef.py`'s tolerance,
    borrowed from `clef_geometry.DEFAULT_CONFIG.max_residual = 0.35` of one
    line spacing -- position 3.0, residual 0.5, is comfortably over it: the
    genuinely ambiguous position). Geometry has nothing to CONFIRM or
    CONTRADICT him with here, so a SPECIFIC class reading stands alone --
    the box was drawn loosely, not wrongly.

    ⚠️ THE ORIGINAL BRIEF'S OWN ILLUSTRATIVE VALUE (3.5) IS NOT AMBIGUOUS
    UNDER THIS TOLERANCE -- residual 0.25, inside 0.35 -- and reaches the
    CONFIRMED case exactly like 4.0829 does; see
    `test_the_briefs_illustrative_3_5_actually_SNAPS`.
    """

    def test_a_specific_class_with_an_unsnappable_position_names_ALONE(self):
        log = _log()
        _file_clef_box(log, reader=READERS.SEAN, glyph="clefCAlto",
                        position=3.0)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, "alto")
        # Named ALONE: the glyph row (the class IS the reading), not the
        # position row -- geometry contributed nothing here.
        glyph_row = log.rows(Q.CLEF_GLYPH, SUB)[0]
        pos_row = log.rows(Q.CLEF_POSITION, SUB)[0]
        self.assertIn(glyph_row.id, v.used)
        self.assertNotIn(pos_row.id, v.used)

    def test_the_briefs_illustrative_3_5_actually_SNAPS(self):
        """Not the "unconfirmable" case at all -- 3.5 snaps to alto
        (residual 0.25 < 0.35) and reaches the CONFIRMED case, citing both
        rows, exactly like 4.0829."""
        log = _log()
        _file_clef_box(log, reader=READERS.SEAN, glyph="clefCAlto",
                        position=3.5)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, "alto")
        glyph_row = log.rows(Q.CLEF_GLYPH, SUB)[0]
        pos_row = log.rows(Q.CLEF_POSITION, SUB)[0]
        self.assertIn(glyph_row.id, v.used)
        self.assertIn(pos_row.id, v.used)


class TestAnUnplacedAmbiguousPositionStillNamesNothingItself(unittest.TestCase):
    """The UNPLACED (`clefC`) analogue of the class above: with no class
    reading to fall back on AND a position that will not snap, the row
    genuinely has nothing to offer beyond plain family support."""

    def test_unplaced_at_an_ambiguous_position_names_NOTHING(self):
        log = _log()
        _file_clef_box(log, reader=READERS.SEAN, glyph="clefC", position=3.0)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_candidates")

    def test_unplaced_ambiguous_STILL_supports_a_name_someone_else_gave(self):
        """"Falls through", not "discarded" -- the same honest support-only
        path a detector's `clefC` row takes when it cannot name a line
        itself."""
        log = _log()
        _file_clef_box(log, reader=READERS.SEAN, glyph="clefC", position=3.0)
        log.observe(SUB, Q.CLEF_LOCATED, "tenor", reader=READERS.CV_LOCATOR,
                    frame="header_window", score=0.88, family="C", line=4)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertEqual(v.value, "tenor")
        self.assertAlmostEqual(
            v.detail["scores"]["tenor"],
            clef_mod.W_LOCATOR + clef_mod.W_C_FAMILY)


class TestOnlyTheClosedHumanReadersQualify(unittest.TestCase):
    """⚠️ SESSION_TEST counts too, and that is not a relaxation of the gate.
    This lane's own real-case artefact
    (`benchmarks/omr-stage-review-2026-09/out/relabel-clefCAlto.sidecar.json`,
    `staff/3/0/9`) is itself stamped `"session-test"`, not `"sean"`, and
    `ownership._human_owner` / `notehead_precision._human_not_a_symbol`
    already treat both identically for the documented reason: a session
    standing in for a person exercises the SAME wiring a real reading
    would."""

    def test_a_SESSION_TEST_box_also_names_its_line(self):
        log = _log()
        _file_clef_box(log, reader=READERS.SESSION_TEST, glyph="clefCAlto",
                        position=4.0829)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertEqual(v.value, "alto")

    def test_a_machine_reader_never_qualifies(self):
        for reader in (READERS.DETECTOR, READERS.GEOMETRY, READERS.CV_LOCATOR,
                       READERS.SPECIALIST, READERS.DETECTOR_HEADER):
            self.assertFalse(clef_mod._is_human_clef_reader(reader), reader)
        self.assertTrue(clef_mod._is_human_clef_reader(READERS.SEAN))
        self.assertTrue(clef_mod._is_human_clef_reader(READERS.SESSION_TEST))


class TestHumanClassNameHelper(unittest.TestCase):
    """`_human_class_name` is the one place "unplaced" is told apart from
    "specific" -- pinned directly since `clef_geometry.clef_name_from_class`
    alone cannot tell them apart (it defaults the unplaced case to `alto`)."""

    def test_unplaced_clefC_has_no_class_name(self):
        self.assertIsNone(clef_mod._human_class_name("clefC"))

    def test_clefCAlto_names_alto(self):
        self.assertEqual(clef_mod._human_class_name("clefCAlto"), "alto")

    def test_clefCTenor_names_tenor(self):
        self.assertEqual(clef_mod._human_class_name("clefCTenor"), "tenor")


if __name__ == "__main__":
    unittest.main()
