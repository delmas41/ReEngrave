"""ROADMAP 2.38 -- a second, independent witness for `beams_ambiguous`.

⚠️ WHY THIS FILE EXISTS. `benchmarks/omr-duration-narrowed-2026-09/
FINDINGS.md` §2 (ROADMAP 2.36's own triage): the single BIGGEST
`duration_narrowed` class -- `beams_ambiguous`, certain=0/possible=1,
"nothing certainly covers this note, but one stroke MIGHT" -- had NO
connection built for it, because it is a first-hand geometric judgement
(`rhythm._beam_levels`'s own padded column test over a stroke's BOX) and
nothing else on the record spoke to the same fact from a different angle.
This is that second witness: `Q.BEAM_STEM_JOIN` (`gather.beam_stem_join_ink`,
`gather._observe_beam_stem_join`), a pixel-continuity scan between a stem's
own tip and a candidate stroke's ink, off the staff-ERASED raster --
independent of the stroke's own bounding box the same way `Q.STEM_TIP_INK`
(2.18c) is independent of `Q.FLAG`'s own box.

⚠️ RUN RED FIRST: every test below fails to import before
`gather.beam_stem_join_ink` / `gather._observe_beam_stem_join` /
`Q.BEAM_STEM_JOIN` / `READERS.CV_BEAM_JOIN` / `rhythm._beam_join_witness`
exist, and the ADJUDICATE-level tests fail on the unmodified `_beam_levels`
(no `join_witness` parameter).
"""

from __future__ import annotations

import unittest

import numpy as np

from tools.omr.staged import adjudicate, evaluate                # noqa: F401
from tools.omr.staged import adjudicators, consequences          # noqa: F401
from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Outcome, Q, READERS

from tools.omr.staged.adjudicators import rhythm

SP = 20.0                        # one staff space, canonical px


def _paper(h=400, w=400):
    return np.full((h, w), 255, dtype=np.uint8)


def _draw(img, x0, y0, x1, y1):
    img[int(round(y0)):int(round(y1)), int(round(x0)):int(round(x1))] = 0


# ─────────────────────────────────────────────────────────────────────────────
# Part 1 -- the pure measurement, on synthetic rasters (0 = ink)
# ─────────────────────────────────────────────────────────────────────────────

