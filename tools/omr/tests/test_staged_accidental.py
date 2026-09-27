"""ROADMAP 2.7 — the PRINTED in-bar accidental, GATHER to `<accidental>`.

⚠️⚠️ EVERY TEST HERE WAS RUN RED FIRST, against the tree at `848dda47`, where
`Q.ACCIDENTAL_STAFF_POSITION` and `Q.ACCIDENTAL_OWNER` did not exist and the
exporter passed no `accidental=` at all. The whole file failed at import on
`Q.ACCIDENTAL_STAFF_POSITION`, which is the RED a new quantity gives.

⚠️ THE TWO FACTS ARE ASSERTED APART, ALWAYS. `<alter>` says what the note
SOUNDS and `<accidental>` says what the engraver DREW; `e8cf5b26` had to
remove a path that emitted the second for the first, 334 printed flats against
0 sounding alterations on Litolff pp.1-4. A test that only checked
`<accidental>` appeared would pass on an exporter that had re-joined them.

⚠️ EVERY REFUSAL CARRIES ITS POSITIVE CONTROL IN THE SAME CLASS. A refusal
test with no positive control passes the moment the decision starts abstaining
on everything -- so each `ambiguous_height` / `no_candidate` case differs from
a DECIDING one in exactly one fact, and the deciding version is asserted too.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate, evaluate, export as E
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import consequences  # noqa: F401  registers the rules
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS

CELL = R.cell(0, 0, 0, 0)
STAFF = R.staff(0, 0, 0)

#: The cell's own unit. ⚠️ NOT 1.0: the x window is expressed in staff SPACES
#: and the y window in staff POSITIONS (half-spaces), so a fixture at unit 1
#: cannot tell a spaces bug from a positions bug. At 20.0 a space is 20 px, a
#: position is 10 px, and the two windows land at visibly different distances.
SPACE = 20.0
HALF = SPACE / 2.0

#: A notehead is ~1.3 staff spaces wide (CLAUDE.md §10).
HEAD_W = 26.0


def _cell_unit(log):
    log.observe(CELL, Q.CELL_STAFF_SPACE, SPACE, reader=READERS.GEOMETRY,
                frame="cell:0", half_step=HALF, lines=5)


def _head(log, gi, x, position, *, w=HEAD_W, h=SPACE):
    """A notehead whose box AND whose clef-free position are both filed.

    ⚠️ BOTH, because the adjudicator reads the box for x and the position row
    for height, and a fixture supplying only one would exercise half the rule
    while looking complete.
    """
    g = R.glyph(0, 0, 0, 0, gi)
    y = position * HALF - h / 2.0
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlackOnLine", x, y, w, h),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                category="notehead")
    log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine",
                reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    log.observe(g, Q.NOTEHEAD_STAFF_POSITION, float(position),
                reader=READERS.GEOMETRY, frame="cell:0",
                residual=0.0, rounded=int(round(position)))
    return g


def _acc(log, gi, x, position, *, cls="accidentalSharp", alteration="#",
         w=12.0):
    """A printed accidental at `position`, its right edge at `x`."""
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.GLYPH_BOX, (cls, x - w, position * HALF - SPACE, w,
                                 SPACE * 2), reader=READERS.DETECTOR,
                frame="cell:0", score=0.8, category="accidental")
    log.observe(g, Q.ACCIDENTAL_STAFF_POSITION, float(position),
                reader=READERS.GEOMETRY, frame="cell:0",
                alteration=alteration, detector_class=cls,
                anchor_fraction=0.5, box_centre_position=float(position),
                residual=0.0, rounded=int(round(position)),
                x0=x - w, x1=x, y0=position * HALF - SPACE,
                y1=position * HALF + SPACE, confidence=0.8)
    return g


def _decide(log):
    """⚠️ ONLY THIS DECISION RUNS. The full `ORDER` also adjudicates the clef
    and the key from evidence this fixture does not supply, and the
    abstentions it files then collide with the verdicts `_full` hands in --
    `Log.record` refuses a second adjudication that declares no `revises=`,
    correctly. Naming the order keeps the fixture about one decision."""
    log.freeze()
    adjudicate.run(log, order=(Q.ACCIDENTAL_OWNER,))
    return log


def _full(log, *, fifths=0, clef="treble", meter=None):
    """GATHER -> ADJUDICATE -> EVALUATE, then the exporter's own input dict.

    ⚠️ THE CLEF AND THE KEY ARE VERDICTS, NOT PITCHES HANDED IN. The pitch is
    produced by `restate_pitch` from the position rows this fixture files, so
    the test exercises the real chain rather than a hand-written answer --
    and `respell_accidental` runs on the same record, which is what makes the
    supersession assertions mean anything.
    """
    log.record(R.Verdict(
        id=log._next_id("vrd"), subject=STAFF, quantity=Q.CLEF,
        outcome=R.Outcome.DECIDED, value=clef, decider="t", reason="fixture"))
    log.record(R.Verdict(
        id=log._next_id("vrd"), subject=STAFF, quantity=Q.KEY_SIGNATURE,
        outcome=R.Outcome.DECIDED, value=fifths, decider="t",
        reason="fixture"))
    log.record(R.Verdict(
        id=log._next_id("vrd"), subject=STAFF, quantity=Q.MEASURE_PARTITION,
        outcome=R.Outcome.DECIDED, value=1, decider="t", reason="fixture"))
    log.record(R.Verdict(
        id=log._next_id("vrd"), subject=R.system(0, 0),
        quantity=Q.SYSTEM_STAFF_COUNT, outcome=R.Outcome.DECIDED, value=1,
        decider="t", reason="fixture"))
    log.record(R.Verdict(
        id=log._next_id("vrd"), subject=R.DOCUMENT,
        quantity=Q.PART_PARTITION, outcome=R.Outcome.DECIDED,
        value={"join": "ordinal", "staves_per_system": 1}, decider="t",
        reason="ordinal"))
    if meter is not None:
        log.record(R.Verdict(
            id=log._next_id("vrd"), subject=R.system(0, 0), quantity=Q.METER,
            outcome=R.Outcome.DECIDED, value=meter, decider="t",
            reason="fixture"))
    evaluate.run(log)
    return {"record": log.to_json(), "summary": log.summary()}


QUARTER = {"beats": 1.0, "written": 1.0, "dots": 0}


def _durations(log, *gis):
    for gi in gis:
        log.record(R.Verdict(
            id=log._next_id("vrd"), subject=R.glyph(0, 0, 0, 0, gi),
            quantity=Q.DURATION, outcome=R.Outcome.DECIDED, value=dict(QUARTER),
            decider="t", reason="fixture"))


# ─────────────────────────────────────────────────────────────────────────────
# GATHER
# ─────────────────────────────────────────────────────────────────────────────


class _Det:
    def __init__(self, name, x, y, w, h, conf=0.8):
        self.smufl_name = name
        self.x_canonical, self.y_canonical = x, y
        self.width_canonical, self.height_canonical = w, h
        self.confidence = conf

    @property
    def x_center(self):
        return self.x_canonical + self.width_canonical / 2.0

    @property
    def y_center(self):
        return self.y_canonical + self.height_canonical / 2.0


class _Cell:
    staff_index = 0
    page_index = 0
    measure_index = 0
    staff_line_ys_canonical = [0.0, SPACE, 2 * SPACE, 3 * SPACE, 4 * SPACE]
    staff_line_spacing_canonical = SPACE


class TestGatherFilesTheGlyphsPosition(unittest.TestCase):

    def _run(self, dets):
        log = Log()
        G.gather_accidental_positions(
            log, [_Cell()], {0: (0, 0)}, {CELL.to_key(): dets})
        return log.rows(Q.ACCIDENTAL_STAFF_POSITION, CELL,
                        scope=R.Scope.SELF_AND_DESCENDANTS)

    def test_a_sharp_is_gathered_with_its_alteration(self):
        rows = self._run([_Det("accidentalSharp", 100.0, 0.0, 12.0, 40.0)])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].detail["alteration"], "#")

    def test_every_alteration_the_detector_spells_is_read(self):
        """⚠️ THE DOUBLES ARE THE ONES THAT BREAK ON ORDERING.
        `doublesharp` CONTAINS `sharp`, so a prefix test in the wrong order
        reads all 85 double sharps of the Litolff movement as single ones --
        a quarter tone, silently."""
        dets = [_Det(n, 100.0 + 50 * i, 0.0, 12.0, 40.0) for i, n in enumerate(
            ("accidentalSharp", "accidentalFlat", "accidentalNatural",
             "accidentalDoubleSharp", "accidentalDoubleFlat"))]
        got = [r.detail["alteration"] for r in self._run(dets)]
        self.assertEqual(got, ["#", "b", "natural", "##", "bb"])

    def test_the_key_signatures_own_glyphs_are_NOT_gathered_here(self):
        """⚠️⚠️ THE CUT THAT MAKES 2,058 INTO 1,531. `keySharp`.lower()
        contains `sharp`, so the legacy pair rule offers the signature's own
        glyphs a notehead and hands every staff's first note the last sharp
        of its key. `Q.KEY_SIGNATURE` owns those."""
        rows = self._run([_Det("keySharp", 100.0, 0.0, 12.0, 40.0),
                          _Det("keyFlat", 140.0, 0.0, 12.0, 40.0),
                          _Det("keyNatural", 180.0, 0.0, 12.0, 40.0),
                          _Det("accidentalSharp", 220.0, 0.0, 12.0, 40.0)])
        self.assertEqual([r.detail["detector_class"] for r in rows],
                         ["accidentalSharp"])

    def test_a_notehead_is_not_an_accidental(self):
        self.assertEqual(self._run(
            [_Det("noteheadBlackOnLine", 100.0, 0.0, 26.0, 20.0)]), ())

    def test_a_SHARP_is_read_at_its_box_centre(self):
        """A sharp is symmetric about the pitch it names -- Bravura puts its
        anchor at 0.501 of the box height -- so its position IS the centre."""
        row = self._run([_Det("accidentalSharp", 100.0, 0.0, 12.0, 40.0)])[0]
        self.assertAlmostEqual(row.value, (40.0 * 0.501) / HALF, places=3)
        # within a hundredth of a position of the box centre, which is what
        # "symmetric" means for a glyph the font puts at 0.501 rather than 0.5
        self.assertAlmostEqual(row.value, row.detail["box_centre_position"],
                               places=1)

    def test_a_FLAT_is_read_BELOW_its_box_centre(self):
        """⚠️⚠️ THE ASYMMETRY, AND IT IS AN ENGRAVING FACT. A flat carries an
        ascender above its bowl, so its box extends UPWARD from the pitch it
        names and its centre is NOT that pitch. Bravura says the anchor sits
        at 0.715 of the box height; measured on Breitkopf with an estimator
        that cannot select on the answer, 0.692. Larger canonical y is LOWER
        on the page, so the anchored position is the LARGER number.

        ⚠️ THE CONTROL IS THE SHARP ABOVE: same box, same grid, and it must
        NOT move -- otherwise this passes on a reader that shifts everything.
        """
        row = self._run([_Det("accidentalFlat", 100.0, 0.0, 12.0, 40.0)])[0]
        self.assertGreater(row.value, row.detail["box_centre_position"])
        self.assertAlmostEqual(row.value, (40.0 * 0.715) / HALF, places=3)

    def test_the_uncorrected_reading_survives_beside_it(self):
        """A consumer that disagrees with the anchor must not need a
        re-gather -- this project's own most-repeated bug is the value that
        existed and nothing carried it."""
        row = self._run([_Det("accidentalFlat", 100.0, 0.0, 12.0, 40.0)])[0]
        self.assertAlmostEqual(row.detail["box_centre_position"],
                               20.0 / HALF, places=3)
        self.assertEqual(row.detail["anchor_fraction"], 0.715)

    def test_a_cell_with_no_grid_files_nothing_and_does_not_raise(self):
        class _Flat(_Cell):
            staff_line_ys_canonical = []
            staff_line_spacing_canonical = None
        log = Log()
        G.gather_accidental_positions(
            log, [_Flat()], {0: (0, 0)},
            {CELL.to_key(): [_Det("accidentalSharp", 100.0, 0.0, 12.0, 40.0)]})
        self.assertEqual(log.rows(Q.ACCIDENTAL_STAFF_POSITION, CELL,
                                  scope=R.Scope.SELF_AND_DESCENDANTS), ())


# ─────────────────────────────────────────────────────────────────────────────
# ADJUDICATE
# ─────────────────────────────────────────────────────────────────────────────


class TestTheOwnerIsTheHeadToTheRightAtTheSameHeight(unittest.TestCase):

    def test_it_is_registered_and_not_a_stub(self):
        self.assertFalse(adjudicate.REGISTRY[Q.ACCIDENTAL_OWNER].stub)

    def test_a_sharp_takes_the_head_immediately_right_of_it(self):
        log = Log()
        _cell_unit(log)
        acc = _acc(log, 0, 100.0, 4.0)
        head = _head(log, 1, 106.0, 4.0)
        v = _decide(log).verdict(Q.ACCIDENTAL_OWNER, acc)
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, head.to_key())
        self.assertEqual(v.reason, "immediately_right_same_position")
        self.assertEqual(v.detail["alteration"], "#")

    def test_a_head_to_the_LEFT_is_not_a_candidate(self):
        """⚠️ THE SIDE CONSTRAINT, AND IT NEEDS ITS OWN CASE. An accidental is
        printed BEFORE its note; a reader taking the nearest head in any
        direction gives the previous note the next note's alteration."""
        log = Log()
        _cell_unit(log)
        acc = _acc(log, 0, 100.0, 4.0)
        _head(log, 1, 40.0, 4.0)            # entirely left of the glyph
        v = _decide(log).verdict(Q.ACCIDENTAL_OWNER, acc)
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "no_candidate")

    def test_the_left_head_case_decides_when_the_head_moves_right(self):
        """The positive control for the refusal above: ONE fact differs."""
        log = Log()
        _cell_unit(log)
        acc = _acc(log, 0, 100.0, 4.0)
        head = _head(log, 1, 106.0, 4.0)
        v = _decide(log).verdict(Q.ACCIDENTAL_OWNER, acc)
        self.assertEqual(v.value, head.to_key())

    def test_a_head_at_the_WRONG_HEIGHT_is_not_a_candidate(self):
        """⚠️ THE HEIGHT CONSTRAINT. L32: *"the height constraint alone rules
        out most mis-attachments in a dense chord"* -- where every head is to
        the right and only one is at the glyph's own position."""
        log = Log()
        _cell_unit(log)
        acc = _acc(log, 0, 100.0, 4.0)
        _head(log, 1, 106.0, 8.0)          # four positions below: two steps
        v = _decide(log).verdict(Q.ACCIDENTAL_OWNER, acc)
        self.assertEqual(v.reason, "no_candidate")

    def test_the_right_height_in_the_same_chord_wins(self):
        """The positive control in the same class: a chord where the glyph
        must pick ONE of three heads, all of them to its right."""
        log = Log()
        _cell_unit(log)
        acc = _acc(log, 0, 100.0, 4.0)
        _head(log, 1, 106.0, 0.0)
        want = _head(log, 2, 106.0, 4.0)
        _head(log, 3, 106.0, 8.0)
        v = _decide(log).verdict(Q.ACCIDENTAL_OWNER, acc)
        self.assertEqual(v.value, want.to_key())

    def test_a_head_TOO_FAR_RIGHT_is_not_a_candidate(self):
        """⚠️ THE BOUND THE LEGACY RULE DOES NOT HAVE. `_pair_accidentals_to_
        noteheads` scores `x_dist + 3*y_dist` over every head in the cell and
        always answers, so a glyph whose own head the detector missed claims a
        note four beats away."""
        log = Log()
        _cell_unit(log)
        acc = _acc(log, 0, 100.0, 4.0)
        _head(log, 1, 100.0 + 3.0 * SPACE, 4.0)
        v = _decide(log).verdict(Q.ACCIDENTAL_OWNER, acc)
        self.assertEqual(v.reason, "no_candidate")

    def test_a_head_just_INSIDE_the_x_window_decides(self):
        """The positive control for the bound: 1.5 spaces against 3.0."""
        log = Log()
        _cell_unit(log)
        acc = _acc(log, 0, 100.0, 4.0)
        head = _head(log, 1, 100.0 + 1.5 * SPACE, 4.0)
        v = _decide(log).verdict(Q.ACCIDENTAL_OWNER, acc)
        self.assertEqual(v.value, head.to_key())

    def test_two_heads_at_equal_distance_ABSTAIN(self):
        """⚠️⚠️ THE REFUSAL THIS DECISION EXISTS FOR. A glyph standing exactly
        between two heads a diatonic step apart is 0.5 positions from each,
        and the geometry does not separate them. The legacy score would pick
        one on a tie-break and record a coin flip as a reading."""
        log = Log()
        _cell_unit(log)
        acc = _acc(log, 0, 100.0, 4.5)
        _head(log, 1, 106.0, 4.0)
        _head(log, 2, 130.0, 5.0)     # 1.5 spaces right: inside the x window
        v = _decide(log).verdict(Q.ACCIDENTAL_OWNER, acc)
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "ambiguous_height")
        self.assertEqual(len(v.detail["candidates"]), 2)

    def test_the_SAME_TWO_HEADS_decide_when_the_glyph_sits_on_one(self):
        """⚠️ THE POSITIVE CONTROL IN THE SAME CLASS, and without it the
        abstention above passes on a decision that abstains on everything.
        One fact differs: the glyph's own position."""
        log = Log()
        _cell_unit(log)
        acc = _acc(log, 0, 100.0, 4.0)
        on = _head(log, 1, 106.0, 4.0)
        _head(log, 2, 130.0, 5.0)
        v = _decide(log).verdict(Q.ACCIDENTAL_OWNER, acc)
        self.assertEqual(v.outcome, "decided")
        self.assertEqual(v.value, on.to_key())

    def test_a_unison_in_ONE_column_is_not_an_ambiguity(self):
        """⚠️ TWO DETECTIONS OF ONE NOTE, OR TWO VOICES ON ONE PITCH. The
        accidental governs the pitch either way, so abstaining here would be
        a refusal manufactured by the detector rather than by the page."""
        log = Log()
        _cell_unit(log)
        acc = _acc(log, 0, 100.0, 4.0)
        _head(log, 1, 106.0, 4.0)
        _head(log, 2, 108.0, 4.0)          # same column, within a head width
        v = _decide(log).verdict(Q.ACCIDENTAL_OWNER, acc)
        self.assertEqual(v.outcome, "decided")

    def test_a_CHORD_a_step_apart_in_one_column_still_ABSTAINS(self):
        """⚠️⚠️ THE CASE THE UNISON EXEMPTION MUST NOT SWALLOW, and the first
        draft of that clause did. Two heads at ONE x a DIATONIC STEP apart are
        two different notes; a glyph standing between them belongs to one of
        them and the geometry does not say which. Exempting them because they
        share a column would put the alteration on whichever was detected
        first -- an argmax over detection order."""
        log = Log()
        _cell_unit(log)
        acc = _acc(log, 0, 100.0, 4.5)
        _head(log, 1, 106.0, 4.0)
        _head(log, 2, 108.0, 5.0)          # same column, one step apart
        v = _decide(log).verdict(Q.ACCIDENTAL_OWNER, acc)
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "ambiguous_height")

    def test_with_NO_HEADS_AT_ALL_it_says_so_in_its_own_word(self):
        log = Log()
        _cell_unit(log)
        acc = _acc(log, 0, 100.0, 4.0)
        v = _decide(log).verdict(Q.ACCIDENTAL_OWNER, acc)
        self.assertEqual(v.reason, "no_candidate")

    def test_with_NO_UNIT_it_refuses_rather_than_assuming_one(self):
        """⚠️ THE WINDOW IS IN STAFF SPACES SO IT SURVIVES A RESCALED CELL.
        Substituting a constant would make the bound a different distance on
        every staff -- the frame fault `Q.ONSET_COLUMN` paid for."""
        log = Log()
        acc = _acc(log, 0, 100.0, 4.0)
        _head(log, 1, 106.0, 4.0)
        v = _decide(log).verdict(Q.ACCIDENTAL_OWNER, acc)
        self.assertEqual(v.reason, "no_unit")

    def test_the_bounds_are_NAMED_CONSTANTS_and_not_the_legacy_numbers(self):
        """⚠️ The legacy `0.6 * the accidental's own height` is a threshold
        taken from the mark's own box -- the augmentation-dot mistake. This
        pins that the staged rule does not import it."""
        from tools.omr.staged.adjudicators import ownership
        self.assertEqual(ownership._ACC_MAX_DX_SPACES, 1.75)
        self.assertEqual(ownership._ACC_MAX_DY_POSITIONS, 1.4)
        self.assertEqual(ownership._ACC_AMBIGUOUS_MARGIN_POSITIONS, 0.5)


