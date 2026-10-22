"""ROADMAP 2.71 -- a TREMOLO SLASH is its own mark: a thick angled stroke
crossing BOTH sides of ONE stem, joined to no other note's stem. It is never
a beam, never a flag hook, never a rest, never a notehead, and never shortens
the written value.

Sean, 2026-10-09 (DECISIONS): *"The trem slash is very different from a beam.
Beams have to be connected to other notes - slashes never are. The hook of a
flag is very different from a slash. The slash crosses both sides of the stem
with a thick line at an angle."* / *"A hollow note with nothing on the stem is
always a half note."*

⚠️ RUN RED FIRST (the commit says so): `gather.stem_slashes`,
`gather.blank_slashes`, `gather._observe_stem_slashes`, `Q.STEM_SLASH` consumers
in `rhythm`, `family_precision` and `notehead_precision` do not exist on the
tree before this lane; every test here fails on the unrepaired tree (the
adjudication controls fail there on the missing vocabulary, so the
behavioural controls are the ones that matter).

⚠️ EVERY REFUSAL HAS A POSITIVE CONTROL IN THE SAME CLASS: a real slash that is
found; a real one-hook flag that still counts; a real two-note beam that
stays a beam; a plain half note that reads as before; an accent or a staccato
dot beside a stem that is not a slash; a real quarter rest that stays a rest.
"""

from __future__ import annotations

import unittest

import cv2
import numpy as np

from tools.omr.staged import adjudicate, evaluate                # noqa: F401
from tools.omr.staged import adjudicators, consequences          # noqa: F401
from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS

from tools.omr.tests.test_staged_duration import (
    CELL, _beam, _staff_space, _stem)

SP = 40.0                    # one staff space, canonical px
LINE = 4.0                   # a staff line's thickness, canonical px
SX0, SX1 = 300, 306          # a 6 px stem
STOP, SBOT = 100, 340        # a 6-space stem (up: head at the bottom)
STEM_BOX = (float(SX0), float(STOP), float(SX1 - SX0), float(SBOT - STOP))


def _paper(h=500, w=700):
    return np.full((h, w), 255, dtype=np.uint8)


def _stem_ink(img, x0=SX0, x1=SX1, y0=STOP, y1=SBOT):
    img[y0:y1, x0:x1] = 0


def _slash(img, y, *, cx=303, half_w=1.0, rise=0.45, thick=0.4):
    """A thick angled stroke across the stem at height `y`: `half_w` spaces
    either side, rising `rise` spaces over its half-width."""
    t = max(2, int(round(thick * SP)))
    cv2.line(img, (int(cx - half_w * SP), int(y + rise * SP)),
             (int(cx + half_w * SP), int(y - rise * SP)), 0, t)


def _read(img, *, stem=STEM_BOX, others=(), heads=()):
    ink = img == 0
    return gather.stem_slashes(ink, stem, SP, LINE, list(others), list(heads))


def _passing(strokes):
    return [s for s in strokes if s["reason"] is None]


# ─────────────────────────────────────────────────────────────────────────────
# Part 1 -- GATHER: the reader, on synthetic rasters (255 paper, 0 ink)
# ─────────────────────────────────────────────────────────────────────────────

