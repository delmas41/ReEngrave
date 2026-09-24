"""The key signature read off the DETECTOR's boxes, and the system check.

⚠️ COHERENCE, NOT ACCURACY — every fixture here is hand-built, so these say
what the rule DOES, never how often it is right. The accuracy figures live in
`benchmarks/omr-key-majority-2026-09/FINDINGS.md`, measured on three real
records.

⚠️ RUN RED FIRST. Every test in this file was run against the unrepaired tree
(commit 259773e5) before the rule existed: the marker tests failed with the
verdict reading the header FITTER's value, the system-check tests failed
because `Q.SYSTEM_KEY` did not exist, and the transposition test passed for
the wrong reason (nothing was normalising anything, so nothing could flatten
it) — which is why it is paired with a case that MUST supersede.
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS

#: One staff space in the CELL's canonical frame, as the engraved fixture
#: measures it. The printed slots stand about one space apart.
SPACE = 85.0


def _staff(log, staff_index, *, clef="treble", label=None, markers=(),
           fit=None, template=None, page=0, system=0):
    """One staff of one system, with whatever its header held."""
    sub = R.staff(page, system, staff_index)
    log.observe(sub, Q.CLEF_GLYPH,
                {"treble": "clefG", "bass": "clefF", "alto": "clefC"}[clef],
                reader=READERS.DETECTOR, frame="cell:0", score=0.95)
    log.observe(R.cell(page, system, staff_index, 0), Q.CELL_STAFF_SPACE,
                SPACE, reader=READERS.GEOMETRY, frame="cell:0")
    if label is not None:
        log.observe(sub, Q.MARGIN_LABEL, label, reader=READERS.TEXT_LAYER,
                    frame="page")
    for kind, x in markers:
        log.observe(sub, Q.KEYSIG_MARKER, kind, reader=READERS.DETECTOR,
                    frame="cell:0", score=0.92, x=x, y_center=500)
    if fit is not None:
        log.observe(sub, Q.KEYSIG_CLEF_FIT, clef, reader=READERS.CV_HEADER,
                    frame="header_window", n_accidentals=abs(fit),
                    accidental="b" if fit < 0 else "#", decided_by="pattern",
                    fifths=fit)
    if template is not None:
        log.observe(sub, Q.KEYSIG_TEMPLATE_FIT, clef, reader=READERS.TEMPLATE,
                    frame="header_window", n_accidentals=abs(template),
                    accidental="b" if template < 0 else "#", fifths=template)
    return sub


def _flats(n, x0=375.0):
    return [("keyFlat", x0 + i * SPACE) for i in range(n)]


class TestTheDetectorsBoxesAreTheReading(unittest.TestCase):
    """⚠️ The rows were declared in `wants` and read by NOTHING until
    2026-09-23. Sean: *"we just need to know what to do with the 3 boxes
    around the 3 flats on every staff."*"""

    def test_three_flat_boxes_beat_a_fit_that_says_one(self):
        log = Log()
        sub = _staff(log, 0, markers=_flats(3), fit=-1)
        adjudicate.run(log)
        v = log.verdict(Q.KEY_SIGNATURE, sub)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, -3)
        self.assertEqual(v.reason, "markers")

    def test_the_losing_fit_is_RECORDED_not_dropped(self):
        """⚠️ A reader that was overruled is the measurement of which reader
        to work on next; discarding it is how a defect becomes invisible."""
        log = Log()
        sub = _staff(log, 0, markers=_flats(3), fit=-1)
        adjudicate.run(log)
        v = log.verdict(Q.KEY_SIGNATURE, sub)
        said = v.detail.get("disagreeing_readers")
        self.assertTrue(said, "the disagreeing fit must be on the record")
        self.assertEqual(said[0]["fifths"], -1)
        self.assertEqual(said[0]["reader"], READERS.CV_HEADER)

    def test_an_agreeing_fit_joins_the_basis(self):
        log = Log()
        sub = _staff(log, 0, markers=_flats(3), fit=-3)
        adjudicate.run(log)
        v = log.verdict(Q.KEY_SIGNATURE, sub)
        self.assertEqual(v.value, -3)
        self.assertEqual(v.detail.get("corroborated_by"), 1)
        self.assertNotIn("disagreeing_readers", v.detail)

    def test_sharps_read_positive(self):
        log = Log()
        sub = _staff(log, 0, markers=[("keySharp", 375.0 + i * SPACE)
                                      for i in range(2)])
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.KEY_SIGNATURE, sub).value, 2)

    def test_two_boxes_at_ONE_x_are_ONE_slot(self):
        """⚠️ The cell is padded 4 staff spaces and on a conductor's page that
        reaches the next staff's ink; on the engraved fixture Violin 1 carries
        a second box 2 px from the middle flat. Counting BOXES reads four."""
        log = Log()
        marks = _flats(3) + [("keyFlat", 375.0 + SPACE + 2.0)]
        sub = _staff(log, 0, markers=marks)
        adjudicate.run(log)
        v = log.verdict(Q.KEY_SIGNATURE, sub)
        self.assertEqual(v.value, -3)
        self.assertEqual(v.detail["keysig_marker_ink"], 4)
        self.assertEqual(v.detail["keysig_marker_slots"], 3)

    def test_a_mark_inside_the_first_BAR_is_not_in_the_run(self):
        """⚠️ `_gather_keysig_markers` reads the whole first MEASURE, so an
        accidental printed in bar 1 is in this population. The ladder stops."""
        log = Log()
        marks = _flats(3) + [("keyFlat", 375.0 + 9 * SPACE)]
        sub = _staff(log, 0, markers=marks)
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.KEY_SIGNATURE, sub).value, -3)

    def test_flats_and_sharps_in_one_run_abstain(self):
        log = Log()
        sub = _staff(log, 0, markers=[("keyFlat", 375.0),
                                      ("keyFlat", 375.0 + SPACE),
                                      ("keySharp", 375.0 + 2 * SPACE)],
                     fit=-2)
        adjudicate.run(log)
        v = log.verdict(Q.KEY_SIGNATURE, sub)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "mixed_marker_kinds")

    def test_a_run_longer_than_seven_abstains(self):
        log = Log()
        sub = _staff(log, 0, markers=_flats(8))
        adjudicate.run(log)
        v = log.verdict(Q.KEY_SIGNATURE, sub)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "too_many_markers")

    def test_with_no_measured_cell_space_it_refuses_rather_than_guessing(self):
        """⚠️ The slot test has no unit without one, and the nominal is wrong
        on half the cells of a conductor's page."""
        log = Log()
        sub = R.staff(0, 0, 0)
        log.observe(sub, Q.CLEF_GLYPH, "clefG", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.95)
        for kind, x in _flats(3):
            log.observe(sub, Q.KEYSIG_MARKER, kind, reader=READERS.DETECTOR,
                        frame="cell:0", score=0.92, x=x, y_center=500)
        adjudicate.run(log)
        v = log.verdict(Q.KEY_SIGNATURE, sub)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_cell_scale")


