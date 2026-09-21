"""The key-derived alteration reaches `<alter>`, and NOT `<accidental>`.

⚠️ WHAT THIS PINS, and why each half needs its own assertion. `Q.ACCIDENTAL`
is declared "respelled when the key settles" and its only producer is
`consequences.respell_accidental`, which reads the KEY SIGNATURE -- so the row
is a fact about what the note SOUNDS. The staged exporter handed it to
`_mxl_note(accidental=)`, which renders `<accidental>`, the glyph the engraver
DREW. Measured on Litolff Beethoven 5 pp.1-4 that was `<alter>` 0 against
`<accidental>` 221, and through Verovio the file carried 0 sounding
alterations and 221 redundant printed flats.

⚠️ THE TWO ASSERTIONS ARE NOT ONE. A test that only checked `<alter>` appeared
would pass on an exporter that emitted BOTH -- which still prints an
accidental the page does not, on every altered note of the movement. So the
absence of `<accidental>` is asserted separately, and separately again as an
ABSTENTION that is counted rather than a field that was forgotten.
"""
from __future__ import annotations

import unittest

from tools.omr.staged import export as E
from tools.omr import export as _legacy


class TestTheSpellingHelper(unittest.TestCase):
    def test_it_folds_the_alteration_into_the_pitch(self):
        self.assertEqual(E._sounding_pitch("E4", "b"), "Eb4")
        self.assertEqual(E._sounding_pitch("F4", "#"), "F#4")

    def test_the_spelling_round_trips_through_the_LEGACY_parser(self):
        """⚠️ THE HALF A SPELLING TABLE CANNOT PROMISE ON ITS OWN. A spelling
        this module invents that `_parse_pitch` cannot read produces a note
        with NO `<pitch>` block at all -- a silently dropped note, not a
        visible error. So the round trip is asserted against the renderer
        rather than against the table."""
        for pitch, alt, want_alter in (("E4", "b", "<alter>-1</alter>"),
                                       ("F4", "#", "<alter>1</alter>")):
            block = _legacy._mxl_pitch_block(E._sounding_pitch(pitch, alt), "")
            self.assertIsNotNone(block, f"{pitch}+{alt} became unparseable")
            self.assertIn(want_alter, block)

    def test_it_REFUSES_rather_than_stacking_on_an_altered_pitch(self):
        """`Eb4` + `b` must not become `Ebb4` -- a whole tone lower than the
        page prints. `_pitch_from_position` never emits an altered pitch, so
        this is a guard against a FUTURE producer, not a live case.

        ⚠️⚠️ THE FIRST TWO CASES CANNOT REACH THE HAZARD THEY NAME, AND THE
        MUTATION BATTERY IS WHAT SAID SO. Deleting the guard entirely leaves
        `Eb4`+`b` and `F#4`+`#` ANSWERING THE SAME -- the rule REPLACES the
        accidental rather than appending one, so where the alteration matches
        what is already there the two implementations agree. Both arms went
        green on a guard that was not running. The discriminating case is a
        MISMATCH, and it is the dangerous one: without the guard `F#4`+`b`
        becomes `Fb4`, a note a whole tone below the one the page prints.
        """
        self.assertEqual(E._sounding_pitch("Eb4", "b"), "Eb4")
        self.assertEqual(E._sounding_pitch("F#4", "#"), "F#4")
        # the two that actually exercise the guard
        self.assertEqual(E._sounding_pitch("F#4", "b"), "F#4")
        self.assertEqual(E._sounding_pitch("Eb4", "#"), "Eb4")

    def test_an_unknown_alteration_leaves_the_pitch_alone(self):
        """⚠️ A `natural` is alter 0 -- the bare letter -- and there IS a
        fixture for it: `test_staged_duration` injects one to exercise the
        inline-accidental override. It must fall through, not raise and not
        guess."""
        self.assertEqual(E._sounding_pitch("E4", "natural"), "E4")
        self.assertEqual(E._sounding_pitch("E4", "?"), "E4")

    def test_an_unparseable_pitch_is_returned_unchanged(self):
        self.assertEqual(E._sounding_pitch("junk", "b"), "junk")
        self.assertEqual(E._sounding_pitch("", "b"), "")