class TestTheReader(unittest.TestCase):

    def test_a_slash_crossing_both_sides_of_one_stem_is_read_RED(self):
        img = _paper()
        _stem_ink(img)
        _slash(img, 150)
        got = _passing(_read(img))
        self.assertEqual(len(got), 1)
        s = got[0]
        self.assertGreater(s["angle_deg"], 15.0)
        self.assertLess(s["angle_deg"], 40.0)
        self.assertGreater(s["thickness_ratio"], 2.0)
        self.assertGreater(min(s["left_reach"], s["right_reach"]), 0.5)

    def test_the_slash_may_stand_at_the_stem_TIP_with_the_stem_poking_past(self):
        """Litolff p4: the slash sits at the tip, the stem showing a little
        above it. Same stroke, same reading."""
        img = _paper()
        _stem_ink(img)
        _slash(img, STOP + 12)
        self.assertEqual(len(_passing(_read(img))), 1)

    def test_a_double_slash_tremolo_is_TWO_strokes_RED(self):
        img = _paper()
        _stem_ink(img)
        _slash(img, 150)
        _slash(img, 150 + int(0.9 * SP))
        self.assertEqual(len(_passing(_read(img))), 2)

    def test_the_slash_leans_either_way(self):
        img = _paper()
        _stem_ink(img)
        _slash(img, 150, rise=-0.45)
        self.assertEqual(len(_passing(_read(img))), 1)

    # -- what it is NOT (each beside the positive control above) -----------

    def test_a_flag_hook_on_ONE_side_is_not_a_slash(self):
        img = _paper()
        _stem_ink(img)
        pts = np.array([[SX1 - 2, STOP], [SX1 + 20, STOP + 20],
                        [SX1 + 34, STOP + 60], [SX1 + 32, STOP + 84]], np.int32)
        cv2.polylines(img, [pts.reshape(-1, 1, 2)], False, 0, thickness=16)
        got = _read(img)
        self.assertEqual(_passing(got), [])
        self.assertTrue(all(s["reason"] == "one_sided" for s in got) or not got)

    def test_a_BEAM_across_a_middle_stem_joins_the_next_stem_and_is_not_a_slash(
            self):
        """The middle stem of a beamed group has ink on both sides; what makes
        it a beam is the stem at its END (Sean: beams connect to other notes,
        slashes never do)."""
        img = _paper()
        _stem_ink(img)
        left = (SX0 - 2 * SP, 100.0, 6.0, 240.0)
        right = (SX0 + 2 * SP, 100.0, 6.0, 240.0)
        for x0, _y, w, _h in (left, right):
            _stem_ink(img, int(x0), int(x0 + w))
        img[100:116, int(left[0]):int(right[0]) + 6] = 0      # the beam
        got = _read(img, others=[left, right])
        self.assertEqual(_passing(got), [])

    def test_a_thin_slur_line_crossing_the_stem_is_too_thin(self):
        img = _paper()
        _stem_ink(img)
        cv2.line(img, (int(303 - SP), 170), (int(303 + SP), 140), 0, 3)
        got = _read(img)
        self.assertEqual(_passing(got), [])
        self.assertIn("too_thin", [s["reason"] for s in got])

    def test_a_horizontal_ledger_line_through_the_stem_is_not_at_an_angle(self):
        img = _paper()
        _stem_ink(img)
        img[200:216, int(303 - 1.0 * SP):int(303 + 1.0 * SP)] = 0
        got = _read(img)
        self.assertEqual(_passing(got), [])
        self.assertIn("not_at_an_angle", [s["reason"] for s in got])

    def test_a_notehead_on_the_stem_end_is_not_a_slash(self):
        """A head hangs on ONE side of its stem's end; a chord's second puts
        one on each. The detector's head box at that end explains the ink."""
        img = _paper()
        _stem_ink(img)
        cv2.ellipse(img, (SX0 - 20, SBOT - 10), (26, 18), -25, 0, 360, 0, -1)
        cv2.ellipse(img, (SX1 + 20, SBOT - 40), (26, 18), -25, 0, 360, 0, -1)
        head_a = (SX0 - 46.0, SBOT - 28.0, 52.0, 36.0)
        head_b = (SX1 - 6.0, SBOT - 58.0, 52.0, 36.0)
        got = _read(img, heads=[head_a, head_b])
        self.assertEqual(_passing(got), [])

    def test_a_box_on_the_slash_at_one_end_is_the_suspect_when_the_other_end_has_a_head(
            self):
        """Litolff p6 `glyph/6/1/11/3/3`: the detector boxed the slash (at the
        stem's TIP) as a notehead, and the real head hangs at the other end.
        A stem has its head at one end, so a box at the tip does not explain
        the stroke -- the stroke is still read as a slash. The control above
        (`..._notehead_on_the_stem_end_...`) keeps the single-ended case."""
        img = _paper()
        _stem_ink(img)
        _slash(img, STOP + 14)
        cv2.ellipse(img, (SX0 - 20, SBOT - 10), (26, 18), -25, 0, 360, 0, -1)
        tip_box = (SX0 - 40.0, STOP - 4.0, 90.0, 36.0)      # the slash, boxed
        real_head = (SX0 - 46.0, SBOT - 28.0, 52.0, 36.0)
        self.assertEqual(len(_passing(_read(img, heads=[tip_box, real_head]))), 1)
        # the control: the SAME box alone at that end explains the stroke
        self.assertEqual(_passing(_read(img, heads=[tip_box])), [])

    def test_a_QUARTER_REST_zigzag_IS_read_as_a_slash_and_the_rest_rule_must_catch_it(
            self):
        """Brahms p1 (two of them read as slashes in this lane's own
        population): the CV stem reader finds a quarter rest's own stroke, and
        its diagonal strokes cross that axis on both sides exactly as a slash
        does."""
        img = _paper()
        cv2.line(img, (303, 100), (303, 250), 0, 8)            # the rest's body
        for y in (130, 190):                                   # angled bars across it
            cv2.line(img, (263, y + 22), (343, y - 22), 0, 20)
        box = (300.0, 100.0, 8.0, 150.0)         # what the CV stem reader draws
        got = _read(img, stem=box)
        # ⚠️ MEASURED AND REFUSED (see `gather.STEM_SLASH_BARE_WIDTH_FACTOR`):
        # the READER does pass this shape as a slash -- two Brahms p1 quarter
        # rests were read that way -- so the pin is that it SAYS so, and that
        # the rest decision (`TestARestOnASlashedStem`) is what keeps a rest a
        # rest, by the box's height.
        self.assertGreaterEqual(len(_passing(got)), 1)
        self.assertLess(_passing(got)[0]["bare_stem_spaces"], 1.5)

    def test_a_stem_with_a_long_bare_stretch_records_it(self):
        img = _paper()
        _stem_ink(img)
        _slash(img, STOP + 20)
        got = _passing(_read(img))
        self.assertEqual(len(got), 1)
        self.assertGreater(got[0]["bare_stem_spaces"], 3.0)

    def test_an_accent_or_a_staccato_dot_beside_a_stem_is_not_a_slash(self):
        img = _paper()
        _stem_ink(img)
        cv2.circle(img, (SX1 + 18, 150), 7, 0, -1)               # staccato dot
        cv2.circle(img, (SX0 - 18, 150), 7, 0, -1)               # and the other side
        self.assertEqual(_passing(_read(img)), [])

    def test_a_bare_stem_reads_ZERO_strokes_not_none(self):
        """⚠️ The reader RAN and found nothing: an empty list, never `None`."""
        img = _paper()
        _stem_ink(img)
        self.assertEqual(_read(img), [])

    def test_a_slash_next_to_a_neighbouring_stem_that_it_does_not_reach_stays_a_slash(
            self):
        """The control for `joins_another_stem`: a stem two spaces beyond the
        slash's end does not make it a beam."""
        img = _paper()
        _stem_ink(img)
        far = (SX0 + 4.0 * SP, 100.0, 6.0, 240.0)
        _stem_ink(img, int(far[0]), int(far[0] + 6))
        _slash(img, 150)
        self.assertEqual(len(_passing(_read(img, others=[far]))), 1)