class TestTheMeasurement(unittest.TestCase):
    """`gather.beam_stem_join_ink` -- a windowed ink-continuity scan, no
    identity, no ownership: does the stem's own ink reach the stroke's?"""

    def test_the_stem_ends_IN_the_beam_is_joined_with_no_gap(self):
        """The tip already sits inside the stroke's own y-range -- the
        physical "one connected mark" case. No ink need be drawn at all;
        there is no gap to walk."""
        img = _paper()
        m = gather.beam_stem_join_ink(img, 190.0, 194.0, 100.0, "top",
                                      90.0, 105.0, gap_tolerance_px=4.0)
        self.assertTrue(m["found"])
        self.assertEqual(m["gap_px"], 0.0)

    def test_a_stroke_ONE_SPACE_past_the_tip_with_no_ink_between_is_NOT_joined(self):
        img = _paper()
        # tip at y=100 (top end); the stroke sits a full space (20px) above,
        # at y=[76, 80] -- nothing drawn in the gap [80, 100).
        _draw(img, 190.0, 76.0, 194.0, 80.0)
        m = gather.beam_stem_join_ink(img, 190.0, 194.0, 100.0, "top",
                                      76.0, 80.0, gap_tolerance_px=4.0)
        self.assertFalse(m["found"])
        self.assertEqual(m["gap_px"], 20.0)
        self.assertEqual(m["max_blank_run_px"], 20)

    def test_a_SHATTERED_junction_with_a_1px_gap_is_still_joined(self):
        """The tolerance exists for exactly this: a shattering plate
        (CLAUDE.md §10) may leave a thin blank seam at a junction that is
        physically one mark."""
        img = _paper()
        # tip at y=100; ink resumes at y=99 up through the stroke edge at
        # y=80 -- EXCEPT one blank row at y=90 (the shattered seam).
        _draw(img, 190.0, 80.0, 194.0, 90.0)
        _draw(img, 190.0, 91.0, 194.0, 100.0)
        m = gather.beam_stem_join_ink(img, 190.0, 194.0, 100.0, "top",
                                      76.0, 80.0, gap_tolerance_px=4.0)
        self.assertTrue(m["found"])
        self.assertEqual(m["max_blank_run_px"], 1)

    def test_a_gap_wider_than_the_tolerance_is_NOT_joined(self):
        img = _paper()
        # a 5px blank seam where the tolerance is 4px.
        _draw(img, 190.0, 80.0, 194.0, 90.0)
        _draw(img, 190.0, 95.0, 194.0, 100.0)
        m = gather.beam_stem_join_ink(img, 190.0, 194.0, 100.0, "top",
                                      76.0, 80.0, gap_tolerance_px=4.0)
        self.assertFalse(m["found"])
        self.assertEqual(m["max_blank_run_px"], 5)

    def test_a_slur_arc_touching_the_stem_MID_LENGTH_is_DECLINED(self):
        """⚠️⚠️ THE FIX (manager review of 024bdc7c). A candidate whose own
        y-range sits well inside the stem's own body -- neither reaching the
        tip nor standing cleanly past it -- used to read `found=False`
        ("not joined"), and `_beam_levels` DROPS a `found=False` stroke
        entirely (neither certain nor possible). That is wrong: position
        alone cannot tell a slur crossing the stem apart from a SECONDARY
        beam attaching just inside the primary, or a `Q.STEM` box that
        overshoots its own beam (see the three tests below) -- all three
        put a stroke in exactly this spot. Rule 8: cannot tell is never an
        answer, so this DECLINES (`None`), not "not joined"."""
        img = _paper()
        # the WHOLE region between the tip (100) and the "stroke" (145..150,
        # deep inside the stem's own 100..200 extent) is solid ink -- the
        # stem's own body -- and the test must still decline, not read it.
        _draw(img, 190.0, 100.0, 194.0, 200.0)
        m = gather.beam_stem_join_ink(img, 190.0, 194.0, 100.0, "top",
                                      145.0, 150.0, gap_tolerance_px=4.0)
        self.assertIsNone(m)

    def test_a_SECONDARY_beam_one_beam_gap_inside_the_primary_is_DECLINED(self):
        """Manager review of 024bdc7c, case (1). A 16th note: the PRIMARY
        beam sits at the stem's own tip (not this test's concern), and the
        SECONDARY sits further into the stem's body, one small gap inside
        it -- exactly the shape a real Brahms 234 `certain=1, possible=2`
        note has. The secondary's own y-range does not reach the tip and
        does not stand past it (it is BEYOND the tip in the wrong
        direction, further into the body) -- DECLINED, not "not joined",
        so `_beam_levels` leaves it POSSIBLE rather than dropping it."""
        img = _paper()
        _draw(img, 190.0, 100.0, 194.0, 130.0)   # continuous stem ink
        # tip (top) at y=100; secondary stroke at y=[112, 116], one gap
        # inside the body -- neither reaches 100 nor stands past it.
        m = gather.beam_stem_join_ink(img, 190.0, 194.0, 100.0, "top",
                                      112.0, 116.0, gap_tolerance_px=4.0)
        self.assertIsNone(m)

    def test_a_stem_box_that_OVERSHOOTS_its_own_beam_is_DECLINED(self):
        """Manager review of 024bdc7c, case (2). The CV `Q.STEM` box ran on
        through the beam (a common shape on a thick print) and reports a
        tip PAST where the beam actually is -- so the real, PRIMARY beam
        now sits in the same "inside the reported tip" position case (1)
        does. Declined for the identical reason: the ink alone cannot
        tell an overshot stem from a secondary beam from a slur."""
        img = _paper()
        _draw(img, 190.0, 80.0, 194.0, 120.0)    # the (overshot) stem's ink
        # reported tip (top) at y=80 -- past the real beam, which sits at
        # y=[100, 104], well inside the reported stem's own extent.
        m = gather.beam_stem_join_ink(img, 190.0, 194.0, 80.0, "top",
                                      100.0, 104.0, gap_tolerance_px=4.0)
        self.assertIsNone(m)

    def test_the_BOTTOM_tip_is_symmetric(self):
        img = _paper()
        # tip at y=200 (bottom end); ink fills the whole gap down to the
        # stroke's own near edge at y=210.
        _draw(img, 190.0, 200.0, 194.0, 210.0)
        m = gather.beam_stem_join_ink(img, 190.0, 194.0, 200.0, "bottom",
                                      210.0, 214.0, gap_tolerance_px=4.0)
        self.assertTrue(m["found"])

    def test_window_off_the_raster_is_none(self):
        img = _paper(h=50, w=50)
        m = gather.beam_stem_join_ink(img, 190.0, 194.0, 100.0, "top",
                                      70.0, 76.0, gap_tolerance_px=4.0)
        self.assertIsNone(m)

    def test_no_raster_is_none(self):
        self.assertIsNone(
            gather.beam_stem_join_ink(None, 190.0, 194.0, 100.0, "top",
                                      70.0, 76.0, gap_tolerance_px=4.0))

    def test_stem_x_unknown_is_none(self):
        img = _paper()
        # x1 <= x0 -- no usable x-range.
        self.assertIsNone(
            gather.beam_stem_join_ink(img, 194.0, 194.0, 100.0, "top",
                                      70.0, 76.0, gap_tolerance_px=4.0))