class TestWhereTheDetectorSaidNothingTheFitterStillSpeaks(unittest.TestCase):
    """⚠️ THE BRANCH THAT MAKES THE MARKER RULE SURVIVABLE ON A SCAN. Litolff
    MERGES its ink and the detector misses runs the template reads; where
    there is no box there is nothing to contradict."""

    def test_no_markers_and_a_fit_of_minus_one(self):
        log = Log()
        sub = _staff(log, 0, fit=-1)
        adjudicate.run(log)
        v = log.verdict(Q.KEY_SIGNATURE, sub)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, -1)
        self.assertEqual(v.reason, "fitted_no_markers")

    def test_a_template_answers_where_the_locator_did_not(self):
        log = Log()
        sub = _staff(log, 0, template=-3)
        adjudicate.run(log)
        v = log.verdict(Q.KEY_SIGNATURE, sub)
        self.assertEqual(v.value, -3)
        self.assertEqual(v.detail.get("decided_by"), "template")

    def test_an_EMPTY_header_reads_zero_and_stays_zero(self):
        """A natural horn prints no signature; the template answers 0 and the
        system check must leave it alone — it is not a dissenter."""
        log = Log()
        strings = [_staff(log, i, clef="bass", label=n, markers=_flats(3))
                   for i, n in enumerate(["Violoncello.", "Basso."])]
        horn = _staff(log, 2, label="Corni in Es.", template=0)
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.KEY_SIGNATURE, horn).value, 0)
        for sub in strings:
            self.assertEqual(log.verdict(Q.KEY_SIGNATURE, sub).value, -3)

    def test_a_staff_printing_no_signature_does_not_VOTE_either(self):
        """⚠️ `[C81]`: a trumpet reads 0 whatever the key. If it could vote it
        would stand as a second witness for 0 and make a real dissent look
        corroborated."""
        log = Log()
        _staff(log, 0, label="Trombe in C.", template=0)
        _staff(log, 1, label="Timpani in C.G.", clef="bass", template=0)
        adjudicate.run(log)
        v = log.verdict(Q.SYSTEM_KEY, R.system(0, 0))
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_staff_read_a_key")


