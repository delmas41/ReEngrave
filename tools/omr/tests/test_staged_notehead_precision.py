"""`notehead_is_not_a_notehead` — ROADMAP 2.4a: notehead PRECISION, staged.

⚠️ THREE RULES, EACH WITH ITS OWN POSITIVE CONTROL, because a battery of
refusal tests passes by refusing everything. See
`tools/omr/staged/adjudicators/notehead_precision.py` for the measurements
each rule ports (`benchmarks/omr-notehead-width-2026-09/FINDINGS.md`,
`transcribe._drop_clipped_notehead_fragments`,
`transcribe._drop_unladdered_noteheads`).

Run RED first, against the unmodified tree (before
`notehead_precision.py`/the `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` registration
existed): every test below either fails with `AttributeError`
(`Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` absent) or `KeyError` (nothing in `ORDER`),
confirming the fixtures exercise code that did not previously exist.
"""

from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import export as SX
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS

CELL = R.cell(0, 0, 0, 0)
SPACING = 100.0                       # one staff space, canonical px
#: A generous cell crop: staff band roughly in the middle, plenty of padding
#: above and below, in PAGE pixels.
CELL_BOX_PAGE = [500.0, 1000.0, 700.0, 1300.0]   # 200 x 300 page px


def _cell_geometry(log, *, spacing=SPACING, cell_box=CELL_BOX_PAGE):
    if spacing is not None:
        log.observe(CELL, Q.CELL_STAFF_SPACE, spacing,
                    reader=READERS.GEOMETRY, frame="cell:0")
    if cell_box is not None:
        log.observe(CELL, Q.CELL_BOX, list(cell_box),
                    reader=READERS.GEOMETRY, frame="cell:0")


def _notehead(log, gi, *, cls="noteheadHalfInSpace", x_c=200.0, y_c=200.0,
             w_c=140.0, h_c=100.0, conf=0.8, pos_float=4.0,
             page_box=None):
    """One detection the detector called a notehead.

    Canonical geometry is what the height/width rules read; `page_box`
    (`[px0, py0, px1, py1]`) is what the edge test reads, and is entirely
    separate — a test that wants to isolate one rule from the other sets one
    and not the other, matching how `test_staged_whole_rest_ink.py` keeps its
    canonical and page boxes independently wrong on purpose.
    """
    g = R.glyph(0, 0, 0, 0, gi)
    kw = {}
    if page_box is not None:
        kw["bbox_page_px"] = list(page_box)
    log.observe(g, Q.GLYPH_BOX, (cls, x_c, y_c, w_c, h_c),
                reader=READERS.DETECTOR, frame="cell:0", score=conf,
                category="notehead", **kw)
    log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR,
               frame="cell:0", score=conf)
    log.observe(g, Q.GLYPH_CONF, conf, reader=READERS.DETECTOR,
               frame="cell:0", score=conf)
    log.observe(g, Q.NOTEHEAD_STAFF_POSITION, pos_float,
               reader=READERS.GEOMETRY, frame="cell:0")
    return g


def _ledger(log, gi, *, x_c, y_c, w_c=140.0, h_c=20.0):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.GLYPH_BOX, ("ledgerLine", x_c, y_c, w_c, h_c),
                reader=READERS.DETECTOR, frame="cell:0", score=0.7,
                category="ledger")
    return g


def _run(log):
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,))
    return log


def _verdict(log, g):
    return log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)