class TestTheSlashInkIsBlankedForTheOtherReaders(unittest.TestCase):

    def _hook(self, img, tip_y):
        pts = np.array([[SX1 - 2, tip_y], [SX1 + 20, tip_y + 20],
                        [SX1 + 34, tip_y + 60], [SX1 + 32, tip_y + 84]], np.int32)
        cv2.polylines(img, [pts.reshape(-1, 1, 2)], False, 0, thickness=16)

    def test_blanking_removes_the_slash_and_keeps_the_stem_RED(self):
        img = _paper()
        _stem_ink(img)
        _slash(img, 200)
        strokes = _read(img)
        out = gather.blank_slashes(img, strokes)
        self.assertEqual(_passing(_read(out)), [])
        self.assertEqual(int((out[150:300, SX0:SX1] == 0).all()), 1)  # stem stays
        self.assertEqual(int((img == 0).sum() > (out == 0).sum()), 1)

    def test_a_real_hook_is_still_counted_beside_a_slash_RED(self):
        """The slash alone must not read as a hook, and a real hook at the tip
        must still be one hook with a slash below it on the same stem."""
        img = _paper()
        _stem_ink(img)
        self._hook(img, STOP)
        _slash(img, STOP + int(2.2 * SP))
        raw = gather.stem_tip_hooks(img, SX0, SX1, float(STOP), 1.0, SP,
                                    head_edge=float(SBOT - 40))
        clean = gather.stem_tip_hooks(gather.blank_slashes(img, _read(img)),
                                      SX0, SX1, float(STOP), 1.0, SP,
                                      head_edge=float(SBOT - 40))
        self.assertEqual(clean["hooks"], 1)
        self.assertIsNone(raw["hooks"])              # the slash spoiled the count

    def test_a_stem_with_only_a_slash_has_no_hook_at_all_RED(self):
        img = _paper()
        _stem_ink(img)
        _slash(img, STOP + int(1.6 * SP))
        clean = gather.blank_slashes(img, _read(img))
        r = gather.stem_tip_hooks(clean, SX0, SX1, float(STOP), 1.0, SP,
                                  head_edge=float(SBOT - 40))
        self.assertIsNone(r["hooks"])
        self.assertNotEqual(r["hooks_reason"], gather.HOOKS_UNCOUNTED_BOTH_SIDES)

    def test_a_plain_one_hook_flag_is_untouched_by_blanking(self):
        img = _paper()
        _stem_ink(img)
        self._hook(img, STOP)
        same = gather.blank_slashes(img, _read(img))
        self.assertTrue((same == img).all())