# ─────────────────────────────────────────────────────────────────────────────
# Part 2 -- `_observe_beam_stem_join`: one row per (stem, stroke, end)
# ─────────────────────────────────────────────────────────────────────────────

class _Det:
    """A stem/beam detection, the fields `gather_cv_lines` reads off it."""

    def __init__(self, x, y, w, h):
        self.x_canonical, self.y_canonical = x, y
        self.width_canonical, self.height_canonical = w, h


class FakeCell:
    def __init__(self, *, image_no_staff, thickness=4.0):
        self.image_no_staff = image_no_staff
        self.staff_line_thickness_canonical = thickness


SUB = R.cell(0, 0, 0, 0)


def _joined_cell():
    """A stem 190-194 x 100-200; a stroke touching its top tip directly."""
    img = _paper()
    _draw(img, 190.0, 96.0, 194.0, 100.0)   # ink right up to the tip
    return FakeCell(image_no_staff=img)


class TestGatherIntegration(unittest.TestCase):

    def test_files_one_row_per_stem_stroke_end_triple(self):
        """The TOP end (the stroke's own side) reads as an Observation; the
        BOTTOM end -- where this stroke is nowhere near either the tip or
        cleanly past it, ROADMAP 2.38's post-review fix -- ABSTAINS rather
        than filing a false `found=False` row."""
        log = Log()
        stem = (_Det(190.0, 100.0, 4.0, 100.0), "obs:stem-1")
        beam = (_Det(190.0, 90.0, 4.0, 6.0), "obs:beam-1")   # y 90..96
        gather._observe_beam_stem_join(log, SUB, "cell:0", _joined_cell(),
                                       [stem], [beam], SP)
        log.freeze()
        rows = log.rows(Q.BEAM_STEM_JOIN, SUB)
        self.assertEqual(len(rows), 1)
        top = rows[0]
        self.assertEqual(top.detail["end"], "top")
        self.assertTrue(top.value)
        self.assertEqual(top.reader, READERS.CV_BEAM_JOIN)
        self.assertEqual(top.detail["stem_row_id"], "obs:stem-1")
        self.assertEqual(top.detail["beam_row_id"], "obs:beam-1")
        bottom = [a for a in log.refusals(Q.BEAM_STEM_JOIN, SUB)
                  if a.detail["end"] == "bottom"]
        self.assertEqual(len(bottom), 1)
        self.assertEqual(bottom[0].reason, ABSTAIN.AMBIGUOUS)

    def test_no_image_no_staff_abstains_no_mask(self):
        log = Log()
        stem = (_Det(190.0, 100.0, 4.0, 100.0), "obs:stem-1")
        beam = (_Det(190.0, 90.0, 4.0, 6.0), "obs:beam-1")
        gather._observe_beam_stem_join(
            log, SUB, "cell:0", FakeCell(image_no_staff=None),
            [stem], [beam], SP)
        log.freeze()
        abst = log.refusals(Q.BEAM_STEM_JOIN, SUB)
        self.assertEqual(len(abst), 2)
        self.assertTrue(all(a.reason == ABSTAIN.NO_MASK for a in abst))

    def test_no_staff_space_unit_abstains_no_staff_geometry(self):
        log = Log()
        stem = (_Det(190.0, 100.0, 4.0, 100.0), "obs:stem-1")
        beam = (_Det(190.0, 90.0, 4.0, 6.0), "obs:beam-1")
        gather._observe_beam_stem_join(log, SUB, "cell:0", _joined_cell(),
                                       [stem], [beam], None)
        log.freeze()
        abst = log.refusals(Q.BEAM_STEM_JOIN, SUB)
        self.assertEqual(len(abst), 2)
        self.assertTrue(
            all(a.reason == ABSTAIN.NO_STAFF_GEOMETRY for a in abst))

    def test_a_stem_with_no_x_range_abstains_no_staff_geometry(self):
        log = Log()
        stem = (_Det(190.0, 100.0, 0.0, 100.0), "obs:stem-1")  # width 0
        beam = (_Det(190.0, 90.0, 4.0, 6.0), "obs:beam-1")
        gather._observe_beam_stem_join(log, SUB, "cell:0", _joined_cell(),
                                       [stem], [beam], SP)
        log.freeze()
        abst = log.refusals(Q.BEAM_STEM_JOIN, SUB)
        self.assertEqual(len(abst), 2)
        self.assertTrue(
            all(a.reason == ABSTAIN.NO_STAFF_GEOMETRY for a in abst))

    def test_a_mid_length_crossing_abstains_AMBIGUOUS_not_a_false_observation(self):
        """⚠️⚠️ THE FIX, AT THE GATHER-INTEGRATION LEVEL (manager review of
        024bdc7c). A stroke sitting well inside the stem's own reported
        extent -- neither end's tip -- must ABSTAIN with a NAMED reason
        (`AMBIGUOUS`), never file a `found=False` Observation: a False
        observation is what `_beam_levels` reads as "drop this candidate
        entirely", which is the bug this fix closes."""
        log = Log()
        stem = (_Det(190.0, 100.0, 4.0, 100.0), "obs:stem-1")  # y 100..200
        beam = (_Det(190.0, 150.0, 4.0, 6.0), "obs:beam-1")    # y 150..156
        gather._observe_beam_stem_join(log, SUB, "cell:0", _joined_cell(),
                                       [stem], [beam], SP)
        log.freeze()
        self.assertEqual(len(log.rows(Q.BEAM_STEM_JOIN, SUB)), 0)
        abst = log.refusals(Q.BEAM_STEM_JOIN, SUB)
        self.assertEqual(len(abst), 2)              # top and bottom
        self.assertTrue(all(a.reason == ABSTAIN.AMBIGUOUS for a in abst))

    def test_falls_back_to_the_default_thickness_fraction(self):
        """No `staff_line_thickness_canonical` on the cell -- the tolerance
        falls back to a fraction of the staff space, same convention as
        `LEDGER_RUNG_INK_DEFAULT_THICKNESS_SPACES`."""
        log = Log()
        img = _paper()
        _draw(img, 190.0, 96.0, 194.0, 100.0)
        cell = FakeCell(image_no_staff=img, thickness=None)
        stem = (_Det(190.0, 100.0, 4.0, 100.0), "obs:stem-1")
        beam = (_Det(190.0, 90.0, 4.0, 6.0), "obs:beam-1")
        gather._observe_beam_stem_join(log, SUB, "cell:0", cell,
                                       [stem], [beam], SP)
        log.freeze()
        rows = {r.detail["end"]: r for r in log.rows(Q.BEAM_STEM_JOIN, SUB)}
        self.assertGreater(rows["top"].detail["gap_tolerance_px"], 0.0)


