"""The dynamics rungs of the staged pipeline: the letters, the wedges, the word.

⚠️ THE CENTRAL TEST HERE IS `TestOwnershipMovesTheLetter`, and it is the one
that must go RED if the ownership query is removed. Everything else in this
file guards a frame or a state distinction; that one guards the actual fix.

The measured fault it stands for: `export.measure_dynamics` uses NO VERTICAL
INFORMATION AT ALL, and over 1246 letters on 18 pages of 9 publishers **24% of
letters stand in the band of the staff IMMEDIATELY ABOVE their own** -- because
a measure cell is the staff plus four to six staff spaces of air. A band GATE
was measured and refused (it under-emits on both arms, because 83% of
re-attributed letters are the target staff's SOLE evidence). The letter has to
MOVE, which is `Q.GLYPH_OWNER`'s question.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

import numpy as np

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Outcome, Q, READERS, Scope

UPPER = R.staff(0, 0, 0)
LOWER = R.staff(0, 0, 1)


def _letter(log, glyph, letter, x0, x1, *, y=100.0, bottom=90.0, spacing=10.0):
    """One `Q.DYNAMIC_LETTER` row, in PAGE pixels, as the gatherer writes it."""
    return log.observe(
        glyph, Q.DYNAMIC_LETTER, "dynamic" + letter.upper(),
        reader=READERS.DETECTOR, frame=G.FRAME_PAGE, score=0.8,
        letter=letter, cell_frame="cell:0",
        bbox_page_px=[x0, y - 5.0, x1, y + 5.0],
        x_center_page=(x0 + x1) / 2.0, y_center_page=y,
        staff_bottom_line_page=bottom, staff_spacing_px=spacing,
        band_offset_spaces=(y - bottom) / spacing, in_hairpin_band=True)


def _band(log, glyph, offset):
    """One `Q.DYNAMIC_BAND_POSITION` row, promoted exactly as `positions.
    gather_band_positions` files it -- an independent reading, on the SAME
    glyph subject a `Q.DYNAMIC_LETTER` row names."""
    return log.observe(glyph, Q.DYNAMIC_BAND_POSITION, float(offset),
                       reader=READERS.GEOMETRY, frame=G.FRAME_PAGE)


def _contest(log, glyph, *, winner, loser, near=1.0, far=4.0):
    """A real cross-staff contest, so `Q.GLYPH_OWNER` is DECIDED by the real
    adjudicator rather than stubbed. ⚠️ Stubbing it would have tested this
    file's own fixture; the composition is the thing under test."""
    log.observe(glyph, Q.GLYPH_BAND_DISTANCE, far, reader=READERS.GEOMETRY,
                frame=G.FRAME_PAGE, candidate=loser.to_key(), own=True,
                position_in_candidate=2.0)
    log.observe(glyph, Q.GLYPH_BAND_DISTANCE, near, reader=READERS.GEOMETRY,
                frame=G.FRAME_PAGE, candidate=winner.to_key(), own=False,
                position_in_candidate=2.0)


class TestSpellingTheWord(unittest.TestCase):
    def _decide(self, log, cell=R.cell(0, 0, 0, 0)):
        log.freeze()
        adjudicate.run(log)
        return log.verdict(Q.DYNAMIC, cell)

    def test_two_adjacent_f_glyphs_are_one_ff(self):
        log = Log()
        _letter(log, R.glyph(0, 0, 0, 0, 0), "f", 100.0, 110.0)
        _letter(log, R.glyph(0, 0, 0, 0, 1), "f", 112.0, 122.0)
        v = self._decide(log)
        self.assertEqual(v.value, ["ff"])
        self.assertEqual(v.reason, "spelled")

    def test_letters_far_apart_are_two_words(self):
        log = Log()
        _letter(log, R.glyph(0, 0, 0, 0, 0), "p", 100.0, 110.0)
        _letter(log, R.glyph(0, 0, 0, 0, 1), "f", 400.0, 410.0)
        v = self._decide(log)
        self.assertEqual(v.value, ["p", "f"])

    def test_a_lone_s_NARROWS_rather_than_vanishing(self):
        """⚠️ 'There is a mark here and I cannot spell it' is a DIFFERENT
        answer from 'I saw nothing', and it is the answer for the dominant
        failure -- an `sf` whose `f` was never detected."""
        log = Log()
        _letter(log, R.glyph(0, 0, 0, 0, 0), "s", 100.0, 110.0)
        v = self._decide(log)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "unspellable")
        self.assertEqual([c.value for c in v.candidates], ["sf", "sfp", "sfz"])

    def test_a_good_word_beside_a_bad_one_is_still_DECIDED(self):
        """A cell holding one readable `ff` has decided something; reporting
        the whole cell as narrowed would lose it."""
        log = Log()
        _letter(log, R.glyph(0, 0, 0, 0, 0), "f", 100.0, 110.0)
        _letter(log, R.glyph(0, 0, 0, 0, 1), "f", 112.0, 122.0)
        _letter(log, R.glyph(0, 0, 0, 0, 2), "s", 400.0, 410.0)
        v = self._decide(log)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, ["ff"])