class TestItReachesTheFile(unittest.TestCase):
    """End to end over a one-note record, because the seam is the point.

    ⚠️ The page is built by `test_staged_export._one_staff_page`, the fixture
    the rest of the staged suite uses, rather than by a second hand-written
    record. A fixture that does not match what GATHER emits tests the test --
    the shape this repo recorded when `TestOwnershipMovesTheLetter` certified
    a page gather cannot produce.
    """

    @staticmethod
    def _record(fifths=-3, pitch="E4", alteration="b", decider=None):
        from .test_staged_export import _one_staff_page, _vrd, QUARTER
        page = _one_staff_page(notes=[(pitch, QUARTER)])
        v = page["record"]["verdicts"]
        v.append(_vrd(950, "staff/0/0/0", "key_signature", fifths))
        if alteration is not None:
            row = _vrd(951, "glyph/0/0/0/0/0", "accidental", alteration,
                       reason="from_key_signature")
            row["decider"] = decider or "respell_accidental"
            v.append(row)
        return page

    def _xml(self, **kw):
        xml, report = E.to_musicxml(self._record(**kw))
        return xml, report

    def test_the_alteration_becomes_alter_and_NOT_accidental(self):
        xml, _ = self._xml()
        self.assertIn("<alter>-1</alter>", xml)
        self.assertIn("<step>E</step>", xml)
        # ⚠️ THE SECOND HALF, AND IT IS NOT IMPLIED BY THE FIRST: an exporter
        # emitting both would pass the assertion above and still print a flat
        # on every altered note of the movement.
        self.assertNotIn("<accidental>", xml)

    def test_a_sharp_key_alters_the_other_way(self):
        xml, _ = self._xml(fifths=2, pitch="F4", alteration="#")
        self.assertIn("<alter>1</alter>", xml)
        self.assertNotIn("<accidental>", xml)

    def test_an_unaltered_note_gets_neither(self):
        """The positive control for the two assertions above: a record with
        no accidental row must produce no `<alter>` either, or they would be
        passing for a reason that has nothing to do with the key."""
        xml, _ = self._xml(alteration=None)
        self.assertNotIn("<alter>", xml)
        self.assertNotIn("<accidental>", xml)

    def test_the_counter_names_what_the_file_HOLDS(self):
        """⚠️ RENAMED RATHER THAN PINNED AT ZERO. `accidentals` counted
        `<accidental>` elements and the exporter now writes none, so keeping
        the name would report an element the file does not contain."""
        _xml, report = self._xml()
        w = report["written"]
        self.assertEqual(w.get("pitches_altered_by_the_key"), 1)
        self.assertNotIn("accidentals", w)

    def test_a_natural_is_not_COUNTED_as_an_alteration(self):
        """It is alter 0, so it neither moves the pitch nor is a note the key
        altered. Guards the counter against the `natural` fixture's shape."""
        xml, report = self._xml(alteration="natural")
        self.assertNotIn("<alter>", xml)
        self.assertEqual(
            report["written"].get("pitches_altered_by_the_key", 0), 0)

    def test_the_UNREAD_printed_glyph_is_reported_as_an_abstention(self):
        """⚠️ A WIRING PASS MAY CONNECT A DECISION; IT MAY NOT LET ONE GUESS.
        The exporter writes no `<accidental>` because nothing reads one -- the
        in-bar accidental is an anonymous `Q.GLYPH_BOX`. That is a gap, and a
        gap that is not counted is indistinguishable from ink nobody read."""
        _xml, report = self._xml()
        block = report["accidental_reading"]
        self.assertEqual(block["printed_glyphs_read_into_a_verdict"], 0)
        self.assertEqual(block["pitches_altered_by_the_key"], 1)
        self.assertIn("printed_glyphs_detected", block)

    def test_that_abstention_figure_is_DERIVED_not_a_literal_zero(self):
        """⚠️ A hardcoded 0 would still read 0 the day a reader of the printed
        glyph lands -- the 'control that computes the wrong thing' family. So
        a verdict written by any OTHER decider must move it."""
        doc = self._record(decider="read_the_printed_glyph")
        _xml, report = E.to_musicxml(doc)
        self.assertEqual(
            report["accidental_reading"]["printed_glyphs_read_into_a_verdict"],
            1)


class TestTheDocumentationClaim(unittest.TestCase):
    def test_NOT_NOTATION_no_longer_claims_the_glyph_is_consumed(self):
        """⚠️ THE TREE CONTRADICTED ITSELF AND ONE SIDE WAS FALSE.
        `NOT_NOTATION["accidental"]` read "consumed into `pitch` and
        `accidental`"; `restate_pitch` reads position + clef and never an
        accidental glyph, and `Q.ACCIDENTAL`'s only producer is the key. The
        other document -- `gather_coverage.FAMILY_Q_IS_ELSEWHERE` -- had it
        right all along."""
        entry = E.NOT_NOTATION["accidental"]
        self.assertNotIn("consumed into", entry)
        self.assertIn("GLYPH_BOX", entry)

    def test_respell_accidental_is_still_the_only_producer(self):
        """⚠️ THE PREMISE THE ROUTING RESTS ON, asserted rather than
        remembered. The alteration may be folded into the pitch only while
        `Q.ACCIDENTAL` means *the key altered this note*. The day a reader of
        the PRINTED glyph files one, that is no longer true and this test is
        where the next author finds out."""
        import inspect
        from tools.omr.staged import consequences
        src = inspect.getsource(consequences)
        writers = [ln for ln in src.splitlines()
                   if "Q.ACCIDENTAL" in ln and "_verdict(" not in ln]
        self.assertTrue(
            any("effect=Q.ACCIDENTAL" in ln for ln in writers),
            "respell_accidental no longer declares Q.ACCIDENTAL as its effect")


if __name__ == "__main__":
    unittest.main()