# ─────────────────────────────────────────────────────────────────────────────
# EVALUATE + EXPORT
# ─────────────────────────────────────────────────────────────────────────────


class TestItReachesTheFile(unittest.TestCase):

    def test_a_sharp_writes_BOTH_the_glyph_and_the_sound(self):
        """⚠️ TWO ASSERTIONS, NEVER ONE. `<accidental>sharp</accidental>` is
        what the engraver drew and `<alter>1</alter>` is what it sounds; an
        exporter writing only one of them is wrong in a way the other
        assertion cannot see."""
        log = Log()
        _cell_unit(log)
        _acc(log, 0, 100.0, 7.0)           # position 7 = F4 in treble
        _head(log, 1, 106.0, 7.0)
        _durations(log, 1)
        xml, report = E.to_musicxml(_full(_decide(log)))
        self.assertIn("<step>F</step>", xml)
        self.assertIn("<alter>1</alter>", xml)
        self.assertIn("<accidental>sharp</accidental>", xml)
        self.assertEqual(report["written"]["accidentals_printed"], 1)

    def test_the_alteration_CARRIES_to_the_end_of_the_bar(self):
        """⚠️⚠️ C21, AND IT IS THE HALF A PER-GLYPH READER GETS WRONG. The
        second F has NO glyph of its own and still sounds F sharp -- the
        ABSENCE of a mark is a positive statement about pitch. It must carry
        the `<alter>` and must NOT carry an `<accidental>`, because the
        engraver drew nothing on it."""
        log = Log()
        _cell_unit(log)
        _acc(log, 0, 100.0, 7.0)
        _head(log, 1, 106.0, 7.0)
        _head(log, 2, 300.0, 7.0)          # same F, later in the bar, no glyph
        _durations(log, 1, 2)
        xml, report = E.to_musicxml(_full(_decide(log)))
        self.assertEqual(xml.count("<alter>1</alter>"), 2)
        self.assertEqual(xml.count("<accidental>sharp</accidental>"), 1)
        self.assertEqual(report["written"]["accidentals_printed"], 1)

    def test_a_DIFFERENT_letter_in_the_same_bar_is_untouched(self):
        """The positive control for the carry: C21 is keyed on (letter,
        octave), so a G in the same bar must sound G natural."""
        log = Log()
        _cell_unit(log)
        _acc(log, 0, 100.0, 7.0)
        _head(log, 1, 106.0, 7.0)          # F4
        _head(log, 2, 300.0, 6.0)          # G4
        _durations(log, 1, 2)
        xml, _r = E.to_musicxml(_full(_decide(log)))
        self.assertEqual(xml.count("<alter>1</alter>"), 1)
        self.assertIn("<step>G</step>", xml)

    def test_a_note_BEFORE_the_glyph_is_untouched(self):
        """An accidental governs FORWARD. A reader applying it to the whole
        bar re-pitches a note the engraver wrote plain."""
        log = Log()
        _cell_unit(log)
        _head(log, 0, 40.0, 7.0)           # F4, before the glyph
        _acc(log, 1, 100.0, 7.0)
        _head(log, 2, 106.0, 7.0)
        _durations(log, 0, 2)
        xml, _r = E.to_musicxml(_full(_decide(log)))
        self.assertEqual(xml.count("<alter>1</alter>"), 1)

    def test_a_NATURAL_after_a_sharp_cancels_it_for_the_rest_of_the_bar(self):
        """⚠️⚠️ THE CONVENTION THIS ITEM ADDS: a natural's cancellation is
        bar-scoped like any other accidental. The third F carries no glyph and
        must sound F natural, not fall back to the sharp -- and the natural's
        own note carries `<alter>0</alter>`, i.e. no `<alter>` at all, WITH a
        drawn `<accidental>natural</accidental>`. The two facts are
        independent and that is the whole reason the element exists."""
        log = Log()
        _cell_unit(log)
        _acc(log, 0, 100.0, 7.0)
        _head(log, 1, 106.0, 7.0)          # F sharp
        _acc(log, 2, 200.0, 7.0, cls="accidentalNatural", alteration="natural")
        _head(log, 3, 206.0, 7.0)          # F natural
        _head(log, 4, 300.0, 7.0)          # no glyph: still natural
        _durations(log, 1, 3, 4)
        xml, report = E.to_musicxml(_full(_decide(log)))
        self.assertEqual(xml.count("<alter>1</alter>"), 1)
        self.assertIn("<accidental>natural</accidental>", xml)
        self.assertEqual(report["written"]["accidentals_printed"], 2)
        # ⚠️ Three F4s, one altered: the other two are alter 0, which is the
        # BARE letter. A carry that survived the natural would show two.
        self.assertEqual(xml.count("<step>F</step>"), 3)

    def test_the_printed_glyph_OVERRIDES_the_key_and_says_so_on_the_record(self):
        """⚠️⚠️ THE SUPERSESSION. `respell_accidental` runs FIRST -- rules are
        ordered by the DOWNHILL index of their CAUSE and `key_signature` sits
        above `accidental_owner` -- so the key-derived row is always already
        on the record. Deferring would be a silent no-op; this asserts the
        page wins AND that the record shows both answers."""
        log = Log()
        _cell_unit(log)
        _acc(log, 0, 100.0, 7.0, cls="accidentalNatural", alteration="natural")
        head = _head(log, 1, 106.0, 7.0)   # F4, in a key with F sharp
        _durations(log, 1)
        doc = _full(_decide(log), fifths=1)
        xml, _r = E.to_musicxml(doc)
        self.assertNotIn("<alter>", xml)
        self.assertIn("<accidental>natural</accidental>", xml)
        rows = [v for v in doc["record"]["verdicts"]
                if v["quantity"] == "accidental"
                and v["subject"] == head.to_key()]
        self.assertEqual(sorted(v["decider"] for v in rows),
                         ["apply_printed_accidental", "respell_accidental"])
        winner = next(v for v in rows
                      if v["decider"] == "apply_printed_accidental")
        self.assertIsNotNone(winner["supersedes"])
        self.assertEqual(winner["detail"]["from"], "#")

    def test_the_KEY_still_writes_no_glyph(self):
        """The positive control for `e8cf5b26`: a note the key altered and the
        page did not mark carries `<alter>` and NO `<accidental>`."""
        log = Log()
        _cell_unit(log)
        _head(log, 0, 106.0, 7.0)
        _durations(log, 0)
        xml, report = E.to_musicxml(_full(_decide(log), fifths=1))
        self.assertIn("<alter>1</alter>", xml)
        self.assertNotIn("<accidental>", xml)
        self.assertEqual(report["written"].get("accidentals_printed", 0), 0)

    def test_an_AMBIGUOUS_glyph_writes_no_accidental_at_all(self):
        """⚠️ AN ABSTENTION MUST NOT BECOME AN ANSWER. Neither head may carry
        a drawn glyph, and neither may be re-pitched."""
        log = Log()
        _cell_unit(log)
        _acc(log, 0, 100.0, 4.5)
        _head(log, 1, 106.0, 4.0)
        _head(log, 2, 130.0, 5.0)
        _durations(log, 1, 2)
        xml, report = E.to_musicxml(_full(_decide(log)))
        self.assertNotIn("<accidental>", xml)
        self.assertNotIn("<alter>", xml)
        self.assertEqual(report["accidental_reading"]["abstained_ambiguous"], 1)
        self.assertEqual(report["accidental_reading"]["applied"], 0)

    def test_a_double_sharp_reaches_alter_2(self):
        log = Log()
        _cell_unit(log)
        _acc(log, 0, 100.0, 7.0, cls="accidentalDoubleSharp", alteration="##")
        _head(log, 1, 106.0, 7.0)
        _durations(log, 1)
        xml, _r = E.to_musicxml(_full(_decide(log)))
        self.assertIn("<alter>2</alter>", xml)
        self.assertIn("<accidental>double-sharp</accidental>", xml)