class TestTheSystemCheck(unittest.TestCase):
    """⚠️ A CHECK, NOT A VOTE. It abstains a staff whose concert key has NO
    peer; it never writes another staff's value onto it."""

    def test_a_lone_dissenter_is_superseded_and_carries(self):
        log = Log()
        for i, name in enumerate(["Flauti.", "Obol.", "Violino I."]):
            _staff(log, i, label=name, markers=_flats(3))
        odd = _staff(log, 3, label="Violino II.", markers=_flats(1))
        adjudicate.run(log)
        v = log.verdict(Q.KEY_SIGNATURE, odd)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "disagrees_with_system")
        self.assertEqual(v.detail["concert_fifths"], -1)
        self.assertEqual(v.detail["written_fifths"], -1)

    def test_two_staves_reading_alike_are_never_touched(self):
        """⚠️ A majority would have overwritten both. A bitonal system, and a
        page this reader half-misreads, must lose nothing.

        ⚠️⚠️ AND ROADMAP 2.9b LATER TOOK THE SECOND HALF OF THAT SENTENCE
        BACK, ON SEAN'S ADJUDICATION OF FOUR CROPS — so this test runs with
        `OMR_PART_KEY` OFF and says what it is asserting. The SYSTEM check
        still never touches a corroborated pair; what changed is that the
        DOCUMENT may, because *every non-transposing staff of both count pages
        prints three flats* and a pair reading one flat on one system of a
        movement in C minor is two readers failing together (CLAUDE.md §10).
        `test_staged_key_by_part.TestTheDocumentCheck` asserts the new
        behaviour on this same fixture; the flag is what separates the two
        claims, and a genuinely bitonal document still loses nothing because
        the document majority is taken over the stretch its own corroborated
        changes cut.
        """
        log = Log()
        keep = [_staff(log, i, label=n, markers=_flats(3))
                for i, n in enumerate(["Flauti.", "Obol.", "Violino I."])]
        pair = [_staff(log, 3 + i, label=n, markers=_flats(1))
                for i, n in enumerate(["Violino II.", "Viola."])]
        with mock.patch.dict(os.environ, {"OMR_PART_KEY": "0"}):
            adjudicate.run(log)
        for sub in keep:
            self.assertEqual(log.verdict(Q.KEY_SIGNATURE, sub).value, -3)
        for sub in pair:
            v = log.verdict(Q.KEY_SIGNATURE, sub)
            self.assertIs(v.outcome, Outcome.DECIDED)
            self.assertEqual(v.value, -1)

    def test_one_witness_cannot_contradict_itself(self):
        log = Log()
        only = _staff(log, 0, label="Flauti.", markers=_flats(3))
        _staff(log, 1, label="Corni in Es.", template=0)
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.SYSTEM_KEY, R.system(0, 0)).reason,
                         "one_staff_only")
        self.assertEqual(log.verdict(Q.KEY_SIGNATURE, only).value, -3)

    def test_the_check_does_not_flatten_a_TRANSPOSITION(self):
        """⚠️⚠️ THE POSITIVE CONTROL. A B-flat clarinet in C minor prints ONE
        flat beside strings printing three, and both are right: normalised to
        concert they are the same key. A check comparing WRITTEN values would
        supersede the clarinet on every orchestral page ever printed."""
        log = Log()
        strings = [_staff(log, i, label=n, markers=_flats(3))
                   for i, n in enumerate(["Violino I.", "Violino II."])]
        clar = _staff(log, 2, label="Clarinetti in B.", markers=_flats(1))
        adjudicate.run(log)
        for sub in strings:
            self.assertEqual(log.verdict(Q.KEY_SIGNATURE, sub).value, -3)
        v = log.verdict(Q.KEY_SIGNATURE, clar)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, -1, "the clarinet keeps its WRITTEN key")
        self.assertEqual(v.detail["concert_fifths"], -3)

    def test_a_clarinet_whose_label_never_NAMED_its_key_is_left_alone(self):
        """⚠️ The lexicon's default is a convention, not a reading, and the
        obvious test for it is wrong — the default clarinet IS the B-flat one.
        A staff resting on it may neither corroborate nor be contradicted."""
        log = Log()
        for i, n in enumerate(["Violino I.", "Violino II."]):
            _staff(log, i, label=n, markers=_flats(3))
        bare = _staff(log, 2, label="Cl.", markers=_flats(2))
        adjudicate.run(log)
        v = log.verdict(Q.KEY_SIGNATURE, bare)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, -2)

    def test_the_system_verdict_NAMES_the_rows_it_counted(self):
        """⚠️ A tally with no basis is a number; a tally whose `used` names
        every marker row it counted is EVIDENCE, and it is what lets a reader
        of the record ask which staff moved the count."""
        log = Log()
        subs = [_staff(log, i, label=n, markers=_flats(3))
                for i, n in enumerate(["Flauti.", "Obol."])]
        adjudicate.run(log)
        v = log.verdict(Q.SYSTEM_KEY, R.system(0, 0))
        self.assertTrue(v.used, "the counted rows must be named")
        self.assertTrue(set(v.used) <= set(v.considered))
        self.assertEqual(v.detail["staves"], len(subs))
        self.assertEqual(v.detail["staves_with_a_reading"], 2)
        self.assertEqual(v.declined, ())

    def test_the_system_tally_is_on_the_record(self):
        log = Log()
        for i, n in enumerate(["Flauti.", "Obol."]):
            _staff(log, i, label=n, markers=_flats(3))
        _staff(log, 2, label="Clarinetti in B.", markers=_flats(1))
        adjudicate.run(log)
        v = log.verdict(Q.SYSTEM_KEY, R.system(0, 0))
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["tally"], {"-3": 3})
        self.assertEqual(v.value["corroborated"], [-3])


if __name__ == "__main__":
    unittest.main()
