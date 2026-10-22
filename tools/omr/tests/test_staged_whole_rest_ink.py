"""`notehead_is_a_whole_rest`: ink the page prints as SILENCE, refused.

⚠️⚠️ SEAN, 2026-09-11, reading the first cleanup artefact against the print:
*"in bars where it should be just whole note rest in two four. It's showing an
actual quarter note, not a quarter note rest."* On a bitonal 1870 plate a whole
rest is a small filled RECTANGLE hanging under a line and a notehead is a small
filled OVAL, and the detector confuses them.

⚠️ THE MEASURED SCOPE, so no test here reads as bigger than it is: of the 26
bars whose entire exported content is one lone quarter in a 2/4 bar, **5 are
this fault and 18 are REAL NOTES** whose bar-mates were never detected. The
rule fires on 25 of 2,347 noteheads. Its value is the error's SHAPE, not its
size -- a wrong note has to be hunted down, a missing one is a visible gap.

⚠️ EVERY REFUSAL TEST CARRIES ITS POSITIVE CONTROL IN THE SAME CLASS. A battery
of refusal tests passes by refusing everything, and this decision's whole
content is a conjunction: each `False` case below is paired with the `True` it
becomes when the one witness it is missing is supplied.
"""

from __future__ import annotations

import inspect
import os
import unittest
import xml.etree.ElementTree as ET

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import export as SX
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import Log, Outcome, Q, READERS

STAFF = R.staff(0, 0, 0)
#: A staff whose five lines sit 16 px apart, bottom line at y=400. One staff
#: step is 8 px, so the whole-rest slot (step 5.5) is at y = 400 - 44 = 356.
LINES = (336, 352, 368, 384, 400)
SPACING = 16.0
SLOT_Y = 400 - 5.5 * SPACING / 2.0          # 356.0


def _staff(log, lines=LINES, spacing=SPACING):
    log.observe(STAFF, Q.STAFF_LINES, list(lines), reader=READERS.GEOMETRY,
                frame="page")
    log.observe(STAFF, Q.STAFF_SPACING, spacing, reader=READERS.GEOMETRY,
                frame="page")


def _glyph(log, cell, gi, *, cy, h_spaces, aspect, page_box=True):
    """One detection the detector called a notehead, of a stated shape.

    ⚠️ The CANONICAL box is deliberately given a DIFFERENT, wrong shape from
    the page box. The decision must read `detail.bbox_page_px` -- a canonical
    box is measured inside one cell rescaled so the staff span is constant, so
    it cannot be compared with a staff's own lines at all, and a test whose two
    frames agree cannot tell a frame error from a correct reading. This is the
    `Q.ONSET_COLUMN` fault, pinned.
    """
    g = R.glyph(0, 0, 0, cell, gi)
    h = h_spaces * SPACING
    w = aspect * h
    kw = {}
    if page_box:
        kw["bbox_page_px"] = [1000.0, cy - h / 2.0, 1000.0 + w, cy + h / 2.0]
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlackInSpace", 7, 7, 999, 999),
                reader=READERS.DETECTOR, frame="cell:0", score=0.4,
                category="notehead", **kw)
    log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlackInSpace",
                reader=READERS.DETECTOR, frame="cell:0", score=0.4)
    return g


def _whole_rest(log, cell, gi, *, cy):
    g = R.glyph(0, 0, 0, cell, gi)
    h, w = 0.7 * SPACING, 1.5 * SPACING
    log.observe(g, Q.GLYPH_BOX, ("restWhole", 7, 7, 30, 12),
                reader=READERS.DETECTOR, frame="cell:0", score=0.5,
                category="rest",
                bbox_page_px=[1000.0, cy - h / 2.0, 1000.0 + w, cy + h / 2.0])
    log.observe(g, Q.REST, "restWhole", reader=READERS.DETECTOR,
                frame="cell:0", score=0.5)
    return g


def _run(log):
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.NOTEHEAD_IS_A_WHOLE_REST,))
    return log


