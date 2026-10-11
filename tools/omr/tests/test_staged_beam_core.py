"""ROADMAP 2.82 -- a real beam in a box WIDER than the beam is not "too thin".

Brahms 317803 pdf 0 (Sean's hand truth), staff 0 bar 3: three beamed chords, a real
beam 0.6 staff spaces thick (3.2 staff lines on this plate). The detector boxed it 362 px
wide against its 152 -- the box runs 210 px past the beam's left end over a bare staff
line. `gather.beam_stroke_ink` reports the MEDIAN of the ink run through the stroke's
columns, and 58% of this stroke's columns are a staff line, so the median read 1.3 lines
and `rhythm._not_a_beam_by_ink` refused the only beam the cell holds as `too_thin`:
six heads read "eighth or quarter" instead of eighth. The thickness cut (1.75) is not
wrong -- every beam stroke that fits its beam measures 2.5-3.9 on that page -- the
reading was taken over columns that are not the beam's.

THE FIX READS THE CORE. The stroke's longest stretch of beam-thick columns
(`gather.BEAM_INK_CORE_RATIO`), its thickness, and whether a stem stands at EACH end of
the core -- off the ink. ADJUDICATE keeps a stroke whose median is thin only where its
core is long enough and stands on a stem at both ends: "a beam must not only connect to
its note but also to another note" (Sean), applied at the ends of the beam-thick ink
instead of the ends of the box. A hairpin's thick end has no stem at either end of it.

⚠️ RUN RED FIRST (the commit says so): every GATHER test fails on the tree without
`core` in `beam_stroke_ink`; the ADJUDICATE tests fail on `rhythm` reading it.

⚠️ THE CONTROLS THAT CAN FAIL: the same box with the core's stems missing (a hairpin
line's thick end) and a ledger line stay refused; an old record with no `core` key is
judged exactly as it was; a core whose stems could not be read does NOT rescue
(rule 8: cannot tell is not "a beam").
"""

from __future__ import annotations

import unittest

import numpy as np

from tools.omr.staged import adjudicate, evaluate                # noqa: F401
from tools.omr.staged import adjudicators, consequences          # noqa: F401
from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import Log, Outcome, Q, READERS

from tools.omr.tests.test_staged_beam_two_stems import (
    CELL, LINES, SP, _bar, _group, _head_with_stem, _measure, _page,
    _stem_down)
from tools.omr.tests.test_staged_duration import _beam, _staff_space


# ─────────────────────────────────────────────────────────────────────────────
# Part 1 -- the reading: the core of a stroke, on synthetic rasters
# ─────────────────────────────────────────────────────────────────────────────

def _overshooting_beam(*, line_thickness=3, beam_thickness=10, y=96):
    """A real beam over the staff line at LINES[0]=100, standing on a stem at each
    end, inside a box that runs 130 px (6.5 spaces) past its left end."""
    img = _page(line_thickness=line_thickness)
    _bar(img, 170, 250, y, beam_thickness)
    _stem_down(img, 170, 36, y + 4)
    _stem_down(img, 247, 36, y + 4)
    return img, (40, y, 210, beam_thickness)