class _Cell:
    """The slice of a MeasureCell the reader touches."""

    def __init__(self, img):
        self.image_no_staff = img
        self.staff_line_ys_canonical = [100 + SP * 2 * k / 2.0 for k in range(5)]
        self.staff_line_thickness_canonical = LINE


class TestTheRowItFiles(unittest.TestCase):

    def _run(self, img, heads=()):
        log = Log()
        sub = R.cell(0, 0, 0, 0)
        row = log.observe(sub, Q.STEM, STEM_BOX, reader=READERS.CV_LINES,
                          frame="cell:0")
        gather._observe_stem_slashes(log, sub, "cell:0", _Cell(img),
                                     [(type("D", (), dict(
                                         x_canonical=STEM_BOX[0], y_canonical=STEM_BOX[1],
                                         width_canonical=STEM_BOX[2],
                                         height_canonical=STEM_BOX[3]))(), row.id)],
                                     list(heads), SP)
        return log, sub, row

    def test_a_slashed_stem_files_its_count_and_its_strokes_RED(self):
        img = _paper()
        _stem_ink(img)
        _slash(img, 150)
        log, sub, row = self._run(img)
        rows = log.rows(Q.STEM_SLASH, sub)
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r.value, 1)
        self.assertEqual(r.detail["stem_row_id"], row.id)
        self.assertEqual(r.reader, READERS.CV_STEM_SLASH)
        self.assertEqual(r.detail["strokes"][0]["reason"], None)
        x0, y0, x1, y1 = r.detail["strokes"][0]["box"]
        self.assertLess(x0, SX0)
        self.assertGreater(x1, SX1)

    def test_a_bare_stem_files_a_READ_zero_RED(self):
        img = _paper()
        _stem_ink(img)
        log, sub, _row = self._run(img)
        rows = log.rows(Q.STEM_SLASH, sub)
        self.assertEqual([r.value for r in rows], [0])

    def test_a_slashed_stem_with_no_head_box_at_either_end_says_so(self):
        """The population the lane reports: a slashed stem whose head the
        detector never boxed."""
        img = _paper()
        _stem_ink(img)
        _slash(img, 150)
        log, sub, _row = self._run(img)
        self.assertEqual(log.rows(Q.STEM_SLASH, sub)[0].detail["head_at_end"],
                         {"top": False, "bottom": False})

    def test_a_head_box_at_the_bottom_end_is_recorded_there(self):
        img = _paper()
        _stem_ink(img)
        _slash(img, 150)
        head = (SX0 - 46.0, SBOT - 28.0, 52.0, 36.0)
        log, sub, _row = self._run(img, heads=[head])
        self.assertEqual(log.rows(Q.STEM_SLASH, sub)[0].detail["head_at_end"],
                         {"top": False, "bottom": True})

    def test_no_raster_abstains_it_does_not_file_a_zero(self):
        log = Log()
        sub = R.cell(0, 0, 0, 0)
        cell = _Cell(None)
        row = log.observe(sub, Q.STEM, STEM_BOX, reader=READERS.CV_LINES,
                          frame="cell:0")
        d = type("D", (), dict(x_canonical=STEM_BOX[0], y_canonical=STEM_BOX[1],
                               width_canonical=STEM_BOX[2],
                               height_canonical=STEM_BOX[3]))()
        gather._observe_stem_slashes(log, sub, "cell:0", cell, [(d, row.id)],
                                     [], SP)
        self.assertEqual(len(log.rows(Q.STEM_SLASH, sub)), 0)