def _verdict(log, g):
    return log.verdict(Q.NOTEHEAD_IS_A_WHOLE_REST, g)


class TestTheDecisionIsDeclaredTheWayItBehaves(unittest.TestCase):

    def test_it_is_not_a_stub(self):
        self.assertFalse(adjudicate.REGISTRY[Q.NOTEHEAD_IS_A_WHOLE_REST].stub)

    def test_its_domain_is_the_noteheads(self):
        """⚠️ ASSERTED OFF THE REGISTRY, not off the body. The decision is only
        safe because its domain is ink the detector ALREADY called a notehead:
        widening it to every glyph would let it refuse rests and clefs, and
        that widening must go red rather than pass quietly. Same guard the
        dedupe repair put on `glyph_owner`'s domain."""
        self.assertEqual(
            adjudicate.REGISTRY[Q.NOTEHEAD_IS_A_WHOLE_REST].subjects_from,
            Q.NOTEHEAD_CLASS)

    def test_it_is_decided_before_the_duration_and_the_events(self):
        """A question about what a thing IS may not be settled after the
        questions that assume the answer."""
        order = adjudicate.ORDER
        self.assertLess(order.index(Q.NOTEHEAD_IS_A_WHOLE_REST),
                        order.index(Q.DURATION))
        self.assertLess(order.index(Q.NOTEHEAD_IS_A_WHOLE_REST),
                        order.index(Q.EVENT))


class TestBothWitnessesMustAgree(unittest.TestCase):
    """⚠️ THE CONJUNCTION IS THE RULE. Measured over 2,347 noteheads: shape
    alone fires 148 times and position alone 310, and both populations hold
    real music; together they fire 25 times and all 25 are whole rests."""

    def test_rest_shaped_ink_in_the_slot_IS_a_whole_rest(self):
        log = Log()
        _staff(log)
        g = _glyph(log, 0, 0, cy=SLOT_Y, h_spaces=0.7, aspect=2.1)
        v = _verdict(_run(log), g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "shape_and_position_agree")
        self.assertEqual(v.detail["witness"], "slot")

    def test_a_NOTEHEAD_in_the_very_same_slot_is_refused(self):
        """POSITION ALONE IS NEARLY USELESS: the slot is where C5 and D5 live
        in treble, which is ordinary music."""
        log = Log()
        _staff(log)
        g = _glyph(log, 0, 0, cy=SLOT_Y, h_spaces=1.3, aspect=1.15)
        v = _verdict(_run(log), g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "not_rest_shaped")

    def test_rest_shaped_ink_where_no_whole_rest_can_hang_is_refused(self):
        """SHAPE ALONE IS NOT ENOUGH EITHER: on the measured page it fires on
        bled heads, beam residue and letters of the word *cresc.*"""
        log = Log()
        _staff(log)
        g = _glyph(log, 0, 0, cy=LINES[-1] + 6 * SPACING,
                   h_spaces=0.7, aspect=2.1)
        v = _verdict(_run(log), g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "not_where_a_whole_rest_can_hang")

    def test_a_LONG_THIN_SLIVER_in_the_slot_is_refused(self):
        """⚠️ THE UPPER ASPECT BOUND, and it costs nothing: the widest of the
        25 real catches is 2.35 and the first thing a one-sided rule admitted
        was a 5.49 sliver of line residue. That sliver is not a whole rest
        EITHER, so excluding it by DESCRIPTION rather than reaching the right
        outcome through a wrong one is the point -- a decision may only claim
        what it can support."""
        log = Log()
        _staff(log)
        g = _glyph(log, 0, 0, cy=SLOT_Y, h_spaces=0.7, aspect=5.5)
        v = _verdict(_run(log), g)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "not_rest_shaped")

    def test_the_two_refusals_are_told_apart(self):
        """*"not rest-shaped"* and *"rest-shaped but in the wrong place"* are
        different facts about the page; folding them together would hide that
        the second names the population a shape-only rule would delete."""
        self.assertNotEqual("not_rest_shaped",
                            "not_where_a_whole_rest_can_hang")
        reasons = adjudicate.REGISTRY[Q.NOTEHEAD_IS_A_WHOLE_REST].reasons
        self.assertIn("not_rest_shaped", reasons)
        self.assertIn("not_where_a_whole_rest_can_hang", reasons)