class TestTheCoreOfAStroke(unittest.TestCase):

    def test_the_MEDIAN_of_an_overshooting_box_is_the_staff_line_not_the_beam(
            self):
        """The defect, pinned: this is what 2.74 read on Brahms pdf 0 q82."""
        img, box = _overshooting_beam()
        m = _measure(img, box)
        self.assertIsNotNone(m)
        self.assertLess(m["thickness_ratio"], 1.75)

    def test_the_core_of_that_box_is_the_beam_and_it_stands_on_a_stem_at_each_end(
            self):
        img, box = _overshooting_beam()
        m = _measure(img, box)
        core = m["core"]
        self.assertIsNotNone(core)
        self.assertGreaterEqual(core["thickness_ratio"], 3.0)
        self.assertGreaterEqual(core["spaces"], 3.5)
        self.assertLessEqual(core["spaces"], 4.5)
        self.assertEqual([e["found"] for e in core["end_stems"]], [True, True])
        # canonical x of the core: the beam's own columns (170..250), not the box's
        self.assertGreaterEqual(core["x0"], 165)
        self.assertLessEqual(core["x1"], 255)

    def test_a_beam_that_fills_its_box_has_a_core_that_agrees_with_its_median(
            self):
        """POSITIVE CONTROL: the ordinary stroke is unchanged -- thick by its median
        and its core is the whole of it."""
        img = _page()
        _bar(img, 60, 200, 40, 10)
        _stem_down(img, 60, 40, 100)
        _stem_down(img, 197, 40, 100)
        m = _measure(img, (60, 40, 140, 10))
        self.assertGreaterEqual(m["thickness_ratio"], 3.0)
        self.assertGreaterEqual(m["core"]["spaces"], 6.0)
        self.assertEqual([e["found"] for e in m["core"]["end_stems"]],
                         [True, True])

    def test_a_hairpins_thick_end_has_a_core_but_NO_stem_at_its_ends(self):
        """A hairpin whose lines are fused toward its apex end is thick for
        several spaces (Brahms: 2.5-5.7 spaces at 2+ lines). That is why a long thick
        stretch alone cannot rescue a stroke: nothing stands on its ends."""
        img = _page()
        for x in range(60, 340):
            t = 3 if x < 228 else int(3 + (x - 228) * 11 / 112.0)
            yc = 60
            img[yc - t // 2: yc - t // 2 + t, x] = 0
        m = _measure(img, (60, 50, 280, 20))
        self.assertLess(m["thickness_ratio"], 1.75)
        self.assertIsNotNone(m["core"])
        self.assertEqual([e["found"] for e in m["core"]["end_stems"]],
                         [False, False])

    def test_a_stem_hangs_from_the_beam_on_ONE_side_a_barline_goes_THROUGH(self):
        """⚠️ POSITIVE CONTROL AND ITS FAILURE: the core's stems at the real beam's
        ends are `through: False`; a bar's staff line thick on a bad plate, with a
        barline at each end, finds a vertical run at both ends of its core too --
        and each of those runs leaves the band on BOTH sides."""
        img, box = _overshooting_beam()
        stems = _measure(img, box)["core"]["end_stems"]
        self.assertEqual([e["through"] for e in stems], [False, False])
        # the staff line at LINES[2] thick (7 px: 2.3 lines of the 3 px lines)
        # between two barlines running the whole staff
        img = _page()
        img[LINES[2] - 2:LINES[2] + 5, 40:240] = 0
        _stem_down(img, 38, 60, 200)
        _stem_down(img, 240, 60, 200)
        m = _measure(img, (40, LINES[2] - 2, 200, 7))
        self.assertIsNotNone(m["core"])
        self.assertEqual([e["found"] for e in m["core"]["end_stems"]],
                         [True, True])
        self.assertEqual([e["through"] for e in m["core"]["end_stems"]],
                         [True, True])

    def test_a_slur_has_no_core(self):
        img = _page()
        _arc(img, 60, 200, 40, 10, 5)
        m = _measure(img, (60, 40, 140, 16))
        self.assertLess(m["thickness_ratio"], 1.75)
        self.assertIsNone(m["core"])

    def test_a_row_of_heads_on_a_ledger_line_is_too_short_to_be_a_core(self):
        """POSITIVE CONTROL for the length floor: a head is ~1.3 spaces wide."""
        img = _page()
        _bar(img, 60, 200, 40, 3)                       # a ledger line
        for x0 in (80, 130):                            # two heads of 1.1 spaces
            img[34:50, x0:x0 + 22] = 0
        m = _measure(img, (60, 36, 140, 10))
        self.assertTrue(m["core"] is None or m["core"]["spaces"] < 2.0)

    def test_the_core_is_read_at_the_strokes_local_staff_line(self):
        """CLAUDE.md §10: the same 10 px bar is 3.3 lines where the lines are 3 px
        and 1.4 where they are 7 px -- the core's ratio is local too."""
        img = _page(line_thickness=3, right_line_thickness=7, w=400)
        _bar(img, 220, 340, 40, 10)
        _stem_down(img, 220, 40, 100)
        _stem_down(img, 337, 40, 100)
        m = _measure(img, (220, 40, 120, 10))
        self.assertIsNone(m["core"])                 # 1.4 lines: nothing beam-thick

    def test_without_staff_lines_the_core_is_UNREAD_not_defaulted(self):
        img = np.full((320, 400), 255, dtype=np.uint8)
        _bar(img, 60, 200, 40, 10)
        m = gather.beam_stroke_ink(img, (60, 40, 140, 10), SP, [])
        self.assertIsNone(m["thickness_ratio"])
        self.assertIsNone(m["core"])

    def test_the_gather_and_adjudicate_cuts_for_thick_are_the_same_number(self):
        """The reading's per-column cut and the decision's cut are ONE number
        (`rhythm.BEAM_THICKNESS_RATIO_MIN`); two spellings can drift."""
        self.assertEqual(gather.BEAM_INK_CORE_RATIO,
                         rhythm.BEAM_THICKNESS_RATIO_MIN)


def _arc(img, x0, x1, y_ends, sag, thickness):
    mid = (x0 + x1) / 2.0
    half = (x1 - x0) / 2.0
    for x in range(x0, x1):
        yc = y_ends + sag * (1.0 - ((x - mid) / half) ** 2)
        t = int(thickness)
        img[int(yc - t / 2): int(yc - t / 2) + t, x] = 0


# ─────────────────────────────────────────────────────────────────────────────
# Part 2 -- ADJUDICATE reads the core
# ─────────────────────────────────────────────────────────────────────────────

#: the two heads `_head_with_stem` files for `_overshoot_group` (canonical x, y, w, h):
#: below the beam at y~40, the stems rising 60 px to it.
HEADS = [(65, 90, 20, 16), (180, 90, 20, 16)]


def _core(*, x0=60, x1=200, ratio=3.2, ends=(True, True), side="down"):
    """The core of a stroke: a stem at each end running DOWN to a head, as in
    `_overshoot_group`."""
    return {"x0": x0, "x1": x1, "spaces": (x1 - x0) / float(SP),
            "thickness_ratio": ratio, "thickness_px": 12.0,
            "end_stems": [{"found": e, "x": (x0 if i == 0 else x1) if e else None,
                           "through": False, "side": side if e else None}
                          for i, e in enumerate(ends)],
            "band": [40.0, 52.0]}


def _ink_with_core(log, stroke, *, ratio=1.3, sag=0.02, ends=(False, True),
                   core="absent", **core_kw):
    """One `Q.BEAM_STROKE_INK` row of a stroke whose MEDIAN is thin. `core="absent"`
    omits the key (a record from before 2.82); `None` files a read `None` (no core)."""
    ends_d = [{"found": e, "x": 100 if e else None} for e in ends]
    detail = dict(beam_row_id=stroke.id, thickness_px=4.0, line_px=3.0,
                  thickness_ratio=ratio, thickness_spaces=0.2,
                  sagitta_spaces=sag, end_stems=ends_d, columns=200,
                  cover=1.0, band=[40.0, 44.0])
    if core != "absent":
        detail["core"] = _core(**core_kw) if core == "build" else core
    return log.observe(CELL, Q.BEAM_STROKE_INK, 0.2,
                       reader=READERS.CV_BEAM_SHAPE, frame="cell:0", **detail)


def _overshoot_group(log):
    """Two stemmed heads under ONE detector box that runs well past the beam."""
    _staff_space(log, SP)
    g1, _ = _head_with_stem(log, 0, 65)
    g2, _ = _head_with_stem(log, 1, 180)
    stroke = _beam(log, y=40, x0=0, x1=210, reader=READERS.DETECTOR)
    return g1, g2, stroke


class TestAThinMedianWithAStemmedCoreIsABeam(unittest.TestCase):

    def test_brahms_q82_both_heads_read_eighth(self):
        log = Log()
        g1, g2, stroke = _overshoot_group(log)
        _ink_with_core(log, stroke, core="build")
        adjudicate.run(log)
        for g in (g1, g2):
            v = log.verdict(Q.DURATION, g)
            self.assertEqual(v.outcome, Outcome.DECIDED)
            self.assertEqual(v.value["beats"], 0.5)
            self.assertEqual(v.detail["beams_not_by_ink"], 0)

    def test_a_head_under_only_the_OVERSHOOT_of_the_box_is_not_under_the_beam(
            self):
        """⚠️ The box is 210 px wide and the core 140: a third head at the box's far
        left stands on a staff line, not under the beam. For it the stroke is refused
        `beyond_core` -- 2.74's own refusal of the whole stroke -- and it NARROWS (a
        stemmed head, its only stroke gone) instead of being decided from a beam it
        does not stand under. The heads under the core are rescued all the same."""
        log = Log()
        g1, g2, stroke = _overshoot_group(log)
        g0, _ = _head_with_stem(log, 2, 5)
        _ink_with_core(log, stroke, core="build")
        adjudicate.run(log)
        v0 = log.verdict(Q.DURATION, g0)
        self.assertEqual(v0.detail["beams_not_by_ink_why"], {"beyond_core": 1})
        self.assertEqual(v0.outcome, Outcome.NARROWED)
        for g in (g1, g2):
            v = log.verdict(Q.DURATION, g)
            self.assertEqual(v.outcome, Outcome.DECIDED)
            self.assertEqual(v.value["beats"], 0.5)

    def test_CONTROL_the_same_box_without_a_core_is_refused_as_it_was(self):
        """⚠️ It must be able to FAIL: with a read `None` core the stroke is
        `too_thin`, and the stemmed head is NARROWED, not decided."""
        log = Log()
        g1, g2, stroke = _overshoot_group(log)
        _ink_with_core(log, stroke, core=None)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g1)
        self.assertEqual(v.detail["beams_not_by_ink_why"], {"too_thin": 1})
        self.assertEqual(v.outcome, Outcome.NARROWED)

    def test_an_OLD_record_with_no_core_key_is_judged_exactly_as_it_was(self):
        log = Log()
        g1, g2, stroke = _overshoot_group(log)
        _ink_with_core(log, stroke)                  # no `core` key at all
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g1)
        self.assertEqual(v.detail["beams_not_by_ink_why"], {"too_thin": 1})

    def test_a_core_with_a_stem_at_ONE_end_does_not_rescue_a_thin_stroke(self):
        """A hairpin's thick end at the edge of a note's stem. Both ends or none."""
        for ends in ((True, False), (False, True), (False, False)):
            log = Log()
            g1, g2, stroke = _overshoot_group(log)
            _ink_with_core(log, stroke, core=_core(ends=ends))
            adjudicate.run(log)
            v = log.verdict(Q.DURATION, g1)
            self.assertEqual(v.detail["beams_not_by_ink_why"],
                             {"too_thin": 1}, ends)

    def test_a_core_standing_between_two_BARLINES_does_not_rescue(self):
        """Litolff p16: the bottom staff line, thick on that plate, between the bar's
        two barlines. Both ends `found`, both `through` -- not stems."""
        log = Log()
        g1, g2, stroke = _overshoot_group(log)
        core = _core()
        for e in core["end_stems"]:
            e["through"] = True
        _ink_with_core(log, stroke, core=core)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g1)
        self.assertEqual(v.detail["beams_not_by_ink_why"], {"too_thin": 1})

    def test_a_stem_that_leads_to_NO_HEAD_is_not_a_beams_stem(self):
        """⚠️ THE CONTROL THAT FAILS THE INK-ONLY RULE. On Litolff's merging plate a thick
        staff line between barlines, or lattice verticals, "stands on a stem at each
        end" by the ink alone (3 of the first 15 strokes that rule rescued were exactly
        that). Here both ends are a one-sided vertical run (found, not through) and no
        detector-boxed head stands at either: still `too_thin`."""
        log = Log()
        g1, g2, stroke = _overshoot_group(log)
        _ink_with_core(log, stroke, core=_core(x0=20, x1=240))   # no head near 20 or 240
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g1)
        self.assertEqual(v.detail["beams_not_by_ink_why"], {"too_thin": 1})

    def test_a_head_on_the_WRONG_SIDE_of_the_stem_run_does_not_count(self):
        """The ink says the stems run UP from the beam; the heads are below it."""
        log = Log()
        g1, g2, stroke = _overshoot_group(log)
        _ink_with_core(log, stroke, core=_core(side="up"))
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g1)
        self.assertEqual(v.detail["beams_not_by_ink_why"], {"too_thin": 1})

    def test_a_core_whose_stems_could_NOT_be_read_does_not_rescue(self):
        """Rule 8: `found: None` is "the ink could not say", not "a stem"."""
        log = Log()
        g1, g2, stroke = _overshoot_group(log)
        core = _core()
        core["end_stems"] = [{"found": None, "x": None}, {"found": True, "x": 200}]
        _ink_with_core(log, stroke, core=core)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g1)
        self.assertEqual(v.detail["beams_not_by_ink_why"], {"too_thin": 1})

    def test_a_core_under_the_thickness_cut_does_not_rescue(self):
        log = Log()
        g1, g2, stroke = _overshoot_group(log)
        _ink_with_core(log, stroke, core=_core(ratio=1.5))
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g1)
        self.assertEqual(v.detail["beams_not_by_ink_why"], {"too_thin": 1})

    def test_a_rescued_stroke_still_has_to_be_straight(self):
        """The core does not excuse a bowed box: `not_straight` still fires."""
        log = Log()
        g1, g2, stroke = _overshoot_group(log)
        _ink_with_core(log, stroke, core="build", sag=0.7)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g1)
        self.assertEqual(v.detail["beams_not_by_ink_why"], {"not_straight": 1})

    def test_a_hairpin_line_boxed_as_a_beam_stays_refused(self):
        """The 2.74 gain, guarded: tile 21's thin stroke beside a real beam."""
        log = Log()
        g1, g2, beam = _group(log)
        slur = _beam(log, y=34, x0=40, x1=220)
        from tools.omr.tests.test_staged_beam_two_stems import _ink
        _ink(log, beam)
        _ink(log, slur, ratio=1.1, sag=0.02, ends=(False, False))
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g1)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.5)
        self.assertEqual(v.detail["beams_not_by_ink_why"], {"too_thin": 1})

    def test_a_ledger_line_stroke_stays_refused(self):
        """A ledger line is thin, short and has no stem: no core, still `too_thin`."""
        log = Log()
        g1, g2, beam = _group(log)
        ledger = _beam(log, y=34, x0=40, x1=130)
        from tools.omr.tests.test_staged_beam_two_stems import _ink
        _ink(log, beam)
        _ink_with_core(log, ledger, ratio=1.0, ends=(False, False), core=None)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g1)
        self.assertEqual(v.value["beats"], 0.5)
        self.assertEqual(v.detail["beams_not_by_ink_why"], {"too_thin": 1})