class TestOwnershipResolvesTheContest(unittest.TestCase):
    """⚠️ THE FIX. Remove the `Q.GLYPH_OWNER` query and these go RED.

    ⚠️⚠️ THIS CLASS WAS REWRITTEN 2026-09-11 BECAUSE ITS FIXTURE WAS A PAGE
    GATHER CANNOT PRODUCE. It filed ONE letter and a contest over it, and then
    asserted the owning staff *gained* a letter it never detected — but
    `gather_contested_glyphs` files a `Q.GLYPH_BAND_DISTANCE` row only where
    TWO same-class detections on DIFFERENT staves overlap, so a lone letter is
    never contested and never offered to another staff at all. The test passed,
    and the behaviour it certified (a moved letter that is kept) is exactly how
    one printed `ff` reached the exported file as `ffff`.

    *A fixture that does not match GATHER tests the test* — the same shape
    CLAUDE.md already records for `Q.METER_GLYPH`. The premise is now pinned
    against the gather site by `TestOneLetterIsNeverContested` below, so the
    fixture cannot drift back.
    """

    def _log(self):
        log = Log()
        # TWO detections of ONE printed letter: the LOWER staff prints it, and
        # the UPPER staff's cell padding reaches down into the same ink. This
        # is what a real contest looks like on the record.
        g_upper = R.glyph(0, 0, 0, 0, 0)
        g_lower = R.glyph(0, 0, 1, 0, 0)
        _letter(log, g_upper, "p", 100.0, 110.0)
        _letter(log, g_lower, "p", 100.0, 110.0)
        _contest(log, g_upper, winner=LOWER, loser=UPPER)
        _contest(log, g_lower, winner=LOWER, loser=UPPER)
        log.freeze()
        adjudicate.run(log)
        assert log.verdict(Q.GLYPH_OWNER, g_upper).value == LOWER.to_key()
        assert log.verdict(Q.GLYPH_OWNER, g_lower).value == LOWER.to_key()
        return log

    def test_the_owning_staff_writes_the_letter_ONCE(self):
        """⚠️ ONCE. Both copies name the LOWER staff as owner — measured at 245
        of 248 cross-staff notehead pairs on Litolff Beethoven 5 p1-4 — so
        keeping both is what spelled `p` twice."""
        log = self._log()
        v = log.verdict(Q.DYNAMIC, R.cell(0, 0, 1, 0))
        self.assertEqual(v.value, ["p"])
        self.assertEqual(v.detail["letters"], 1)
        self.assertEqual(v.detail["letters_dropped_as_duplicate"], 1)

    def test_the_other_staff_LOSES_its_copy(self):
        log = self._log()
        v = log.verdict(Q.DYNAMIC, R.cell(0, 0, 0, 0))
        self.assertEqual(v.value, [])
        self.assertEqual(v.reason, "owned_elsewhere")
        self.assertEqual(v.detail["letters_moved_out"], 1)

    def test_an_UNCONTESTED_letter_stays_where_it_was_cut(self):
        """The positive control in the same class: without a contest nothing is
        dropped, so the refusal above cannot be passing by refusing everything.
        """
        log = Log()
        _letter(log, R.glyph(0, 0, 0, 0, 0), "p", 100.0, 110.0)
        log.freeze()
        adjudicate.run(log)
        v = log.verdict(Q.DYNAMIC, R.cell(0, 0, 0, 0))
        self.assertEqual(v.value, ["p"])
        self.assertEqual(v.detail["letters_dropped_as_duplicate"], 0)