class TestTheNeighbouringBarIsTheSecondWayToEstablishPosition(unittest.TestCase):
    """⚠️ `Q.STAFF_LINES` models a staff as five IDEAL rows while a scanned
    staff tilts and bows, so this document's own correctly-read whole rests
    spread over steps 2.5-5.9. A tacet part prints a whole rest in EVERY bar,
    and a shared registration error cancels between two rows of one staff --
    which is what catches `P1 m85`, at step 4.21, that the absolute slot
    misses."""

    def _off_slot_y(self):
        return SLOT_Y + 2.0 * SPACING / 2.0        # two steps low: outside 1.0

    def test_off_slot_ink_with_a_whole_rest_next_door_IS_one(self):
        log = Log()
        _staff(log)
        y = self._off_slot_y()
        _whole_rest(log, 1, 0, cy=y)
        g = _glyph(log, 2, 0, cy=y, h_spaces=0.7, aspect=2.1)
        v = _verdict(_run(log), g)
        self.assertIs(v.value, True)
        self.assertEqual(v.detail["witness"], "neighbouring_bar")
        self.assertEqual(v.detail["neighbour"]["cell"], 1)

    def test_the_SAME_ink_with_no_neighbour_is_refused(self):
        """⚠️ THE POSITIVE CONTROL FOR THE TEST ABOVE: identical ink at an
        identical height, and the ONLY difference is the neighbouring bar."""
        log = Log()
        _staff(log)
        g = _glyph(log, 2, 0, cy=self._off_slot_y(), h_spaces=0.7, aspect=2.1)
        self.assertIs(_verdict(_run(log), g).value, False)

    def test_a_neighbour_TOO_FAR_ALONG_THE_STAFF_does_not_vouch(self):
        """A long reach would let one distant rest vouch for ink anywhere on
        the staff.

        ⚠️ THE DISTANCE IS A LITERAL, NOT THE CONSTANT. Placing the neighbour
        at `WHOLE_REST_NEIGHBOUR_BARS + 1` moves the fixture whenever the
        constant moves, so the test passes for every value of it and pins
        nothing — measured: two mutation arms widening these two constants to
        99 SURVIVED a green suite. Eight bars away must stay refused whatever
        the constant says, and widening it to reach there is a behaviour
        change that should have to be re-argued.
        """
        log = Log()
        _staff(log)
        y = self._off_slot_y()
        _whole_rest(log, 10, 0, cy=y)          # eight bars away
        g = _glyph(log, 2, 0, cy=y, h_spaces=0.7, aspect=2.1)
        self.assertIs(_verdict(_run(log), g).value, False)

    def test_a_neighbour_AT_A_DIFFERENT_HEIGHT_does_not_vouch(self):
        """⚠️ Also a LITERAL: five staff steps is most of a staff, and a rest
        that far from this ink is a different row of music."""
        log = Log()
        _staff(log)
        _whole_rest(log, 1, 0,
                    cy=self._off_slot_y() + 5.0 * SPACING / 2.0)
        g = _glyph(log, 2, 0, cy=self._off_slot_y(), h_spaces=0.7, aspect=2.1)
        self.assertIs(_verdict(_run(log), g).value, False)

    def test_the_neighbour_constants_are_narrow_enough_to_mean_something(self):
        """⚠️ The two tests above use literals so they cannot move with the
        constants; this is the other half of that pair — the constants must
        stay inside the window those literals describe, or the rule would
        reach past what has been adjudicated."""
        self.assertLess(rhythm.WHOLE_REST_NEIGHBOUR_BARS, 8)
        self.assertLess(rhythm.WHOLE_REST_NEIGHBOUR_STEPS, 5.0)