# ─────────────────────────────────────────────────────────────────────────────
# Part 2 -- ADJUDICATE: a slash is never a beam level
# ─────────────────────────────────────────────────────────────────────────────

X = 160


def _half_head(log, gi=0, x=X, y=90, head="noteheadHalf"):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.NOTEHEAD_CLASS, head, reader=READERS.DETECTOR,
                frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, (head, x, y, 20, 16),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    return g


def _slash_row(log, stem_row, *, box, ok=True):
    return log.observe(CELL, Q.STEM_SLASH, 1 if ok else 0,
                       reader=READERS.CV_STEM_SLASH, frame="cell:0",
                       stem_row_id=stem_row.id,
                       strokes=[{"reason": None, "box": list(box),
                                 "centreline": [box[0], box[3], box[2], box[1]],
                                 "thickness_px": 12.0,
                                 "angle_deg": 25.0, "thickness_ratio": 3.0,
                                 "left_reach": 0.9, "right_reach": 0.9,
                                 "y": (box[1] + box[3]) / 2.0}] if ok else [],
                       head_at_end={"top": False, "bottom": True})


class TestASlashIsNeverABeamLevel(unittest.TestCase):

    def _black_head_with_slash(self, with_row):
        """A BLACK-classed head on a stem with a thick stroke across it, boxed
        as a beam by the detector -- the 2.23-era tile-3 reading (0.5 beats)."""
        log = Log()
        _staff_space(log)
        g = _half_head(log, head="noteheadBlack")
        stem = _stem(log, x=X + 18, y=20, h=80)
        stroke = _beam(log, y=60, x0=X + 18 - 20, x1=X + 18 + 20)
        if with_row:
            _slash_row(log, stem, box=(X + 18 - 20, 54, X + 18 + 24, 70))
        adjudicate.run(log)
        return log, g, stroke

    def test_CONTROL_without_a_slash_row_the_stroke_still_counts_as_a_beam(self):
        """⚠️ It must be able to FAIL: with no `Q.STEM_SLASH` row the stroke is
        judged by the old rules alone, and a stroke over a stemmed black head
        is a beam level."""
        log, g, _stroke = self._black_head_with_slash(False)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.detail["beams_slash"], 0)
        self.assertGreater(v.detail["levels_certain"]
                           + v.detail["levels_possible"], 0)

    def test_a_stroke_inside_a_read_slash_is_not_a_beam_RED(self):
        log, g, _stroke = self._black_head_with_slash(True)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.detail["beams_slash"], 1)
        self.assertEqual(v.detail["levels_certain"], 0)
        self.assertEqual(v.detail["levels_possible"], 0)

    def test_a_slash_does_not_NARROW_the_head_it_is_not_a_mark_of_duration_RED(
            self):
        """Rule 8 guards a note a REFUSED stroke would have marked; a slash
        is not an absence, it is a seen mark of another kind. The half note
        stays a half note and a slashed black head is not narrowed to
        'eighth or quarter'."""
        log = Log()
        _staff_space(log)
        g = _half_head(log, head="noteheadHalf")
        stem = _stem(log, x=X + 18, y=20, h=80)
        _beam(log, y=60, x0=X - 2, x1=X + 38)
        _slash_row(log, stem, box=(X - 2, 54, X + 42, 70))
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 2.0)
        self.assertEqual(v.value["beam_levels"], 0)

    def test_CONTROL_a_half_note_without_a_slash_is_unchanged(self):
        log = Log()
        _staff_space(log)
        g = _half_head(log, head="noteheadHalf")
        _stem(log, x=X + 18, y=20, h=80)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual((v.outcome, v.value["beats"]),
                         (Outcome.DECIDED, 2.0))

    def test_CONTROL_a_real_two_note_beam_next_to_a_slashed_stem_stays_a_beam(
            self):
        """The slash footprint is local: a long beam over two stems is not
        inside it, whatever else the cell holds."""
        log = Log()
        _staff_space(log)
        g1 = _half_head(log, 0, x=65, y=90, head="noteheadBlack")
        g2 = _half_head(log, 1, x=180, y=90, head="noteheadBlack")
        s1 = _stem(log, x=83, y=38, h=60)
        _stem(log, x=198, y=38, h=60)
        _beam(log, y=40, x0=60, x1=200)
        _slash_row(log, s1, box=(60, 90, 120, 100))        # a slash elsewhere
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g1)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.5)
        self.assertEqual(v.detail["beams_slash"], 0)

    def test_a_slash_over_a_hollow_black_class_head_does_not_block_the_half_RED(
            self):
        """The 2.65 head-fill tile 3 case, at ADJUDICATE: a BLACK-classed head
        whose own ink reads decisively hollow, a stem with a tremolo slash on
        it, and a CV stroke over the slash. The slash is nothing on the stem,
        so the 2.23 narrowing (black | half | whole) is reached with the half
        among the candidates -- never `eighth` from a stroke that is a slash."""
        from tools.omr.tests.test_staged_duration import _notehead_ink
        log = Log()
        _staff_space(log)
        g = _half_head(log, head="noteheadBlack")
        stem = _stem(log, x=X + 18, y=20, h=80)
        _beam(log, y=60, x0=X + 18 - 20, x1=X + 18 + 20)
        _slash_row(log, stem, box=(X + 18 - 20, 54, X + 18 + 24, 70))
        _notehead_ink(log, g, center=0.1, ring=0.55)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.reason, "head_fill_from_ink")
        beats = sorted(c.value["beats"] for c in v.candidates)
        self.assertEqual(beats, [1.0, 2.0, 4.0])
        self.assertEqual(v.detail["beams_slash"], 1)

    def test_a_slash_is_not_a_flag_hook_either_RED(self):
        """The tip reader's ink, blanked of the slash upstream, files nothing;
        an old-style row that says `found` over a slash-only stem is
        discounted by the same fact."""
        log = Log()
        _staff_space(log)
        g = _half_head(log, head="noteheadBlack")
        stem = _stem(log, x=X + 18, y=20, h=80)
        _slash_row(log, stem, box=(X - 2, 24, X + 42, 40))
        log.observe(CELL, Q.STEM_TIP_INK, True, reader=READERS.CV_STEM_TIP,
                    frame="cell:0", stem_row_id=stem.id, end="top",
                    hooks=None, hooks_min=1, hooks_max=2,
                    hooks_reason="crosses_both_sides")
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertNotEqual(v.reason, "flag_ink_unread")