class TestBandPositionRescuesAnUntwinnedLetter(unittest.TestCase):
    """ROADMAP 2.27c, registry `[C46 + L53]`. `Q.GLYPH_OWNER` only ever sees
    the CONTESTED population -- a letter that never got an independent twin
    in the neighbour's own cell reaches `adjudicate_dynamic` as `owner is
    None`, and falls back to `home` unchanged. `Q.DYNAMIC_BAND_POSITION` is
    the SEPARATE, promoted reading that can speak for exactly that 24%
    (measured empty interval -3.04..-0.52 spaces, `capture.py`'s own
    "UNREAD-POSITION Q.DYNAMIC_BAND_POSITION" note).

    ⚠️ THE FIX. Remove the `Q.DYNAMIC_BAND_POSITION` read from `adjudicate_
    dynamic` (or the `owned_by = above` line) and
    `test_a_decisively_ABOVE_reading_moves_an_uncontested_letter` goes RED --
    the letter stays on `LOWER`, exactly the 24% miss the band study
    measured.
    """

    def test_a_decisively_ABOVE_reading_moves_an_uncontested_letter(self):
        """A letter home is `LOWER` (gathered there because the padded cell
        reached up into `UPPER`'s own air), but never independently
        re-detected in `UPPER`'s own cell -- so `Q.GLYPH_OWNER` never saw a
        contest at all. Its band offset, measured against `LOWER`'s own
        bottom line, is decisively in the "staff immediately above"
        population."""
        log = Log()
        g = R.glyph(0, 0, 1, 0, 0)          # home = LOWER
        _letter(log, g, "f", 100.0, 110.0)
        _band(log, g, -4.0)                 # <= DYNAMIC_ABOVE_BAND_MAX_SPACES
        # ⚠️ `subjects_from=Q.DYNAMIC_LETTER`: UPPER's own cell needs a
        # `Q.DYNAMIC_LETTER` row of ITS OWN (an abstention counts, per
        # `gather_dynamic_letters`'s own "EVERY CELL GETS A ROW") or the
        # decision never runs there at all and a letter ownership moves onto
        # it is silently lost -- exactly the fault that docstring names.
        log.abstain(R.cell(0, 0, 0, 0), Q.DYNAMIC_LETTER,
                    reader=READERS.DETECTOR, frame="cell:0",
                    reason=ABSTAIN.NO_GLYPH_OF_THIS_KIND)
        log.freeze()
        adjudicate.run(log)
        self.assertIsNone(log.verdict(Q.GLYPH_OWNER, g))   # never contested

        moved = log.verdict(Q.DYNAMIC, R.cell(0, 0, 1, 0))   # LOWER's own bar
        self.assertEqual(moved.value, [])
        self.assertEqual(moved.detail["letters_moved_out"], 1)

        rescued = log.verdict(Q.DYNAMIC, R.cell(0, 0, 0, 0))  # UPPER's bar
        self.assertEqual(rescued.value, ["f"])

    def test_POSITIVE_CONTROL_an_OWN_BAND_reading_stays_put(self):
        """The mirror -- a reading decisively in home's OWN band never
        moves anything, so the fix above is not just abstaining its way to
        a pass."""
        log = Log()
        g = R.glyph(0, 0, 1, 0, 0)
        _letter(log, g, "f", 100.0, 110.0)
        _band(log, g, 0.5)                  # own band, per gather.py's own
        log.abstain(R.cell(0, 0, 0, 0), Q.DYNAMIC_LETTER,  # +0.0..+5.6 range
                    reader=READERS.DETECTOR, frame="cell:0",
                    reason=ABSTAIN.NO_GLYPH_OF_THIS_KIND)
        log.freeze()
        adjudicate.run(log)

        home = log.verdict(Q.DYNAMIC, R.cell(0, 0, 1, 0))
        self.assertEqual(home.value, ["f"])
        above = log.verdict(Q.DYNAMIC, R.cell(0, 0, 0, 0))
        self.assertEqual(above.value, [])

    def test_NEGATIVE_CONTROL_the_measured_empty_gap_is_left_UNCHANGED(self):
        """A reading strictly between the two measured populations decides
        nothing new -- CLAUDE.md rule 8, a fallback never turns "cannot
        tell" into an answer. It stays exactly where `home` already put it,
        the same "unchanged" outcome as a letter with no band row at all."""
        log = Log()
        g = R.glyph(0, 0, 1, 0, 0)
        _letter(log, g, "f", 100.0, 110.0)
        _band(log, g, -1.5)                 # inside (-3.04, -0.52)
        log.abstain(R.cell(0, 0, 0, 0), Q.DYNAMIC_LETTER,
                    reader=READERS.DETECTOR, frame="cell:0",
                    reason=ABSTAIN.NO_GLYPH_OF_THIS_KIND)
        log.freeze()
        adjudicate.run(log)

        home = log.verdict(Q.DYNAMIC, R.cell(0, 0, 1, 0))
        self.assertEqual(home.value, ["f"])
        above = log.verdict(Q.DYNAMIC, R.cell(0, 0, 0, 0))
        self.assertEqual(above.value, [])

    def test_a_DECIDED_contest_is_never_overridden_by_the_band(self):
        """A band row that would otherwise say "own band" cannot pull a
        letter back from a staff `Q.GLYPH_OWNER` has already, genuinely,
        decided it belongs to -- the ownership query runs FIRST, and this
        code path is only reached when it left `owned_by == home`."""
        log = Log()
        g_upper = R.glyph(0, 0, 0, 0, 0)
        g_lower = R.glyph(0, 0, 1, 0, 0)
        _letter(log, g_upper, "p", 100.0, 110.0)
        _letter(log, g_lower, "p", 100.0, 110.0)
        _contest(log, g_upper, winner=LOWER, loser=UPPER)
        _contest(log, g_lower, winner=LOWER, loser=UPPER)
        # A band row that, read alone, says "clearly LOWER's own" -- and it
        # must not matter, because ownership already decided LOWER either
        # way here.
        _band(log, g_lower, 0.5)
        log.freeze()
        adjudicate.run(log)
        self.assertEqual(log.verdict(Q.GLYPH_OWNER, g_lower).value,
                         LOWER.to_key())
        v = log.verdict(Q.DYNAMIC, R.cell(0, 0, 1, 0))
        self.assertEqual(v.value, ["p"])
        self.assertEqual(v.detail["letters"], 1)


