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
from tools.omr.staged.record import Q
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


#: ⚠️ A SCALE THAT IS NOT 1 AND AN ORIGIN THAT IS NOT 0, DELIBERATELY. The
#: canonical and page frames differ by both here (heads are 40 canonical units
#: wide and 20 page px, at page origin 1050/500), so a conversion that dropped
#: the scale, or the offset, or confused corners with widths, produces a
#: visibly wrong span. This repo has already paid for a fixture at the origin
#: where "the two spellings agree in every coordinate" and a frame error
#: passed every assertion.
_CANON_W, _PAGE_W = 40.0, 20.0
_SCALE = _PAGE_W / _CANON_W          # 0.5
EIGHTH = {"beats": 0.5, "written": 0.5, "dots": 0, "beam_levels": 1}


def _beamed_page(n_notes=4, beam_levels=1, beam_box=True, page_boxes=True):
    """`n_notes` eighths in one cell, optionally under one beam stroke."""
    from .test_staged_export import _log_json, _obs, _vrd
    obs, vrd = [], []
    i = 0
    for gi in range(n_notes):
        sub = f"glyph/0/0/0/0/{gi}"
        cx = 100.0 + 100.0 * gi
        detail = {"category": "notehead"}
        if page_boxes:
            px = 1050.0 + (cx - 100.0) * _SCALE
            # ⚠️ CORNERS, which is what `detail["bbox_page_px"]` carries and
            # what `_corners_to_wh` converts. Handing widths here would be the
            # recorded corner/width trap.
            detail["bbox_page_px"] = [px, 500.0, px + _PAGE_W, 500.0 + _PAGE_W]
        obs.append(_obs(i, sub, Q.GLYPH_BOX,
                        ["noteheadBlackOnLine", cx, 50.0, _CANON_W, _CANON_W],
                        **detail))
        i += 1
        obs.append(_obs(i, sub, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine"))
        i += 1
        vrd.append(_vrd(i, sub, Q.PITCH, "C5"))
        i += 1
        dur = dict(EIGHTH, beam_levels=beam_levels)
        vrd.append(_vrd(i, sub, Q.DURATION, dur))
        i += 1
    if beam_box:
        # one stroke spanning every head, in the CELL's canonical frame
        span = 100.0 * (n_notes - 1) + _CANON_W
        obs.append(_obs(500, "cell/0/0/0/0", Q.BEAM_STROKE,
                        [100.0, 20.0, span, 10.0]))
    vrd.append(_vrd(900, "staff/0/0/0", Q.MEASURE_PARTITION, 1))
    vrd.append(_vrd(901, "staff/0/0/0", Q.CLEF, "treble"))
    vrd.append(_vrd(902, "system/0/0", Q.SYSTEM_STAFF_COUNT, 1))
    vrd.append(_vrd(903, "document", Q.PART_PARTITION,
                    {"join": "ordinal", "staves_per_system": 1},
                    reason="ordinal"))
    return _log_json(obs, vrd)


class TestTheBeamReachesTheFile(unittest.TestCase):
    """⚠️ In MusicXML an absent `<beam>` IS a flag — MEASURED, not assumed.
    `probe/renderer_semantics.py` puts four eighths through Verovio with and
    without the element: with it, one beam and no flag glyphs; without it,
    **four `flag8thDown` glyphs**. On the real artefact the same swap takes
    page 1 from 574 flags / 0 beams to 82 flags / 171 beams.
    """

    def test_a_beamed_group_gets_begin_continue_end(self):
        xml, _ = E.to_musicxml(_beamed_page(n_notes=4))
        self.assertIn('<beam number="1">begin</beam>', xml)
        self.assertIn('<beam number="1">continue</beam>', xml)
        self.assertIn('<beam number="1">end</beam>', xml)
        self.assertEqual(xml.count('<beam number="1">begin</beam>'), 1)
        self.assertEqual(xml.count('<beam number="1">end</beam>'), 1)

    def test_begin_and_end_BALANCE(self):
        """The structural invariant a beam must satisfy, and the one a wrong
        grouping breaks. It holds on both real documents at every level."""
        import re
        import collections
        xml, _ = E.to_musicxml(_beamed_page(n_notes=4, beam_levels=2))
        c = collections.Counter(
            re.findall(r'<beam number="(\d+)">([a-z ]+)</beam>', xml))
        levels = {lv for lv, _ in c}
        self.assertTrue(levels, "no beams written at all")
        for lv in levels:
            self.assertEqual(c[(lv, "begin")], c[(lv, "end")],
                             f"level {lv} is unbalanced")

    def test_a_SECOND_level_is_written_for_a_sixteenth(self):
        xml, _ = E.to_musicxml(_beamed_page(n_notes=4, beam_levels=2))
        self.assertIn('<beam number="2">', xml)

    def test_NO_beam_box_leaves_every_note_flagged(self):
        """⚠️ THE ADDITIVE PROPERTY, and it is why this needs no flag: where
        the CV read no stroke the file does not move. A lone eighth IS
        flagged, so writing a beam here would be the invention."""
        xml, _ = E.to_musicxml(_beamed_page(n_notes=4, beam_box=False))
        self.assertNotIn("<beam", xml)

    def test_a_cell_with_no_frame_RULER_refuses_and_is_counted(self):
        """⚠️ A WIRING PASS MAY CONNECT A DECISION; IT MAY NOT LET ONE GUESS.
        Without a head carrying both frames there is no scale, so the strokes
        cannot be placed — and the refusal is COUNTED rather than silent."""
        xml, report = E.to_musicxml(_beamed_page(n_notes=4, page_boxes=False))
        self.assertNotIn("<beam", xml)
        self.assertGreaterEqual(
            report["written"].get("beam_cells_without_a_frame_ruler", 0), 1)

    def test_the_counter_reports_what_the_file_HOLDS(self):
        xml, report = E.to_musicxml(_beamed_page(n_notes=4))
        self.assertEqual(report["written"].get("beams"), xml.count("<beam "))

    def test_two_voices_get_their_OWN_runs(self):
        """⚠️⚠️ `annotate_beams`' own docstring says it "must be called PER
        VOICE": two voices interleave in x, so a run computed across both is
        broken by the other voice's notes. On a ONE-voice fixture that call
        is an equivalent mutant — the battery said so — and only a two-voice
        bar can tell the two apart.

        Four notes under one stroke, split 0,2 / 1,3. Per voice that is TWO
        runs (two begins, two ends). Across both voices it is ONE.
        """
        from .test_staged_export import _vrd
        doc = _beamed_page(n_notes=4)
        doc["record"]["verdicts"].append(
            _vrd(960, "cell/0/0/0/0", Q.VOICES,
                 {"n_voices": 2, "voices": [[0, 2], [1, 3]],
                  "rests_in_every_voice": []}))
        xml, _ = E.to_musicxml(doc)
        self.assertEqual(xml.count('<beam number="1">begin</beam>'), 2)
        self.assertEqual(xml.count('<beam number="1">end</beam>'), 2)

    def test_the_beam_level_comes_from_the_DURATION_verdict(self):
        """It is already on the record — `adjudicate_duration` puts
        `beam_levels` in the verdict's own value — so nothing re-reads the
        ink. Level 3 in, level 3 out."""
        xml, _ = E.to_musicxml(_beamed_page(n_notes=4, beam_levels=3))
        self.assertIn('<beam number="3">', xml)


class TestTheFrameConversion(unittest.TestCase):
    """⚠️⚠️ THE FRAME IS THE WHOLE RISK, and a wrong one does not raise — it
    writes a beam over the wrong notes. `Q.BEAM_STROKE` is filed in the CELL's
    CANONICAL frame while `annotate_beams` compares against `bbox_page`."""

    @staticmethod
    def _cell(page_boxes=True):
        doc = _beamed_page(n_notes=4, page_boxes=page_boxes)
        parts, *_ = E.build(E.Record(doc))
        return E.Record(doc), parts[0][0].cells[0]

    def test_the_stroke_is_converted_into_the_HEADS_frame(self):
        """⚠️⚠️ ASSERTED AS EXACT GEOMETRY, NOT AS "it covers the heads".
        The mutation battery caught the weaker form: with the SCALE dropped
        to 1.0 the stroke is twice as wide and still covers every head, so a
        containment test goes green on a conversion that is wrong by a factor
        of two. On a real page that over-wide box swallows the NEXT group —
        which is the `box containing two disjoint boxes` failure
        `annotate_beams` already documents paying for.
        """
        rec, cell = self._cell()
        boxes = E._beam_boxes_by_cell(rec)["cell/0/0/0/0"]
        dets = E._beam_detections_page(cell, boxes)
        self.assertEqual(len(dets), 1)
        x, y, w, h = dets[0]["bbox_page"]
        # canonical stroke is (100, 20, 340, 10); head 0 is canonical
        # (100, 50, 40, 40) and page (1050, 500, 20, 20), so scale = 0.5.
        self.assertAlmostEqual(x, 1050.0, places=6)
        self.assertAlmostEqual(y, 500.0 + (20.0 - 50.0) * _SCALE, places=6)
        self.assertAlmostEqual(w, 340.0 * _SCALE, places=6)
        self.assertAlmostEqual(h, 10.0 * _SCALE, places=6)
        # ⚠️ and it must be in the PAGE frame, not the canonical one — the
        # canonical stroke starts at 100, the page one at 1050.
        self.assertGreater(x, 900.0)

    def test_it_REFUSES_where_no_head_carries_both_frames(self):
        rec, cell = self._cell(page_boxes=False)
        boxes = E._beam_boxes_by_cell(rec)["cell/0/0/0/0"]
        self.assertEqual(E._beam_detections_page(cell, boxes), [])


class TestTheDocumentationClaim(unittest.TestCase):
    def test_the_two_documents_about_the_accidental_AGREE(self):
        """⚠️ THE TREE CONTRADICTED ITSELF FOR AS LONG AS BOTH EXISTED, and
        that is what this pins -- not either side's current answer.
        `NOT_NOTATION["accidental"]` said the glyph was "consumed into `pitch`
        and `accidental`" while `gather_coverage.FAMILY_Q_IS_ELSEWHERE` said
        it reached no quantity at all; the second was right and the first was
        repaired on 2026-09-21.

        ⚠️⚠️ ROADMAP 2.7 MOVED BOTH, ON 2026-09-23, AND THIS TEST MOVED WITH
        THEM. The glyph now IS read -- `Q.ACCIDENTAL_STAFF_POSITION` gathers
        it and `accidental_owner` decides it -- so the assertion is no longer
        "neither claims it is consumed" but "both name the SAME quantity".
        The pairing is the point: a future change that repairs one document
        and forgets the other fails here whichever direction it moves.
        """
        from tools.omr.staged import gather_coverage as GC
        entry = E.NOT_NOTATION["accidental"]
        self.assertNotIn("consumed into", entry)
        self.assertIn("ACCIDENTAL_STAFF_POSITION", entry)
        self.assertEqual(GC.FAMILY_TO_Q["accidental"],
                         "ACCIDENTAL_STAFF_POSITION")
        self.assertNotIn("accidental", GC.FAMILY_Q_IS_ELSEWHERE)

    def test_respell_accidental_is_still_a_producer_and_is_no_longer_alone(self):
        """⚠️⚠️ THAT DAY CAME: ROADMAP 2.7, 2026-09-23. This test used to be
        named `..._is_still_the_ONLY_producer` and its docstring said *"the
        day a reader of the PRINTED glyph files one, that is no longer true
        and this test is where the next author finds out"*. It did, and this
        is the finding out.

        ⚠️ WHAT THE ROUTING NOW RESTS ON IS NARROWER AND IS ASSERTED HERE.
        `Q.ACCIDENTAL` still means ONLY *what this note sounds*, whichever
        rule wrote it, so folding it into the pitch stays correct. What says
        whether a GLYPH was drawn is `detail.printed` on the row, not the
        decider's name -- and `apply_printed_accidental` sets it on the owned
        head only, never on the notes it carries to."""
        from tools.omr.staged import consequences  # noqa: F401  registers
        from tools.omr.staged import evaluate
        from tools.omr.staged.record import Q
        writers = sorted(r.consequence.value for r in evaluate.RULES
                         if r.effect == Q.ACCIDENTAL)
        self.assertEqual(writers,
                         ["apply_printed_accidental", "respell_accidental"])


if __name__ == "__main__":
    unittest.main()