# ─────────────────────────────────────────────────────────────────────────────
# Part 3 -- a rest box on a slashed stem is a stem, not a rest
# ─────────────────────────────────────────────────────────────────────────────

def _rest_on_stem(log, cls="restQuarter", *, x=X, y=20, w=18, h=80,
                  slash=True):
    _staff_space(log)
    g = R.glyph(0, 0, 0, 0, 0)
    log.observe(g, Q.GLYPH_BOX, (cls, x, y, w, h), reader=READERS.DETECTOR,
                frame="cell:0", score=0.5)
    log.observe(g, Q.REST, cls, reader=READERS.DETECTOR, frame="cell:0",
                score=0.5)
    stem = _stem(log, x=x + 6, y=y, w=5, h=h)
    if slash:
        _slash_row(log, stem, box=(x - 14, y + 30, x + 34, y + 44))
    return g


class TestARestOnASlashedStem(unittest.TestCase):

    def test_a_quarter_rest_box_on_a_slashed_stem_is_refused_RED(self):
        log = Log()
        g = _rest_on_stem(log)
        adjudicate.run(log)
        v = log.verdict(Q.REST_IS_NOT_A_REST, g)
        self.assertEqual(v.value, True)
        self.assertEqual(v.reason, "rest_is_a_slashed_stem")

    def test_CONTROL_a_plain_quarter_rest_height_with_a_slash_row_stays_a_rest_RED(
            self):
        """The Brahms p1 case: the reader passes a quarter rest's own zigzag
        as a slash, and the rest is ~3 spaces tall. The height says rest."""
        log = Log()
        g = _rest_on_stem(log, h=48)                 # 3 spaces at SPACE=16
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.REST_IS_NOT_A_REST, g).value, False)

    def test_CONTROL_the_same_rest_box_without_a_slash_stays_a_rest(self):
        log = Log()
        g = _rest_on_stem(log, slash=False)
        adjudicate.run(log)
        v = log.verdict(Q.REST_IS_NOT_A_REST, g)
        self.assertEqual(v.value, False)

    def test_CONTROL_a_slash_elsewhere_in_the_cell_leaves_a_rest_alone(self):
        log = Log()
        g = _rest_on_stem(log, slash=False)
        far = _stem(log, x=X + 200, y=20, w=5, h=80)
        _slash_row(log, far, box=(X + 186, 50, X + 234, 64))
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.REST_IS_NOT_A_REST, g).value, False)