def _two_notes_no_stems_under_a_bar(log, *, bar_y=40):
    """Two heads whose stems the stem finder never registered (fused with the stack of heads on
    them: `too WIDE`), and ONE thick straight stroke below them whose ink reads a stem at ONE end
    only -- Litolff pdf 10 tile 02 / pdf 13 tile 29, printed eighths, refused `one_stem`."""
    from tools.omr.tests.test_staged_beam_two_stems import _ink
    from tools.omr.tests.test_staged_duration import _note
    _staff_space(log, SP)
    g1 = _note(log, 0, x=65)
    g2 = _note(log, 1, x=180)
    bar = _beam(log, y=bar_y, x0=55, x1=195, reader=READERS.DETECTOR)
    _ink(log, bar, ratio=3.0, sag=0.01, ends=(False, True))
    return g1, g2, bar


class TestOneStemNeedsPositiveEvidence(unittest.TestCase):
    """Sean, 2026-10-10: *"The 'doesn't touch more than one stem' is off."* `one_stem` fired where
    the OTHER stem simply was not registered; "cannot tell" is not "only one stem" (rule 8)."""

    def test_two_notes_under_a_thick_bar_are_not_one_stem(self):
        log = Log()
        g1, g2, bar = _two_notes_no_stems_under_a_bar(log)
        adjudicate.run(log)
        for g in (g1, g2):
            v = log.verdict(Q.DURATION, g)
            self.assertEqual(v.detail["beams_not_by_ink"], 0)
            self.assertNotIn("one_stem", v.detail["beams_not_by_ink_why"])

    def test_CONTROL_ONE_note_under_the_same_bar_is_still_one_stem(self):
        """⚠️ It must be able to FAIL: with a single head at the stroke there is nothing for a
        second stem to hang from -- positive evidence -- and the refusal stands."""
        from tools.omr.tests.test_staged_beam_two_stems import _ink
        from tools.omr.tests.test_staged_duration import _note
        log = Log()
        _staff_space(log, SP)
        g = _note(log, 0, x=65)
        bar = _beam(log, y=40, x0=55, x1=195, reader=READERS.DETECTOR)
        _ink(log, bar, ratio=3.0, sag=0.01, ends=(False, True))
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.detail["beams_not_by_ink_why"], {"one_stem": 1})

    def test_CONTROL_a_second_note_FAR_from_the_stroke_is_not_a_second_stem(self):
        log = Log()
        g1, g2, bar = _two_notes_no_stems_under_a_bar(log, bar_y=300)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g1)
        self.assertEqual(v.detail["beams_not_by_ink_why"], {"one_stem": 1})

    def test_a_hairpins_thick_end_over_two_notes_stays_refused_one_stem(self):
        """⚠️ THE REGRESSION THE FIRST VERSION SHIPPED: two 17-space hairpin boxes at 1.82 lines
        (Brahms pdf 18) have two head columns under them wherever they lie, and heads alone kept
        them -- three heads read sixteenth and dotted eighth. The ink READ their thick cores'
        two ends and found no stem at either: positive evidence, the refusal stands."""
        from tools.omr.tests.test_staged_duration import _note
        log = Log()
        _staff_space(log, SP)
        g1 = _note(log, 0, x=65)
        g2 = _note(log, 1, x=180)
        bar = _beam(log, y=40, x0=55, x1=195, reader=READERS.DETECTOR)
        _ink_with_core(log, bar, ratio=1.9, ends=(False, True),
                       core=_core(x0=60, x1=190, ends=(False, False), side="up"))
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g1)
        self.assertEqual(v.detail["beams_not_by_ink_why"], {"one_stem": 1})

    def test_a_core_with_a_stem_at_ONE_end_over_two_notes_stays(self):
        """Litolff pdf 13 tile 29's shape: the core reads a stem at one end only (the other
        stem is fused with its head and the end window misses it). Not positive evidence."""
        from tools.omr.tests.test_staged_duration import _note
        log = Log()
        _staff_space(log, SP)
        g1 = _note(log, 0, x=65)
        g2 = _note(log, 1, x=180)
        bar = _beam(log, y=40, x0=55, x1=195, reader=READERS.DETECTOR)
        _ink_with_core(log, bar, ratio=3.0, ends=(False, True),
                       core=_core(x0=60, x1=190, ends=(False, True), side="up"))
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g1)
        self.assertEqual(v.detail["beams_not_by_ink"], 0)

    def test_the_head_columns_of_a_chord_are_ONE_column(self):
        box = (55.0, 40.0, 140.0, 4.0)
        chord = [(55, 0, 20, 16), (57, 14, 20, 16)]          # two stacked heads, one column
        self.assertEqual(rhythm._head_columns_at_stroke(box, chord, SP), 1)
        notes = [(55, 0, 20, 16), (170, 0, 20, 16)]
        self.assertEqual(rhythm._head_columns_at_stroke(box, notes, SP), 2)
        self.assertEqual(rhythm._head_columns_at_stroke(box, notes, 0.0), 0)    # no unit: nothing claimed
        self.assertEqual(rhythm._head_columns_at_stroke(None, notes, SP), 0)

    def test_a_thick_stroke_whose_CORE_stands_on_two_stems_is_not_one_stem(self):
        """The box's own ends are not a beam's ends: ink at the box ends [False, False] says
        nothing where the thick core's ends read a stem each that leads to a head."""
        from tools.omr.tests.test_staged_duration import _note
        log = Log()
        _staff_space(log, SP)
        g1 = _note(log, 0, x=65)
        g2 = _note(log, 1, x=180)
        bar = _beam(log, y=40, x0=0, x1=260, reader=READERS.DETECTOR)
        _ink_with_core(log, bar, ratio=3.0, ends=(False, False),
                       core=_core(x0=60, x1=190, side="up"))
        adjudicate.run(log)
        for g in (g1, g2):
            v = log.verdict(Q.DURATION, g)
            self.assertEqual(v.detail["beams_not_by_ink"], 0)