class TestSilenceIsNotAnAnswer(unittest.TestCase):
    """⚠️ THREE states, not two -- the module's reason to exist, at the one
    place in this decision where it changes the ruling."""

    def test_a_reader_that_LOOKED_and_found_nothing_decides_empty(self):
        log = Log()
        log.abstain(R.cell(0, 0, 0, 0), Q.DYNAMIC_LETTER,
                    reader=READERS.DETECTOR, frame="cell:0",
                    reason=ABSTAIN.NO_INK)
        log.freeze()
        adjudicate.run(log)
        v = log.verdict(Q.DYNAMIC, R.cell(0, 0, 0, 0))
        self.assertEqual(v.value, [])
        self.assertEqual(v.reason, "no_letters")

    def test_a_reader_that_never_RAN_abstains(self):
        log = Log()
        log.abstain(R.cell(0, 0, 0, 0), Q.DYNAMIC_LETTER,
                    reader=READERS.DETECTOR, frame="cell:0",
                    reason=ABSTAIN.READER_UNAVAILABLE)
        log.freeze()
        adjudicate.run(log)
        v = log.verdict(Q.DYNAMIC, R.cell(0, 0, 0, 0))
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertNotEqual(v.reason, "no_letters")


# ─────────────────────────────────────────────────────────────────────────────
# The gatherers
# ─────────────────────────────────────────────────────────────────────────────


class _Det:
    def __init__(self, name, x, y, w=10.0, h=10.0, conf=0.8):
        self.smufl_name = name
        self.x_canonical, self.y_canonical = x, y
        self.width_canonical, self.height_canonical = w, h
        self.confidence, self.category = conf, "dynamic"
        self.x_center, self.y_center = x + w / 2, y + h / 2


def _staff(idx, line_ys, sys_idx=0):
    return SimpleNamespace(staff_index=idx, system_index=sys_idx,
                           line_ys=list(line_ys), top_y=min(line_ys),
                           x_start=0, x_end=1000, line_thickness_px=None,
                           line_wander_px=None)


def _cell(staff_index, measure_index, bbox, upscale):
    return SimpleNamespace(staff_index=staff_index, page_index=0,
                           measure_index=measure_index, bbox_page_px=bbox,
                           upscale_factor=upscale, image_no_staff=None)


def _pws(staves, binary=None):
    return SimpleNamespace(page=SimpleNamespace(page_index=0, binary=binary),
                           staves=staves)