# ─────────────────────────────────────────────────────────────────────────────
# Part 3 -- `rhythm._beam_levels`: the witness only ever touches a stroke
# that was merely POSSIBLE, never one already CERTAIN
# ─────────────────────────────────────────────────────────────────────────────

class _Row:
    def __init__(self, id_, x0, x1):
        self.id = id_
        self.detail = {"x0": x0, "x1": x1}


#: x_center=150, width=20 -> pad=20. `PADDED` sits 10px short of the centre
#: (160 > 150), so `x0<=x_center<=x1` fails but `x0-pad<=x_center<=x1+pad`
#: (140<=150) holds -- possible, never certain, by box geometry alone.
def _padded_only_row():
    return _Row("b1", 160, 300)


class TestBeamLevelsWitness(unittest.TestCase):

    def test_no_witness_is_the_UNCHANGED_baseline(self):
        b = _padded_only_row()
        certain, possible = rhythm._beam_levels([b], 150, 20, ())
        self.assertEqual((certain, possible), (0, 1))

    def test_a_JOINED_witness_promotes_the_possible_stroke_to_certain(self):
        b = _padded_only_row()
        certain, possible = rhythm._beam_levels(
            [b], 150, 20, (), join_witness={"b1": True})
        self.assertEqual((certain, possible), (1, 1))

    def test_a_NOT_JOINED_witness_drops_the_stroke_entirely(self):
        b = _padded_only_row()
        certain, possible = rhythm._beam_levels(
            [b], 150, 20, (), join_witness={"b1": False})
        self.assertEqual((certain, possible), (0, 0))

    def test_a_DECLINED_witness_None_leaves_it_possible(self):
        b = _padded_only_row()
        certain, possible = rhythm._beam_levels(
            [b], 150, 20, (), join_witness={"b1": None})
        self.assertEqual((certain, possible), (0, 1))

    def test_POSITIVE_CONTROL_an_already_CERTAIN_stroke_is_UNAFFECTED(self):
        """⚠️ THE CONTROL. A stroke whose box already covers the centre, or
        that a stem already joins, must not move whatever the witness says
        -- box-geometry certainty is never overridden by this reader."""
        exact = _Row("b1", 100, 200)          # covers x_center=150 exactly
        certain, possible = rhythm._beam_levels(
            [exact], 150, 20, (), join_witness={"b1": False})
        self.assertEqual((certain, possible), (1, 1))

        stem_joined = _Row("b2", 400, 500)    # box FAR from the centre...
        certain, possible = rhythm._beam_levels(
            [stem_joined], 150, 20, (stem_joined,),   # ...but stem-joined
            join_witness={"b2": False})
        self.assertEqual((certain, possible), (1, 1))