class TestTheDecisionIsDeclaredTheWayItBehaves(unittest.TestCase):

    def test_it_is_not_a_stub(self):
        self.assertFalse(
            adjudicate.REGISTRY[Q.NOTEHEAD_IS_NOT_A_NOTEHEAD].stub)

    def test_its_domain_is_the_noteheads(self):
        """⚠️ ASSERTED OFF THE REGISTRY. Widening this decision's domain past
        ink the detector already called a notehead would let it refuse a
        clef or a barline outright, which must go red rather than pass
        quietly — the same guard `glyph_owner`'s domain carries."""
        self.assertEqual(
            adjudicate.REGISTRY[Q.NOTEHEAD_IS_NOT_A_NOTEHEAD].subjects_from,
            Q.NOTEHEAD_CLASS)

    def test_it_is_decided_before_ownership_can_arbitrate_it(self):
        """A question about what a thing IS may not be settled after the
        question that assumes the answer -- `glyph_owner` arbitrates ink
        between staves and must not be handed a box already known to be
        furniture."""
        order = adjudicate.ORDER
        self.assertLess(order.index(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD),
                        order.index(Q.GLYPH_OWNER))


class TestCleanInkIsDecidedNotAbstained(unittest.TestCase):
    """A glyph none of the three rules condemns decides `False`, `notehead`
    -- not an abstention, because geometry was available and was tested."""

    def test_an_ordinary_notehead_decides_false(self):
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, cls="noteheadHalfInSpace", h_c=100.0,
                     w_c=140.0, pos_float=4.0, conf=0.9,
                     page_box=[520.0, 1100.0, 660.0, 1200.0])
        v = _verdict(_run(log), g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "notehead")


class TestClippedFragment(unittest.TestCase):
    """A notehead-shaped sliver flush against the cell's own crop boundary."""

    def test_a_short_slice_TOUCHING_the_cell_top_is_refused(self):
        log = Log()
        _cell_geometry(log)
        # h_c = 30 canonical px = 0.3 staff spaces, under the 0.6 floor.
        # page top (1000.0) coincides with the cell's own top (1000.0).
        g = _notehead(log, 0, h_c=30.0, pos_float=4.0,
                     page_box=[520.0, 1000.0, 560.0, 1010.0])
        v = _verdict(_run(log), g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "clipped_fragment")
        self.assertLess(v.detail["height_spaces"], 0.6)

    def test_the_SAME_SHORT_SLICE_AWAY_FROM_THE_EDGE_is_NOT_refused(self):
        """⚠️ POSITIVE CONTROL. `transcribe._CLIPPED_NOTEHEAD_MAX_SPACES`'s
        own docstring: "a short notehead in the middle of a cell is some
        other problem and this must not have an opinion about it." Same
        height as above, page box in the middle of the 300px-tall cell."""
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, h_c=30.0, pos_float=4.0,
                     page_box=[520.0, 1140.0, 560.0, 1150.0])
        v = _verdict(_run(log), g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "notehead")

    def test_a_TALL_notehead_AT_THE_EDGE_is_not_refused(self):
        """Touching the edge alone is not enough -- height must ALSO be
        under the floor, or a legitimately edge-grazing note (Sean's
        Flute 1 / Violin 1 F6, in the legacy docstring) would be deleted."""
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, h_c=95.0, pos_float=4.0,
                     page_box=[520.0, 1000.0, 660.0, 1095.0])
        v = _verdict(_run(log), g)
        self.assertIs(v.value, False)

    def test_with_NO_page_frame_it_declines_rather_than_guesses(self):
        """⚠️ `page_box=None` for both glyph and cell: the height alone is
        under the floor, but the edge test cannot run, so the honest default
        is NOT clipped -- never a guess either way. Still a DECIDED False,
        not an abstention: `too_narrow`/`unladdered` were still tested."""
        log = Log()
        _cell_geometry(log, cell_box=None)
        g = _notehead(log, 0, h_c=30.0, pos_float=4.0, page_box=None)
        v = _verdict(_run(log), g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, False)