class TestItAbstainsRatherThanGuessing(unittest.TestCase):

    def test_no_page_frame_ABSTAINS(self):
        """⚠️ DECLINED, NOT DEFAULTED. `gather_detections` omits the page box
        rather than inventing one, and the canonical frame cannot answer a
        question about a staff's lines."""
        log = Log()
        _staff(log)
        g = _glyph(log, 0, 0, cy=SLOT_Y, h_spaces=0.7, aspect=2.1,
                   page_box=False)
        v = _verdict(_run(log), g)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_page_frame")

    def test_no_staff_geometry_ABSTAINS(self):
        log = Log()                       # no _staff(log)
        g = _glyph(log, 0, 0, cy=SLOT_Y, h_spaces=0.7, aspect=2.1)
        v = _verdict(_run(log), g)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)

    def test_the_positive_control_for_both(self):
        """⚠️ Two abstention tests pass for free if the decision has died.
        This is the same fixture with both inputs present."""
        log = Log()
        _staff(log)
        g = _glyph(log, 0, 0, cy=SLOT_Y, h_spaces=0.7, aspect=2.1)
        self.assertEqual(_verdict(_run(log), g).outcome, Outcome.DECIDED)


class TestTheCutsAreSTAFFSPACESNotPixels(unittest.TestCase):
    """⚠️ The staves of one plate differ in spacing and the DPI differs between
    runs, so a pixel constant would be a property of one render of one page.
    The same ink on a staff at HALF the spacing must read the same way."""

    def test_the_same_glyph_decides_the_same_on_a_smaller_staff(self):
        got = []
        for spacing in (16.0, 8.0, 32.0):
            lines = tuple(400 - int(spacing) * i for i in (4, 3, 2, 1, 0))
            log = Log()
            _staff(log, lines=lines, spacing=spacing)
            g = R.glyph(0, 0, 0, 0, 0)
            cy = 400 - 5.5 * spacing / 2.0
            h, w = 0.7 * spacing, 2.1 * 0.7 * spacing
            log.observe(g, Q.GLYPH_BOX, ("noteheadBlackInSpace", 7, 7, 9, 9),
                        reader=READERS.DETECTOR, frame="cell:0", score=0.4,
                        category="notehead",
                        bbox_page_px=[1000.0, cy - h / 2.0, 1000.0 + w,
                                      cy + h / 2.0])
            log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlackInSpace",
                        reader=READERS.DETECTOR, frame="cell:0", score=0.4)
            got.append(_verdict(_run(log), g).value)
        self.assertEqual(got, [True, True, True])


class TestTheConstantsAreDerivedAndNamed(unittest.TestCase):
    """⚠️ Not a behaviour test -- a drift test. Each of these was derived from
    the document's OWN 395 detected whole rests and then swept; a silent edit
    that put one outside the population it was derived from would change what
    the rule means without changing what any behavioural fixture says."""

    def test_the_slot_is_the_engraving_convention(self):
        self.assertEqual(rhythm.WHOLE_REST_STEP, 5.5)

    def test_the_aspect_band_is_two_sided(self):
        self.assertLess(rhythm.WHOLE_REST_INK_MIN_ASPECT,
                        rhythm.WHOLE_REST_INK_MAX_ASPECT)

    def test_the_height_cut_excludes_a_median_notehead(self):
        """A notehead's median height on the measured page is 1.31 spaces."""
        self.assertLess(rhythm.WHOLE_REST_INK_MAX_HEIGHT_SPACES, 1.31)

    def test_confidence_is_not_a_witness(self):
        """⚠️ The flagged glyphs DO sit low (median 0.36 against 0.66), and a
        confidence filter is measured and REFUSED one family over at 233 good
        dynamic letters lost to remove half of 35 bad ones. A tier that is a
        proxy for ink quality is not evidence about what a glyph IS."""
        src = inspect.getsource(rhythm.adjudicate_notehead_is_a_whole_rest)
        self.assertNotIn("Q.GLYPH_CONF", src)
        self.assertNotIn(".score", src)