# ─────────────────────────────────────────────────────────────────────────────
# Part 4 -- end to end through `adjudicate_duration`: the ADJUDICATE wiring
# ─────────────────────────────────────────────────────────────────────────────

CELL = R.cell(0, 0, 0, 0)


def _beam(log, *, y, x0, x1):
    return log.observe(CELL, Q.BEAM_STROKE, (x0, y, x1 - x0, 4),
                       reader=READERS.CV_LINES, frame="cell:0",
                       x0=x0, x1=x1, y_center=y,
                       image="no_staff", staff_lines_erased=True)


def _stem(log, *, x, y, h):
    return log.observe(CELL, Q.STEM, (x, y, 4, h),
                       reader=READERS.CV_LINES, frame="cell:0",
                       x0=x, x1=x + 4, y_center=y + h / 2.0,
                       image="no_staff", staff_lines_erased=True)


def _beam_stem_join(log, *, stem_row_id, beam_row_id, end, found):
    return log.observe(CELL, Q.BEAM_STEM_JOIN, bool(found),
                       reader=READERS.CV_BEAM_JOIN, frame="cell:0",
                       stem_row_id=stem_row_id, beam_row_id=beam_row_id,
                       end=end)


def _up_stemmed_note_with_a_padded_only_stroke(log):
    """A stem-up head whose STEM does NOT reach the candidate stroke (no
    box overlap -- `_stem_joined` calls it unjoined), but the stroke's
    x-range still falls within the padded column test -- exactly
    `certain=0, possible=1`, FINDINGS §1's biggest bucket, with a real gap
    for the ink witness to speak to.

    Head: x=135-155 (centre 145), y=90-106. Stem: x=135-139, y=70-100 (up-
    stemmed: mostly above the head, per `_legacy_stems._stem_direction`).
    Stroke: y=40-44, x=60-140 -- 5px short of the centre (padded, not
    certain) and 26px above the stem's own tip (y=70) with NO box overlap.
    """
    beam_row = _beam(log, y=40, x0=60, x1=140)
    g = R.glyph(0, 0, 0, 0, 0)
    log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, 16),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    stem_row = _stem(log, x=135, y=70, h=30)
    return g, beam_row, stem_row