class TestTooNarrow(unittest.TestCase):
    """A `noteheadBlack*` box under the measured 1.0-staff-space floor."""

    def test_a_narrow_BLACK_notehead_is_refused(self):
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, cls="noteheadBlackInSpace", w_c=80.0,
                     h_c=100.0, pos_float=4.0)
        v = _verdict(_run(log), g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "too_narrow")
        self.assertLess(v.detail["width_spaces"], 1.0)

    def test_a_WIDE_ENOUGH_black_notehead_is_NOT_refused(self):
        """⚠️ POSITIVE CONTROL, same class, width at the floor's other side."""
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, cls="noteheadBlackInSpace", w_c=120.0,
                     h_c=100.0, pos_float=4.0)
        v = _verdict(_run(log), g)
        self.assertIs(v.value, False)

    def test_a_narrow_WHOLE_notehead_is_NOT_refused_by_this_rule(self):
        """⚠️ `benchmarks/omr-notehead-width-2026-09/FINDINGS.md` §6: the
        under-floor count is ZERO for every Half and Whole class on both
        publishers -- that population's contamination is a class-identity
        fault, not a width one, and this rule has no opinion on it."""
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, cls="noteheadWholeInSpace", w_c=80.0,
                     h_c=100.0, pos_float=4.0)
        v = _verdict(_run(log), g)
        self.assertIs(v.value, False)


class TestUnladdered(unittest.TestCase):
    """A low-confidence notehead standing outside the staff, with not one
    ledger rung joining it to that staff."""

    def test_LOW_CONFIDENCE_outside_the_staff_with_NO_rung_is_refused(self):
        log = Log()
        _cell_geometry(log)
        # pos_float = -3.0: 1.5 staff spaces above the top line.
        # n_expected = int(1.5 + 0.25) = 1, and no ledgerLine glyph exists.
        g = _notehead(log, 0, w_c=140.0, h_c=100.0, conf=0.4,
                     pos_float=-3.0)
        v = _verdict(_run(log), g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "unladdered")
        self.assertEqual(v.detail["ledger_found"], 0)

    def test_THE_SAME_INK_WITH_ITS_OWN_RUNG_is_NOT_refused(self):
        """⚠️ POSITIVE CONTROL -- the whole point of the rule. Same box, same
        low confidence, same distance outside the staff; a `ledgerLine`
        glyph now sits at the one expected rung position and overlaps the
        notehead in x."""
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, x_c=200.0, y_c=200.0, w_c=140.0, h_c=100.0,
                     conf=0.4, pos_float=-3.0)
        # y_center = 250; half_step = 50; anchor (top line, canonical) =
        # 250 - (-3.0)*50 = 400; rung k=1 above -> 400 - 100 = 300.
        _ledger(log, 1, x_c=210.0, y_c=290.0, w_c=140.0, h_c=20.0)
        v = _verdict(_run(log), g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "notehead")

    def test_HIGH_CONFIDENCE_outside_the_staff_with_no_rung_is_NOT_refused(self):
        """The gate needs LOW confidence too -- a confidently-read outside-
        staff note is not this population."""
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, w_c=140.0, h_c=100.0, conf=0.9,
                     pos_float=-3.0)
        v = _verdict(_run(log), g)
        self.assertIs(v.value, False)

    def test_LOW_CONFIDENCE_INSIDE_THE_STAFF_is_NOT_refused(self):
        """A note inside the five-line band needs no ladder at all."""
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, w_c=140.0, h_c=100.0, conf=0.4,
                     pos_float=4.0)
        v = _verdict(_run(log), g)
        self.assertIs(v.value, False)


class TestItAbstainsOnlyWhenTheUnitItselfIsMissing(unittest.TestCase):

    def test_no_cell_staff_space_ABSTAINS(self):
        log = Log()
        _cell_geometry(log, spacing=None)
        g = _notehead(log, 0, pos_float=4.0)
        v = _verdict(_run(log), g)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)

    def test_the_positive_control_for_it(self):
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, pos_float=4.0)
        v = _verdict(_run(log), g)
        self.assertEqual(v.outcome, Outcome.DECIDED)


# ── the exporter ─────────────────────────────────────────────────────────────

def _obs(i, subject, quantity, value, **detail):
    return {"id": f"obs:{i:06d}", "subject": subject, "quantity": quantity,
            "value": value, "reader": "t", "frame": "f", "score": 0.5,
            "detail": detail, "basis": []}