# ── the exporter ────────────────────────────────────────────────────────────

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


def _two_note_page(*, flagged):
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
        vrd.append(_vrd(950, "glyph/0/0/0/0/0", Q.NOTEHEAD_IS_A_WHOLE_REST,
                        True, reason="shape_and_position_agree"))
    return {"record": {"observations": obs, "verdicts": vrd,
                       "abstentions": []},
            "source": {}}


class TestInkTheRecordCallsAWholeRestIsNotWrittenAsANote(unittest.TestCase):
    """⚠️ A `True` verdict must reach the FILE, not merely the record. This is
    the `dynamic`-decides-and-nothing-writes-it shape, asserted before it can
    happen again."""

    @staticmethod
    def _pitches(xml):
        return [p.find("step").text + p.find("octave").text
                for p in ET.fromstring(xml).iter("pitch")]

    def test_the_flagged_note_does_not_reach_the_file(self):
        # ⚠️ The BASE arm is the positive control: without the verdict BOTH
        # notes are written, so a fixture that wrote neither could not be told
        # from a rule that works.
        self.assertEqual(self._pitches(SX.to_musicxml(
            _two_note_page(flagged=False))[0]), ["C5", "D5"])
        self.assertEqual(self._pitches(SX.to_musicxml(
            _two_note_page(flagged=True))[0]), ["D5"])

    def test_it_is_COUNTED_under_its_own_name(self):
        """A refusal that is not counted is how the accounting control stops
        being able to fire."""
        _, rep = SX.to_musicxml(_two_note_page(flagged=True))
        self.assertEqual(
            rep["notes_not_written"].get("ink_is_a_whole_rest"), 1)

    def test_the_accounting_control_still_balances(self):
        for flagged in (False, True):
            _, rep = SX.to_musicxml(_two_note_page(flagged=flagged))
            self.assertEqual(
                rep["written"]["notes"] + rep["notes_not_written_total"], 2,
                f"flagged={flagged}")

    def test_NO_rest_element_is_manufactured(self):
        """⚠️ REFUSED, NOT CONVERTED. What ink is on the page is a GATHER fact;
        the bar falls to the padded measure rest, which says *we read nothing
        here* rather than *we read silence*."""
        xml, _ = SX.to_musicxml(_two_note_page(flagged=True))
        root = ET.fromstring(xml)
        self.assertEqual(len(root.findall(".//rest")), 0)
        self.assertEqual(len(root.findall(".//note")), 1)

    def test_a_FALSE_verdict_changes_nothing(self):
        page = _two_note_page(flagged=False)
        page["record"]["verdicts"].append(
            _vrd(951, "glyph/0/0/0/0/0", Q.NOTEHEAD_IS_A_WHOLE_REST, False,
                 reason="not_rest_shaped"))
        self.assertEqual(self._pitches(SX.to_musicxml(page)[0]), ["C5", "D5"])

    def test_an_ABSTENTION_changes_nothing(self):
        page = _two_note_page(flagged=False)
        page["record"]["verdicts"].append(
            _vrd(952, "glyph/0/0/0/0/0", Q.NOTEHEAD_IS_A_WHOLE_REST, None,
                 outcome="abstained", reason="no_page_frame"))
        self.assertEqual(self._pitches(SX.to_musicxml(page)[0]), ["C5", "D5"])


