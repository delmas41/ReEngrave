"""The template reader, aimed at a mid-staff BAR HEAD — a printed meter CHANGE.

`gather_meter` hands `locate_time_signature` the HEADER window and nothing
else, so a time signature printed anywhere later on the staff is read by the
DETECTOR alone, which is the weak reader on exactly the ink it is worst at.
`gather_meter_at_bars` asks the good reader at every candidate bar, of EVERY
staff of the system — including the staves that detected nothing, which is the
only part of this the detector cannot already do.

⚠️⚠️ THE HAZARD THESE TESTS EXIST FOR IS *an empty window answered anyway*.
CLAUDE.md records the key-signature family paying for it: *"the template found
a clean window and answered a confident `fifths: 0` — a key signature
fabricated out of a crop containing none."* The measurement lives in
`benchmarks/omr-meter-template-changes-2026-09/`; what lives here is the
mechanism that keeps a lone reading from ever becoming a change.
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

import cv2
import numpy as np

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import rhythm as rhythm_mod
from tools.omr.staged.record import Log, Outcome, Q, READERS
from tools.omr.time_signature_locator import (DEFAULT_LOCATOR_CONFIG,
                                              _meter_templates,
                                              locate_time_signature)
from tools.omr.types import MeasureCell

SPACING = 25.0
TOP = 40.0


def _blank_cell(staff_index: int, measure_index: int, width: int = 400):
    """A synthetic measure cell with a real five-line geometry and no ink.

    ⚠️ REAL GEOMETRY, because `_bar_head_window` measures the slice width off
    `staff_metrics`, and a fixture that fakes the spacing would test arithmetic
    this module does not do.
    """
    height = int(TOP * 2 + 4 * SPACING)
    image = np.full((height, width), 255, np.uint8)
    lines = [int(round(TOP + i * SPACING)) for i in range(5)]
    for y in lines:
        image[y, :] = 0
    return MeasureCell(
        page_index=0, system_index=0, staff_index=staff_index,
        measure_index=measure_index, image=image,
        image_no_staff=np.full((height, width), 255, np.uint8),
        bbox_page_px=(0, 0, width, height),
        staff_line_ys_canonical=lines, upscale_factor=1.0)


def _stamp(cell, raw: str = "3/4"):
    """Put a real Bravura meter at this cell's bar head.

    ⚠️ THE ONLY WAY A UNIT TEST CAN MAKE THIS READER ANSWER. It is an NCC
    against Bravura templates, so blank ink or a hand-drawn rectangle scores
    nothing and every assertion below would pass for the wrong reason.
    """
    glyph = None
    for (_n, _d, r), tpl in _meter_templates(
            DEFAULT_LOCATOR_CONFIG.template_em_px,
            tuple(DEFAULT_LOCATOR_CONFIG.meters)):
        if r == raw:
            glyph = tpl
            break
    assert glyph is not None, raw
    height = int(round(4 * SPACING))
    width = max(2, int(round(glyph.shape[1] * height / glyph.shape[0])))
    resized = cv2.resize(glyph, (width, height), interpolation=cv2.INTER_AREA)
    ink = resized > 127
    y0 = int(round(TOP - 0.5 * SPACING))
    x0 = int(round(0.4 * SPACING))
    for canvas in (cell.image, cell.image_no_staff):
        canvas[y0:y0 + height, x0:x0 + width][ink] = 0
    return cell


class _Det:
    """The minimum `gather._meter_cells` and the candidate scan read."""

    def __init__(self, smufl_name, x=10.0, y=10.0, conf=0.9):
        self.smufl_name = smufl_name
        self.x_canonical = x
        self.y_canonical = y
        self.y_center = y
        self.confidence = conf


def _detections(page, staff_keys, marks):
    """`{cell_key: [detections]}`; `marks` is `{(staff, cell): [classes]}`."""
    out = {}
    for staff_index, (sysi, sti) in staff_keys.items():
        for (st, cell), classes in marks.items():
            if st != staff_index:
                continue
            key = R.cell(page, sysi, sti, cell).to_key()
            out.setdefault(key, []).extend(_Det(c) for c in classes)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# The window
# ─────────────────────────────────────────────────────────────────────────────


class TestTheBarHeadWindow(unittest.TestCase):

    def test_it_slices_to_the_declared_number_of_staff_spaces(self):
        cell = _blank_cell(0, 3, width=400)
        window = G._bar_head_window(cell, 4.0)
        self.assertEqual(window.image.shape[1], int(round(4.0 * SPACING)))
        self.assertEqual(window.image_no_staff.shape[1],
                         int(round(4.0 * SPACING)))

    def test_a_narrow_cell_is_not_widened(self):
        """A degenerate final cell is narrower than the window. It is taken
        whole rather than padded — padding would hand the reader invented
        paper, which is the empty-window hazard with extra steps."""
        cell = _blank_cell(0, 3, width=40)
        self.assertEqual(G._bar_head_window(cell, 4.0).image.shape[1], 40)

    def test_no_five_line_geometry_ABSTAINS_rather_than_guessing_a_width(self):
        cell = _blank_cell(0, 3)
        cell.staff_line_ys_canonical = []
        self.assertIsNone(G._bar_head_window(cell, 4.0))

    def test_the_PROBE_takes_the_same_slice_as_the_GATHERER(self):
        """⚠️ The benchmark restates the slice rather than importing it, so it
        can run against a tree where the gatherer does not exist. That is only
        safe while the two agree, and nothing but this asserts they do."""
        import importlib.util
        import pathlib
        probe = (pathlib.Path(__file__).resolve().parents[3]
                 / "benchmarks" / "omr-meter-template-changes-2026-09"
                 / "probe" / "empty_window.py")
        if not probe.is_file():                       # pragma: no cover
            self.skipTest("probe not present")
        spec = importlib.util.spec_from_file_location("_ew", probe)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for spaces in (3.0, 4.0, 6.0):
            mine = G._bar_head_window(_blank_cell(0, 3), spaces)
            theirs = mod.head_slice(_blank_cell(0, 3), spaces)
            self.assertEqual(mine.image.shape, theirs.image.shape,
                             f"slices disagree at {spaces} spaces")


# ─────────────────────────────────────────────────────────────────────────────
# Which columns are asked at all
# ─────────────────────────────────────────────────────────────────────────────


class TestTheCandidateColumns(unittest.TestCase):

    LOCAL = {0: (0, 0), 1: (0, 1), 2: (0, 2)}

    def test_cell_zero_is_never_a_candidate(self):
        """Cell 0 states the staff's OPENING — the header reader's business,
        and `_meter_changes` excludes it for the same reason."""
        dets = _detections(0, self.LOCAL, {(0, 0): ["timeSig3"],
                                           (1, 0): ["timeSig4"]})
        self.assertEqual(G._meter_candidate_columns(dets, 0, self.LOCAL), {})

    def test_it_counts_the_STAVES_that_saw_meter_shaped_ink(self):
        dets = _detections(0, self.LOCAL, {(0, 2): ["timeSig3", "timeSig4"],
                                           (1, 2): ["timeSigCommon"],
                                           (2, 5): ["timeSig2"]})
        self.assertEqual(G._meter_candidate_columns(dets, 0, self.LOCAL),
                         {0: {2: 2, 5: 1}})

    def test_ink_that_is_not_meter_shaped_opens_nothing(self):
        dets = _detections(0, self.LOCAL, {(0, 2): ["noteheadBlack",
                                                    "restWhole"]})
        self.assertEqual(G._meter_candidate_columns(dets, 0, self.LOCAL), {})


# ─────────────────────────────────────────────────────────────────────────────
# The gatherer, and the flag
# ─────────────────────────────────────────────────────────────────────────────


class TestTheGatherer(unittest.TestCase):

    LOCAL = {0: (0, 0), 1: (0, 1), 2: (0, 2)}

    def _cells(self, stamped_staves=(0, 1, 2), cell=2):
        cells = []
        for staff_index in self.LOCAL:
            for measure_index in (0, 1, 2, 3):
                c = _blank_cell(staff_index, measure_index)
                if measure_index == cell and staff_index in stamped_staves:
                    _stamp(c, "3/4")
                cells.append(c)
        return cells

    def _run(self, enabled, stamped_staves=(0, 1, 2)):
        log = Log()
        dets = _detections(0, self.LOCAL, {(0, 2): ["timeSig3", "timeSig4"]})
        env = {G.METER_TEMPLATE_AT_BAR_ENV: "1"} if enabled else {}
        with mock.patch.dict(os.environ, env, clear=False):
            if not enabled:
                os.environ.pop(G.METER_TEMPLATE_AT_BAR_ENV, None)
            G.gather_meter_at_bars(log, self._cells(stamped_staves),
                                   self.LOCAL, dets)
        return log

    @staticmethod
    def _rows(log):
        """Every row of this quantity on the log — observations AND
        abstentions, because the flag-off claim is about BOTH."""
        out = []
        for staff_index in (0, 1, 2):
            sub = R.staff(0, 0, staff_index)
            out.extend(log.rows(Q.METER_TEMPLATE_AT_BAR, sub))
            out.extend(log.refusals(Q.METER_TEMPLATE_AT_BAR, sub))
        return out

    def test_FLAG_OFF_WRITES_NOTHING_AT_ALL(self):
        """⚠️ THE BYTE-IDENTITY CONTROL. With the flag off the record must be
        exactly what it would have been without this change — not an
        abstention per staff per column, which would be a few hundred rows a
        page saying only *"a flag is off"*."""
        log = self._run(enabled=False)
        self.assertEqual(self._rows(log), [])

    def test_FLAG_ON_WRITES_ROWS(self):
        """⚠️⚠️ THE POSITIVE CONTROL FOR THE TEST ABOVE, and without it that
        zero is worthless. CLAUDE.md records a byte-identity control that
        passed because the function under test was never called on any
        fixture; this asserts the fixture DOES reach the reader."""
        log = self._run(enabled=True)
        self.assertGreater(len(self._rows(log)), 0)

    def test_the_reading_is_filed_on_the_STAFF_with_the_BAR_in_detail(self):
        """⚠️ THE `Q.METER_GLYPH` LESSON, applied before it could be repeated.
        That quantity is filed on the STAFF with the bar in `detail["cell"]`,
        a test fixture filed it on a GLYPH, and `subject.at(Kind.CELL)`
        returns None for a staff — so a shipped rule read no boxes on any real
        page while five green tests said otherwise. *A fixture that does not
        match GATHER tests the test.*"""
        log = self._run(enabled=True)
        rows = [e for e in self._rows(log)
                if getattr(e, "value", None) is not None]
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(row.subject.kind, R.Kind.STAFF)
            self.assertEqual((row.detail or {}).get("cell"), 2)

    def test_the_reader_ANSWERS_on_a_stamped_bar_head(self):
        log = self._run(enabled=True)
        values = {e.value for e in self._rows(log)
                  if getattr(e, "value", None) is not None}
        self.assertIn((3, 4), values)

    def test_a_staff_that_DETECTED_NOTHING_is_still_asked(self):
        """⚠️ THE WHOLE POINT OF A COLUMN. One staff's detection names the bar;
        every staff of the system is then read there. Staff 1 and 2 carry no
        meter detection at all and must still produce a row."""
        log = self._run(enabled=True)
        staves = {e.subject.staff for e in self._rows(log)}
        self.assertEqual(staves, {0, 1, 2})

    def test_a_bar_head_with_NO_meter_abstains_rather_than_answering(self):
        """The empty-window case, in miniature: only staff 0's bar is stamped,
        and the other two must come back as abstentions."""
        log = self._run(enabled=True, stamped_staves=(0,))
        answered = {e.subject.staff for e in self._rows(log)
                    if getattr(e, "value", None) is not None}
        self.assertEqual(answered, {0})

    def test_the_flag_is_an_ALLOW_LIST_because_the_default_is_OFF(self):
        """⚠️ CLAUDE.md, *A flag's OFF test must follow its DEFAULT*: written
        as a deny-list, a typo would switch a document ON to a mechanism whose
        cost has never been priced."""
        for value, expect in (("1", True), ("true", True), ("on", True),
                              ("", False), ("yess", False), ("ON!", False),
                              ("0", False)):
            with mock.patch.dict(os.environ,
                                 {G.METER_TEMPLATE_AT_BAR_ENV: value}):
                self.assertIs(G._meter_template_at_bar_enabled(), expect,
                              f"{value!r}")


# ─────────────────────────────────────────────────────────────────────────────
# The consumer
# ─────────────────────────────────────────────────────────────────────────────


class TestTheConsensus(unittest.TestCase):
    """⚠️⚠️ WHERE THE SAFETY IS. Measured over 1,612 mid-staff bar-head windows
    on ten real scanned pages of two publishers, none of which prints a meter
    change: admitted on ONE staff the reader produces 16 spurious columns, on
    two it produces 2, on three it produces ZERO."""

    def test_a_LONE_reading_is_refused(self):
        readings = {}
        admitted = rhythm_mod._admit_template_consensus(
            readings, {(3, 4, "3/4"): {0}}, already_read=set())
        self.assertEqual(readings, {})
        self.assertEqual(admitted, {})

    def test_TWO_agreeing_staves_are_refused_at_the_shipped_quorum(self):
        self.assertGreaterEqual(rhythm_mod.METER_TEMPLATE_AT_BAR_MIN_STAVES, 3)
        readings = {}
        rhythm_mod._admit_template_consensus(
            readings, {(3, 4, "3/4"): {0, 1}}, already_read=set())
        self.assertEqual(readings, {})

    def test_THREE_agreeing_staves_are_admitted(self):
        readings = {}
        admitted = rhythm_mod._admit_template_consensus(
            readings, {(3, 4, "3/4"): {0, 1, 2}}, already_read=set())
        self.assertEqual(readings, {(3, 4, "3/4"): [0, 1, 2]})
        self.assertEqual(admitted, {(3, 4, "3/4"): 3})

    def test_staves_that_read_their_own_DIGITS_are_left_alone(self):
        """⚠️ GAPS ONLY, inherited from `adjudicate_key_signature` rather than
        re-decided: the second reader is the one that can OVER-produce, so it
        speaks where the first was silent."""
        readings = {(3, 4, "3/4"): [0]}
        rhythm_mod._admit_template_consensus(
            readings, {(3, 4, "3/4"): {0, 1, 2}}, already_read={0})
        self.assertEqual(readings, {(3, 4, "3/4"): [0, 1, 2]})

    def test_a_meter_the_glyphs_already_named_gains_the_template_staves(self):
        readings = {(3, 4, "3/4"): [5]}
        rhythm_mod._admit_template_consensus(
            readings, {(3, 4, "3/4"): {0, 1, 2}}, already_read={5})
        self.assertEqual(sorted(readings[(3, 4, "3/4")]), [0, 1, 2, 5])

    def test_the_PRINTED_FORM_is_part_of_the_key(self):
        """`C` and `4/4` are one bar length and two engravings; three staves
        reading `C` and three reading `4/4` are two readings, not six."""
        readings = {}
        rhythm_mod._admit_template_consensus(
            readings, {(4, 4, "C"): {0, 1}, (4, 4, "4/4"): {2, 3}},
            already_read=set())
        self.assertEqual(readings, {})


class TestTheRowsAreRead(unittest.TestCase):

    def _log_with(self, rows):
        log = Log()
        for staff, cell, value, raw in rows:
            log.observe(R.staff(0, 0, staff), Q.METER_TEMPLATE_AT_BAR, value,
                        reader=READERS.TEMPLATE, frame=G.frame_bar_head(cell),
                        cell=cell, raw=raw, score=0.6)
        log.freeze()
        from tools.omr.staged.adjudicate import Evidence
        adjudicate._ensure_decisions()
        return Evidence(log, R.system(0, 0), adjudicate.REGISTRY[Q.METER])

    def test_rows_group_by_bar_and_by_printed_form(self):
        ev = self._log_with([(0, 4, (3, 4), "3/4"), (1, 4, (3, 4), "3/4"),
                             (2, 7, (4, 4), "C")])
        out = rhythm_mod._template_readings_at_bars(ev)
        self.assertEqual(out, {4: {(3, 4, "3/4"): {0, 1}},
                               7: {(4, 4, "C"): {2}}})

    def test_cell_zero_is_dropped(self):
        ev = self._log_with([(0, 0, (3, 4), "3/4")])
        self.assertEqual(rhythm_mod._template_readings_at_bars(ev), {})

    def test_no_rows_is_an_empty_dict_which_is_the_FLAG_OFF_case(self):
        ev = self._log_with([])
        self.assertEqual(rhythm_mod._template_readings_at_bars(ev), {})


# ─────────────────────────────────────────────────────────────────────────────
# End to end, through `adjudicate_meter`
# ─────────────────────────────────────────────────────────────────────────────


class TestAConsensusReachesTheSegments(unittest.TestCase):
    """The same fixture shape `TestAMeterChangeIsReadFromTheInk` uses, with
    the change carried by the TEMPLATE reader instead of by digits."""

    N_STAVES = 4

    def _log(self, template_rows=(), glyphs=(), per_cell=(3.0, 4.0, 4.0, 4.0)):
        log = Log()
        sysj = R.system(0, 0)
        log.record(adjudicate.Verdict(
            id=log._next_id("vrd"), subject=sysj,
            quantity=Q.SYSTEM_STAFF_COUNT, outcome=Outcome.DECIDED,
            value=self.N_STAVES, decider="t", reason="counted"))
        for st in range(self.N_STAVES):
            log.observe(R.staff(0, 0, st), Q.METER_TEMPLATE, (3, 4),
                        reader=READERS.TEMPLATE, frame="header_window",
                        score=0.7, raw="3/4")
            for cell, klass in glyphs:
                y = 10.0 if klass.endswith(("2", "3", "6", "9")) else 30.0
                log.observe(R.staff(0, 0, st), Q.METER_GLYPH, klass,
                            reader=READERS.DETECTOR, frame="cell:%d" % cell,
                            score=0.9, cell=cell, x=10.0, y_center=y,
                            letter=klass.startswith("timeSigC"))
            for cell, value, raw in template_rows:
                if st not in value[2]:
                    continue
                log.observe(R.staff(0, 0, st), Q.METER_TEMPLATE_AT_BAR,
                            (value[0], value[1]), reader=READERS.TEMPLATE,
                            frame=G.frame_bar_head(cell), cell=cell, raw=raw,
                            score=0.6)
            for c, beats in enumerate(per_cell):
                cell_sub = R.cell(0, 0, st, c)
                g = R.glyph(0, 0, st, c, 0)
                log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlack",
                            reader=READERS.DETECTOR, frame="cell:%d" % c,
                            score=0.9)
                log.observe(g, Q.GLYPH_BOX,
                            ("noteheadBlack", 100, 0, 20, 16),
                            reader=READERS.DETECTOR, frame="cell:%d" % c,
                            score=0.9)
                log.record(adjudicate.Verdict(
                    id=log._next_id("vrd"), subject=g, quantity=Q.DURATION,
                    outcome=Outcome.DECIDED,
                    value={"beats": beats, "written": beats,
                           "duration_type": "quarter", "dots": 0},
                    decider="t", reason="head_and_marks"))
                log.record(adjudicate.Verdict(
                    id=log._next_id("vrd"), subject=cell_sub,
                    quantity=Q.EVENT, outcome=Outcome.DECIDED,
                    value={"events": [{"glyphs": [0], "x": 100.0,
                                       "kind": "chord"}]},
                    decider="t", reason="x_clustered"))
        return log, sysj

    def _segments(self, log, sysj):
        log.freeze()
        adjudicate._ensure_decisions()
        adjudicate.adjudicate_one(log, adjudicate.REGISTRY[Q.METER], sysj)
        v = log.verdict(Q.METER, sysj)
        return (v.value or {}).get("segments") or [], v

    def test_a_bar_with_NO_glyph_anywhere_proposes_nothing(self):
        """⚠️ THE STRUCTURAL BOUND: the gatherer only ever looks where some
        staff saw meter-shaped ink, so this pass can add STAVES to a bar and
        never a bar to the page. Asserted rather than assumed."""
        segs, _ = self._segments(*self._log(
            template_rows=[(1, (4, 4, {0, 1, 2, 3}), "4/4")]))
        self.assertEqual([s["from_cell"] for s in segs], [0])

    def test_a_CONSENSUS_at_a_candidate_bar_carries_the_change(self):
        log, sysj = self._log(
            glyphs=((1, "timeSig4"),),          # one loose digit opens the bar
            template_rows=[(1, (4, 4, {0, 1, 2, 3}), "4/4")])
        segs, _ = self._segments(log, sysj)
        self.assertEqual([(s["from_cell"], s["raw"]) for s in segs],
                         [(0, "3/4"), (1, "4/4")])
        self.assertEqual(segs[1]["staves_from_bar_head_template"], 4)

    def test_TWO_agreeing_template_staves_do_NOT_carry_it(self):
        """The same bar, the same loose digit, two template readings instead
        of four — and a loose digit alone is below `METER_CHANGE_FLOOR`."""
        log, sysj = self._log(
            glyphs=((1, "timeSig4"),),
            template_rows=[(1, (4, 4, {0, 1}), "4/4")])
        segs, _ = self._segments(log, sysj)
        self.assertEqual([s["from_cell"] for s in segs], [0])

    def test_the_OPENING_vote_does_not_read_the_bar_head_rows(self):
        """⚠️⚠️ WHY THIS IS A SEPARATE QUANTITY AT ALL. `adjudicate_meter`
        takes every `Q.METER_TEMPLATE` row as a vote on the system's OPENING;
        filing a mid-staff reading there would make a change at bar 1 argue
        about what bar 0 prints. The precedent is `Q.KEYSIG_TEMPLATE_FIT`.
        Run this RED by changing the gatherer to emit `Q.METER_TEMPLATE`."""
        log, sysj = self._log(
            glyphs=((1, "timeSig4"),),
            template_rows=[(1, (4, 4, {0, 1, 2, 3}), "4/4")])
        _segs, v = self._segments(log, sysj)
        self.assertEqual((v.value["numerator"], v.value["denominator"]),
                         (3, 4))
        self.assertEqual(v.value["raw"], "3/4")

    def test_the_record_NAMES_the_template_staves_rather_than_netting_them(self):
        log, sysj = self._log(
            glyphs=((1, "timeSig4"),),
            template_rows=[(1, (4, 4, {0, 1, 2, 3}), "4/4")])
        segs, _ = self._segments(log, sysj)
        self.assertIn("staves_from_bar_head_template", segs[1])

    def test_a_change_the_DIGITS_carry_alone_records_no_template_key(self):
        """Absent, not zero — so a flag-off record carries no new key at all
        and a reader cannot mistake *"nothing was admitted"* for
        *"the mechanism ran and found none"*."""
        log, sysj = self._log(glyphs=((1, "timeSig4"), (1, "timeSig4")))
        segs, _ = self._segments(log, sysj)
        if len(segs) > 1:
            self.assertNotIn("staves_from_bar_head_template", segs[1])


class TestTheReaderIsSaneOnBlankPaper(unittest.TestCase):
    """A direct control on `locate_time_signature` itself, with its own
    positive control inside the test — otherwise a refusal test passes for
    free the moment the reader dies."""

    def test_a_blank_bar_head_is_refused_and_a_stamped_one_is_not(self):
        blank = G._bar_head_window(_blank_cell(0, 2), 4.0)
        self.assertIsNone(locate_time_signature(blank))
        stamped = G._bar_head_window(_stamp(_blank_cell(0, 2), "3/4"), 4.0)
        found = locate_time_signature(stamped)
        self.assertIsNotNone(found)
        self.assertEqual(found.raw, "3/4")


if __name__ == "__main__":       # pragma: no cover
    unittest.main()
