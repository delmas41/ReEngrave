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

The fix is the ONE branch `adjudicate_clef` takes on `_c_family_support`'s
population, keyed on the row's READER: a human witness's row may NAME the
line his own `Q.CLEF_POSITION` measures, snapped to the nearest staff line
with `clef_geometry`'s own table and tolerance; every other reader's row
still only supports a name someone else gave.

⚠️ RUN RED FIRST. Every test below fails against the unrepaired tree except
`TestThePositiveControlCanFail.test_the_control_CAN_FAIL_widen_the_branch_
to_every_reader`, which asserts what the REPAIRED code does under a
deliberately widened gate and therefore needs the repair to exist at all
(`clef_mod._is_human_clef_reader` does not exist on the unrepaired tree, so
that test errors rather than fails RED -- recorded as such in the commit).
"""

from __future__ import annotations

import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import clef as clef_mod
from tools.omr.staged.record import Log, Outcome, Q, READERS

SUB = R.staff(0, 0, 0)


def _log() -> Log:
    return Log()


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
    printed middle line."""

    def test_a_human_alto_box_DECIDES_alto(self):
        log = _log()
        _file_clef_box(log, reader=READERS.SEAN, glyph="clefCAlto",
                        position=4.0829)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, "alto")

    def test_the_naming_term_cites_the_POSITION_row_not_the_glyph_row(self):
        """⚠️ The measurement does the naming, exactly as it does for the CV
        locator (`_locator_terms`) -- citing the glyph row instead would put
        the term in the wrong correlated group and risks double-counting the
        same box against `_c_family_support`'s own glyph-row citation."""
        log = _log()
        _file_clef_box(log, reader=READERS.SEAN, glyph="clefCAlto",
                        position=4.0829)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        pos_row = log.rows(Q.CLEF_POSITION, SUB)[0]
        glyph_row = log.rows(Q.CLEF_GLYPH, SUB)[0]
        self.assertIn(pos_row.id, v.used)
        self.assertNotIn(glyph_row.id, v.used)


class TestAHumanTenorBoxDecidesTenor(unittest.TestCase):
    """One staff line up from alto --
    `clef_geometry.CLEF_BY_FAMILY_LINE["C"][4] == "tenor"`."""

    def test_a_human_box_on_the_tenor_line_DECIDES_tenor(self):
        log = _log()
        _file_clef_box(log, reader=READERS.SEAN, glyph="clefCTenor",
                        position=1.95)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, "tenor")


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


class TestAnAmbiguousPositionDoesNotSnapSilently(unittest.TestCase):
    """A box exactly midway between two staff lines. `clef.py`'s tolerance
    (borrowed from `clef_geometry.DEFAULT_CONFIG.max_residual = 0.35`, one
    line spacing) makes the exact midpoint -- position 3.0, residual 0.5 --
    the genuinely ambiguous case.

    ⚠️ THE BRIEF'S OWN ILLUSTRATIVE VALUE (3.5) IS NOT AMBIGUOUS UNDER THIS
    TOLERANCE -- residual 0.25, comfortably inside 0.35 -- and snaps to alto
    just as confidently as 4.0829 does; asserted below as its own control so
    the claim is not merely asserted in a comment.
    """

    def test_a_position_exactly_between_two_lines_names_NOTHING(self):
        """Idiom picked: NOT a new abstention reason. The row falls back to
        the SAME "supports nothing" honest outcome a detector's row gets
        when nothing else named a candidate (`_c_family_support`'s own
        docstring) -- so with nothing else on the staff, the clef stays
        ABSTAINED `no_candidates`, unchanged from before this fix."""
        log = _log()
        _file_clef_box(log, reader=READERS.SEAN, glyph="clefCAlto",
                        position=3.0)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_candidates")

    def test_an_ambiguous_box_still_SUPPORTS_a_name_someone_else_gave(self):
        """"Falls through", not "discarded" -- the same honest support-only
        path a detector's `clefC` row takes when it cannot name a line
        itself."""
        log = _log()
        _file_clef_box(log, reader=READERS.SEAN, glyph="clefCAlto",
                        position=3.0)
        log.observe(SUB, Q.CLEF_LOCATED, "tenor", reader=READERS.CV_LOCATOR,
                    frame="header_window", score=0.88, family="C", line=4)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertEqual(v.value, "tenor")
        self.assertAlmostEqual(
            v.detail["scores"]["tenor"],
            clef_mod.W_LOCATOR + clef_mod.W_C_FAMILY)

    def test_the_briefs_illustrative_3_5_actually_SNAPS(self):
        """The control for the docstring's own claim above."""
        log = _log()
        _file_clef_box(log, reader=READERS.SEAN, glyph="clefCAlto",
                        position=3.5)
        adjudicate.run(log)
        v = log.verdict(Q.CLEF, SUB)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, "alto")


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


if __name__ == "__main__":
    unittest.main()