class TestTheFlagTurnsTheREFUSALOffAndNothingElse(unittest.TestCase):
    """`OMR_WHOLE_REST_INK` — default ON, and off restores the pre-2026-09-15
    exporter exactly.

    ⚠️ IT IS FLAGGED BECAUSE IT DELETES MUSIC. Every other staged repair adds
    an element or withholds one the record never decided; this one removes
    pitched notes from a file on the evidence of ONE document, where two of the
    six cuts sit on a plateau one step wide or less. The flag makes the call
    Sean's and reversible in a word.

    ⚠️ WHAT IT MUST **NOT** TURN OFF IS THE DECISION. The verdict is an
    ADJUDICATE fact and stays on the record either way; only the exporter's
    refusal is gated. Gating the decision instead would throw away the evidence
    along with the behaviour, and a later consumer — a bar sum that should not
    count this ink — would find the quantity missing rather than decided.
    """

    def setUp(self):
        self._prior = os.environ.get(SX.WHOLE_REST_INK_ENV)

    def tearDown(self):
        if self._prior is None:
            os.environ.pop(SX.WHOLE_REST_INK_ENV, None)
        else:
            os.environ[SX.WHOLE_REST_INK_ENV] = self._prior

    @staticmethod
    def _pitches(xml):
        return [p.find("step").text + p.find("octave").text
                for p in ET.fromstring(xml).iter("pitch")]

    def test_the_default_REFUSES(self):
        """⚠️ THE POSITIVE CONTROL FOR EVERY TEST BELOW. A flag suite that only
        ever asserted the off state would pass against a rule that never fires
        — the `a battery of refusal tests can pass by refusing everything`
        lesson, pointed the other way."""
        os.environ.pop(SX.WHOLE_REST_INK_ENV, None)
        self.assertEqual(
            self._pitches(SX.to_musicxml(_two_note_page(flagged=True))[0]),
            ["D5"])

    def test_OFF_writes_the_note_the_rule_would_have_refused(self):
        os.environ[SX.WHOLE_REST_INK_ENV] = "0"
        self.assertEqual(
            self._pitches(SX.to_musicxml(_two_note_page(flagged=True))[0]),
            ["C5", "D5"])

    def test_OFF_does_not_COUNT_a_refusal_it_did_not_make(self):
        """A counter naming an element the exporter still wrote is the
        `control that computes the wrong thing`."""
        os.environ[SX.WHOLE_REST_INK_ENV] = "0"
        _, rep = SX.to_musicxml(_two_note_page(flagged=True))
        self.assertNotIn("ink_is_a_whole_rest", rep["notes_not_written"])

    def test_the_accounting_control_balances_under_BOTH_settings(self):
        for val, written in (("1", 1), ("0", 2)):
            os.environ[SX.WHOLE_REST_INK_ENV] = val
            _, rep = SX.to_musicxml(_two_note_page(flagged=True))
            self.assertEqual(rep["written"]["notes"], written, val)
            self.assertEqual(
                rep["written"]["notes"] + rep["notes_not_written_total"], 2,
                val)

    def test_every_OFF_WORD_turns_it_off_and_a_TYPO_does_not(self):
        """⚠️⚠️ THE DIRECTION FOLLOWS THE DEFAULT. On by default, so the test
        is a DENY-list: `OMR_WHOLE_REST_INK=yess` must leave the refusal ON,
        because an allow-list would silently put the phantom notes back on a
        misspelling. `test_flag_default_direction.py` derives this from the
        source; this pins the behaviour it derives."""
        for off in ("0", "", "false", "no", "off", "OFF", " off "):
            os.environ[SX.WHOLE_REST_INK_ENV] = off
            self.assertFalse(SX.whole_rest_ink_enabled(), repr(off))
        for on in ("1", "true", "yes", "on", "yess", "ON!", "banana"):
            os.environ[SX.WHOLE_REST_INK_ENV] = on
            self.assertTrue(SX.whole_rest_ink_enabled(), repr(on))

    def test_the_DECISION_is_untouched_by_the_flag(self):
        """The flag is the exporter's, not the adjudicator's — `stubs()` and
        the registry do not move, and neither does the verdict."""
        os.environ[SX.WHOLE_REST_INK_ENV] = "0"
        log = Log()
        _staff(log)
        g = _glyph(log, 0, 0, cy=SLOT_Y, h_spaces=0.7, aspect=2.0)
        _run(log)
        self.assertIs(_verdict(log, g).value, True)


if __name__ == "__main__":
    unittest.main()