class TestOneSpellingOfThin(unittest.TestCase):
    """`rhythm._beam_anchor_ids` and the notehead-precision beam-piece refusal read the
    same thickness test; a rescued stroke is one beam for all three."""

    def test_a_rescued_stroke_is_not_thin(self):
        log = Log()
        g1, g2, stroke = _overshoot_group(log)
        row = _ink_with_core(log, stroke, core="build")
        self.assertFalse(rhythm.stroke_thin_by_ink(row.detail, HEADS, SP))
        # ...and the same stroke with NO head in sight is thin (heads empty -> never rescued)
        self.assertTrue(rhythm.stroke_thin_by_ink(row.detail))

    def test_an_unrescued_thin_stroke_is_thin(self):
        log = Log()
        g1, g2, stroke = _overshoot_group(log)
        row = _ink_with_core(log, stroke, core=None)
        self.assertTrue(rhythm.stroke_thin_by_ink(row.detail, HEADS, SP))

    def test_a_thick_stroke_is_not_thin(self):
        self.assertFalse(rhythm.stroke_thin_by_ink({"thickness_ratio": 3.0}))

    def test_an_unread_thickness_is_not_thin(self):
        self.assertFalse(rhythm.stroke_thin_by_ink({"thickness_ratio": None}))
        self.assertFalse(rhythm.stroke_thin_by_ink({}))


if __name__ == "__main__":
    unittest.main()