def _vrd(i, subject, quantity, value, outcome="decided", reason="x"):
    return {"id": f"vrd:{i:06d}", "subject": subject, "quantity": quantity,
            "outcome": outcome, "value": value, "decider": "t",
            "reason": reason, "considered": [], "used": [], "missing": [],
            "declined": [], "excluded": [], "correlated": [],
            "candidates": [], "basis": [], "margin": None,
            "supersedes": None, "detail": {}}


def _two_note_page(*, flagged, reason="too_narrow"):
    obs, vrd = [], []
    for gi, pitch in enumerate(("C5", "D5")):
        sub = f"glyph/0/0/0/0/{gi}"
        obs.append(_obs(gi * 2, sub, Q.GLYPH_BOX,
                        ["noteheadBlackOnLine", 100 * gi, 50, 40, 40],
                        category="notehead"))
        obs.append(_obs(gi * 2 + 1, sub, Q.NOTEHEAD_CLASS,
                        "noteheadBlackOnLine"))
        vrd.append(_vrd(100 + gi, sub, Q.PITCH, pitch))
        vrd.append(_vrd(200 + gi, sub, Q.DURATION,
                        {"beats": 1.0, "written": 1.0, "dots": 0}))
    vrd.append(_vrd(900, "staff/0/0/0", Q.MEASURE_PARTITION, 1))
    vrd.append(_vrd(901, "staff/0/0/0", Q.CLEF, "treble"))
    vrd.append(_vrd(902, "system/0/0", Q.SYSTEM_STAFF_COUNT, 1))
    vrd.append(_vrd(903, "document", Q.PART_PARTITION,
                    {"join": "ordinal", "staves_per_system": 1},
                    reason="ordinal"))
    if flagged:
        vrd.append(_vrd(950, "glyph/0/0/0/0/0", Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,
                        True, reason=reason))
    return {"record": {"observations": obs, "verdicts": vrd,
                       "abstentions": []},
            "source": {}}


class TestARefusedNoteheadDoesNotReachTheFile(unittest.TestCase):

    @staticmethod
    def _pitches(xml):
        return [p.find("step").text + p.find("octave").text
                for p in ET.fromstring(xml).iter("pitch")]

    def test_the_flagged_note_does_not_reach_the_file(self):
        # ⚠️ The BASE arm is the positive control: without the verdict BOTH
        # notes are written.
        self.assertEqual(self._pitches(SX.to_musicxml(
            _two_note_page(flagged=False))[0]), ["C5", "D5"])
        self.assertEqual(self._pitches(SX.to_musicxml(
            _two_note_page(flagged=True))[0]), ["D5"])

    def test_it_is_COUNTED_under_its_reason(self):
        _, rep = SX.to_musicxml(_two_note_page(flagged=True,
                                              reason="too_narrow"))
        self.assertEqual(
            rep["notes_not_written"].get("not_a_notehead:too_narrow"), 1)

    def test_a_DIFFERENT_reason_is_counted_under_its_OWN_name(self):
        _, rep = SX.to_musicxml(_two_note_page(flagged=True,
                                              reason="clipped_fragment"))
        self.assertEqual(
            rep["notes_not_written"].get("not_a_notehead:clipped_fragment"),
            1)

    def test_the_accounting_control_still_balances(self):
        for flagged in (False, True):
            _, rep = SX.to_musicxml(_two_note_page(flagged=flagged))
            self.assertEqual(
                rep["written"]["notes"] + rep["notes_not_written_total"], 2,
                f"flagged={flagged}")

    def test_a_FALSE_verdict_changes_nothing(self):
        page = _two_note_page(flagged=False)
        page["record"]["verdicts"].append(
            _vrd(950, "glyph/0/0/0/0/0", Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,
                False, reason="notehead"))
        self.assertEqual(self._pitches(SX.to_musicxml(page)[0]),
                         ["C5", "D5"])


if __name__ == "__main__":
    unittest.main()