class TestTheLetterIsMeasuredAgainstTheSTAFFNotTheCell(unittest.TestCase):
    """⚠️ THE FRAME REQUIREMENT, made falsifiable.

    `measure_extractor` pads a cell by 4 staff spaces, or 6 where the
    neighbouring staff is more than 6 spaces away -- so the SAME ink sits at a
    different height in the cell frame depending on how crowded its neighbours
    are. A band number taken in that frame moves when the page's crowding
    changes and the ink does not. Two cells here hold identical PAGE ink with
    different padding; the band offset must not notice.
    """

    def _offset(self, pad_px):
        st = _staff(0, [50, 60, 70, 80, 90])
        # The ink sits at page y = 100..110 whatever the padding: a taller crop
        # starts higher and the detection's canonical y grows to match.
        cell = _cell(0, 0, [0.0, 50.0 - pad_px, 500.0, 200.0], 1.0)
        det = _Det("dynamicF", 100.0, 100.0 - (50.0 - pad_px))
        log = Log()
        local = {0: (0, 0)}
        G.gather_dynamic_letters(log, _pws([st]), [cell], local,
                                 {R.cell(0, 0, 0, 0).to_key(): [det]})
        rows = log.rows(Q.DYNAMIC_LETTER, R.cell(0, 0, 0, 0),
                        scope=Scope.SELF_AND_DESCENDANTS)
        self.assertEqual(len(rows), 1)
        return rows[0]

    def test_the_band_offset_is_identical_under_two_paddings(self):
        a, b = self._offset(40.0), self._offset(60.0)
        self.assertAlmostEqual(a.detail["band_offset_spaces"],
                               b.detail["band_offset_spaces"], places=6)
        self.assertAlmostEqual(a.detail["y_center_page"],
                               b.detail["y_center_page"], places=6)

    def test_the_offset_is_below_the_staffs_own_BOTTOM_line(self):
        row = self._offset(40.0)
        # bottom line is page y=90, spacing 10, ink centre y=105 -> +1.5
        self.assertAlmostEqual(row.detail["band_offset_spaces"], 1.5, places=6)
        self.assertEqual(row.detail["staff_bottom_line_page"], 90.0)
        self.assertTrue(row.detail["in_hairpin_band"],
                        "1.5 spaces below the bottom line is inside "
                        "hairpin_detection's own 0.3-6.0 band")
        self.assertEqual(row.frame, G.FRAME_PAGE)


class TestTheWedgeRungSaysWhyItSaidNothing(unittest.TestCase):
    """⚠️ A silent null is the one result this project treats as worse than a
    loud failure -- `read_hairpins_for_page` asserts its own ink polarity for
    exactly this reason. A rung that could not run must not look like a page
    with no hairpins on it."""

    def test_no_raster_is_a_LOUD_abstention_per_staff(self):
        st = _staff(0, [50, 60, 70, 80, 90])
        log = Log()
        G.gather_wedge_boxes(log, _pws([st], binary=None), [], {0: (0, 0)}, {})
        refusals = log.refusals(Q.WEDGE_BOX, R.staff(0, 0, 0))
        self.assertTrue(refusals)
        self.assertEqual(refusals[0].reason, ABSTAIN.READER_UNAVAILABLE)
        self.assertEqual(refusals[0].reader, READERS.CV_HAIRPINS)

    def test_a_page_with_no_hairpin_ink_abstains_NO_INK_not_silence(self):
        """The `0 spurious` half of the ledger's reading. A consumer that
        cannot tell this from 'the rung never ran' cannot tell silence from
        blindness."""
        st = _staff(0, [50, 60, 70, 80, 90])
        blank = np.full((200, 500), 255, dtype=np.uint8)   # 0 = ink: all paper
        log = Log()
        G.gather_wedge_boxes(log, _pws([st], binary=blank), [], {0: (0, 0)}, {})
        refusals = log.refusals(Q.WEDGE_BOX, R.staff(0, 0, 0))
        self.assertEqual([a.reason for a in refusals], [ABSTAIN.NO_INK])

    def test_the_detector_and_the_CV_rung_are_DIFFERENT_readers(self):
        """⚠️ Two rows from ONE reader on one crop are ONE signal. Filing
        `hairpin_detection` under CV_LINES would collapse two genuinely
        independent readings of the same band."""
        st = _staff(0, [50, 60, 70, 80, 90])
        cell = _cell(0, 0, [0.0, 10.0, 500.0, 200.0], 1.0)
        det = _Det("dynamicCrescendoHairpin", 100.0, 100.0)
        log = Log()
        G.gather_wedge_boxes(log, _pws([st], binary=None), [cell], {0: (0, 0)},
                             {R.cell(0, 0, 0, 0).to_key(): [det]})
        rows = log.rows(Q.WEDGE_BOX, R.cell(0, 0, 0, 0),
                        scope=Scope.SELF_AND_DESCENDANTS)
        self.assertEqual([r.reader for r in rows], [READERS.DETECTOR])
        self.assertEqual(rows[0].value, "crescendo")
        self.assertNotEqual(READERS.CV_HAIRPINS, READERS.CV_LINES)


if __name__ == "__main__":
    unittest.main()