# ─────────────────────────────────────────────────────────────────────────────
# Part 4 -- a notehead-classed box that is the slash is refused
# ─────────────────────────────────────────────────────────────────────────────

class TestANoteheadBoxOnASlash(unittest.TestCase):

    def _box_on_shaft(self, log, *, with_row):
        _staff_space(log)
        g = R.glyph(0, 0, 0, 0, 0)
        # the box sits mid-shaft, the stem 100 px long, box centre 40 px from
        # either end
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.7)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlack", X - 4, 52, 44, 28),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.7)
        stem = _stem(log, x=X + 14, y=10, w=6, h=110)
        if with_row:
            _slash_row(log, stem, box=(X - 2, 56, X + 38, 76))
        return g

    def test_a_box_that_covers_a_read_slash_mid_shaft_is_not_a_notehead_RED(
            self):
        log = Log()
        g = self._box_on_shaft(log, with_row=True)
        adjudicate.run(log)
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)
        self.assertEqual(v.value, True)
        self.assertEqual(v.reason, "tremolo_slash_crosses_stem")

    def test_CONTROL_the_same_box_without_a_slash_reading_is_kept(self):
        log = Log()
        g = self._box_on_shaft(log, with_row=False)
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g).value,
                         False)

    def test_CONTROL_a_real_head_at_the_stem_end_beside_a_slash_is_kept(self):
        log = Log()
        _staff_space(log)
        g = R.glyph(0, 0, 0, 0, 0)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadHalf",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_BOX, ("noteheadHalf", X - 8, 100, 26, 20),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        stem = _stem(log, x=X + 14, y=10, w=6, h=110)
        _slash_row(log, stem, box=(X - 2, 40, X + 38, 60))
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g).value,
                         False)


if __name__ == "__main__":
    unittest.main()