class TestBeamStemJoinWiresIntoDuration(unittest.TestCase):
    """ROADMAP 2.38: possible+joined -> decided; possible+not joined ->
    the level is dropped; possible+declined -> stays narrowed; and the
    existing CERTAIN path (box overlap / stem join) is a positive control,
    untouched by a contradicting witness."""

    def test_the_UNWITNESSED_baseline_stays_NARROWED(self):
        """⚠️ THE CONTROL THIS WHOLE FILE EXISTS TO MOVE. Without any
        `Q.BEAM_STEM_JOIN` row the note narrows exactly as it did before
        this lane, `certain=0, possible=1`."""
        log = Log()
        g, _beam_row, _stem_row = \
            _up_stemmed_note_with_a_padded_only_stroke(log)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "beams_ambiguous")
        self.assertEqual(v.detail["levels_possible"], 1)
        self.assertEqual(v.detail["levels_certain"], 0)

    def test_JOINED_ink_DECIDES_the_note_at_one_beam_level(self):
        log = Log()
        g, beam_row, stem_row = \
            _up_stemmed_note_with_a_padded_only_stroke(log)
        _beam_stem_join(log, stem_row_id=stem_row.id, beam_row_id=beam_row.id,
                        end="top", found=True)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.5)
        self.assertEqual(v.detail["levels_certain"], 1)
        self.assertEqual(v.detail["beam_evidence"], "read")

    def test_NOT_JOINED_ink_DROPS_the_stroke_and_DECIDES_the_head_value(self):
        log = Log()
        g, beam_row, stem_row = \
            _up_stemmed_note_with_a_padded_only_stroke(log)
        _beam_stem_join(log, stem_row_id=stem_row.id, beam_row_id=beam_row.id,
                        end="top", found=False)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 1.0)    # the head value: quarter
        self.assertEqual(v.detail["levels_certain"], 0)
        self.assertEqual(v.detail["beam_evidence"], "none_over_this_note")

    def test_the_JOIN_ROW_IS_IN_THE_BASIS(self):
        log = Log()
        g, beam_row, stem_row = \
            _up_stemmed_note_with_a_padded_only_stroke(log)
        join_row = _beam_stem_join(log, stem_row_id=stem_row.id,
                                   beam_row_id=beam_row.id, end="top",
                                   found=True)
        adjudicate.run(log)
        self.assertIn(join_row.id, log.verdict(Q.DURATION, g).basis)

    def test_POSITIVE_CONTROL_a_box_CERTAIN_join_is_unmoved_by_the_ink(self):
        """⚠️ THE POSITIVE CONTROL. The identical stroke, but the stem now
        physically reaches it (box overlap) -- already CERTAIN before this
        lane existed -- and a CONTRADICTING ink witness (`found=False`) must
        not move it: box-geometry certainty is never overridden by the ink
        reader."""
        log = Log()
        beam_row = _beam(log, y=40, x0=60, x1=140)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, 16),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        stem_row = _stem(log, x=135, y=38, h=60)     # 38..98: meets y=40
        _beam_stem_join(log, stem_row_id=stem_row.id, beam_row_id=beam_row.id,
                        end="top", found=False)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.5)
        self.assertEqual(v.detail["levels_certain"], 1)

    def test_a_REAL_SECONDARY_beam_stays_POSSIBLE_not_DROPPED(self):
        """⚠️⚠️ THE BUG, END TO END (manager review of 024bdc7c). A 16th
        note: the PRIMARY beam is CERTAIN (its box covers the centre), the
        SECONDARY sits one gap further into the stem's body -- padded-only
        by the column test, exactly `certain=1, possible=2`, the shape a
        real Brahms 234 note has. No `Q.BEAM_STEM_JOIN` row exists for the
        secondary (GATHER would ABSTAIN `AMBIGUOUS` here, per the gather-
        level test above) -- so the fixed code must leave it POSSIBLE, not
        drop it to `possible=1` the way the pre-fix `found=False` read did.
        """
        log = Log()
        _beam(log, y=40, x0=100, x1=200)                 # covers centre=145
        _beam(log, y=52, x0=160, x1=260)                 # padded-only
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", 135, 90, 20, 16),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        _stem(log, x=135, y=40, h=60)                    # up-stem, tip=40
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "beams_ambiguous")
        self.assertEqual(v.detail["levels_certain"], 1)
        self.assertEqual(v.detail["levels_possible"], 2)
        levels = sorted(c.value["beam_levels"] for c in v.candidates)
        self.assertEqual(levels, [1, 2])


if __name__ == "__main__":
    unittest.main()