class TestTheCensusIsAPartition(unittest.TestCase):
    """⚠️ `unaccounted` EMPTY IS THE CONTROL. A headline coverage number
    cannot be unpicked afterwards; a partition with a remainder bucket makes a
    branch nobody declared visible the first time it fires."""

    def _census(self, log):
        _r, report = E.to_musicxml(_full(_decide(log)))
        return report["accidental_reading"]

    def test_an_applied_glyph_lands_in_applied_and_nowhere_else(self):
        log = Log()
        _cell_unit(log)
        _acc(log, 0, 100.0, 7.0)
        _head(log, 1, 106.0, 7.0)
        _durations(log, 1)
        c = self._census(log)
        self.assertEqual(c["gathered"], 1)
        self.assertEqual(c["applied"], 1)
        self.assertEqual(c["owner_decided"], 1)
        self.assertEqual(c["unaccounted"], 0)
        self.assertEqual(c["unowned"], 0)

    def test_a_no_candidate_glyph_lands_in_no_candidate(self):
        log = Log()
        _cell_unit(log)
        _acc(log, 0, 100.0, 7.0)
        c = self._census(log)
        self.assertEqual(c["no_candidate"], 1)
        self.assertEqual(c["applied"], 0)
        self.assertEqual(c["unaccounted"], 0)

    def test_the_census_counts_the_carry_apart_from_the_glyph(self):
        log = Log()
        _cell_unit(log)
        _acc(log, 0, 100.0, 7.0)
        _head(log, 1, 106.0, 7.0)
        _head(log, 2, 300.0, 7.0)
        _durations(log, 1, 2)
        c = self._census(log)
        self.assertEqual(c["applied"], 1)
        self.assertEqual(c["carried_in_bar"], 1)

    def test_the_key_signatures_glyphs_are_counted_SEPARATELY(self):
        """⚠️ Folding them into the denominator would inflate it by a third
        (527 of 2,058 on the Litolff movement) with ink this family is right
        not to own."""
        log = Log()
        _cell_unit(log)
        g = R.glyph(0, 0, 0, 0, 9)
        log.observe(g, Q.GLYPH_BOX, ("keySharp", 10.0, 0.0, 12.0, 40.0),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.8,
                    category="accidental")
        _acc(log, 0, 100.0, 7.0)
        _head(log, 1, 106.0, 7.0)
        _durations(log, 1)
        c = self._census(log)
        self.assertEqual(c["printed_glyphs_detected"], 1)
        self.assertEqual(c["key_signature_glyphs_detected_and_owned_elsewhere"],
                         1)


class TestTheTreeNoLongerSaysNothingReadsIt(unittest.TestCase):

    def test_the_family_table_names_the_owner_quantity(self):
        self.assertEqual(E.FAMILIES["accidental"][0], Q.ACCIDENTAL_OWNER)

    def test_the_gather_coverage_gap_is_closed(self):
        from tools.omr.staged import gather_coverage as GC
        self.assertEqual(GC.FAMILY_TO_Q["accidental"],
                         "ACCIDENTAL_STAFF_POSITION")
        self.assertNotIn("accidental", GC.FAMILY_Q_IS_ELSEWHERE)

    def test_the_key_family_still_claims_the_signatures_glyphs(self):
        """⚠️ LONGEST PREFIX WINS, and this is the pair it has to resolve:
        `accidental` must not claim `keyFlat` and `key` must not claim
        `accidentalFlat`."""
        self.assertTrue(E._claims("accidental", "accidentalFlat"))
        self.assertFalse(E._claims("key", "accidentalFlat"))
        self.assertTrue(E._claims("key", "keyFlat"))
        self.assertFalse(E._claims("accidental", "keyFlat"))


if __name__ == "__main__":
    unittest.main()
