"""ROADMAP 2.7b — a head filed on a staff it does not belong to.

Sean's convention (2026-09-27): *"notes should never be that far away from a
staff unless there are ledger lines close to the staff connecting the note
conceptually to the staff."* `notehead_is_not_a_notehead` refuses such a head
on its filed staff, reason `belongs_to_a_nearer_staff`; it is dropped, never
relocated (CLAUDE.md §10), and its accidental follows it.

⚠️ THE GEOMETRY IS MEASURED, NOT INVENTED. `fixtures/nearer_staff_litolff_p3.
json` is cut from the Litolff acceptance record (re-decided on a5f7cf58) by
`benchmarks/omr-accidental-2026-09/probe/extract_nearer_fixture.py`: the page
box of every head Sean adjudicated in 2.7 (`out/print/ADJUDICATION-sean-2026-
09-27.json`), the lines of every staff of its system, every ledger box of its
cell with its 3.4g-2 verdict, and GATHER's band rows. The negatives are his
six wrong-staff heads (crops 4, 13, 20, 23, 26 decided + control 2); the
positive controls are the eighteen heads of his twenty-one confirmed crops,
ALL of which must be kept — a refusal battery passes by refusing everything.

Run RED first against a5f7cf58 (no `belongs_to_a_nearer_staff`, no
`is_a_key_signature_marker`): the refusal, yield, rung, header and
follow-the-head tests fail; the positive controls pass on both trees.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import export as E
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS, Subject

FIXTURE = json.loads((Path(__file__).parent / "fixtures"
                      / "nearer_staff_litolff_p3.json").read_text())
HEADS = {h["subject"]: h for h in FIXTURE["heads"]}
#: Sean's five decided wrong-staff pairings, by head.
FIVE = {h["subject"] for h in FIXTURE["heads"]
        if h["sean"] == "wrong_staff" and h["crops"] != [2]}
#: Crop 2: the same finding, and the one of the six whose near staff DID
#: detect the ink — `glyph_owner` already awards it there by ladder.
CROP_2 = next(h["subject"] for h in FIXTURE["heads"] if h["crops"] == [2])
CONFIRMED = {h["subject"] for h in FIXTURE["heads"] if h["sean"] == "confirmed"}


def _verdict(log, subject, quantity, value, *, reason="fixture"):
    return log.record(R.Verdict(
        id=log._next_id("vrd"), subject=subject, quantity=quantity,
        outcome=R.Outcome.DECIDED, value=value, decider="t", reason=reason))


def _build(head_key, *, extra_ledgers=(), drop_bands=False, bands=None,
          recentre=None):
    """A log holding exactly what the record held for this head.

    `recentre` (ROADMAP 2.39b) — `None` (every existing caller) files no
    `Q.NOTEHEAD_RECENTRE` row at all, byte-identical to before this
    parameter existed; `(dx_sp, dy_sp)` files GATHER's own observation, the
    shape `test_staged_notehead_recentre.py` exercises against this same
    fixture.
    """
    h = HEADS[head_key]
    g = Subject.from_key(head_key)
    log = Log()
    for key, st in FIXTURE["staves"].items():
        s = Subject.from_key(key)
        log.observe(s, Q.STAFF_LINES, list(st["staff_lines"]),
                    reader=READERS.GEOMETRY, frame="page")
        log.observe(s, Q.STAFF_SPACING, st["staff_spacing"],
                    reader=READERS.GEOMETRY, frame="page")
    cell_key = "cell/" + "/".join(head_key.split("/")[1:5])
    cell = Subject.from_key(cell_key)
    geo = FIXTURE["cells"][cell_key]
    log.observe(cell, Q.CELL_STAFF_SPACE, geo["cell_staff_space"][0],
                reader=READERS.GEOMETRY, frame=f"cell:{g.cell}",
                **(geo["cell_staff_space"][1] or {}))
    log.observe(cell, Q.CELL_BOX, geo["cell_box"][0],
                reader=READERS.GEOMETRY, frame=f"cell:{g.cell}")
    log.observe(g, Q.GLYPH_BOX, tuple(h["value"]), reader=READERS.DETECTOR,
                frame=f"cell:{g.cell}", score=0.9, category=h["category"],
                bbox_page_px=h["bbox_page_px"])
    log.observe(g, Q.NOTEHEAD_CLASS, h["value"][0], reader=READERS.DETECTOR,
                frame=f"cell:{g.cell}", score=0.9)
    if recentre is not None:
        dx_sp, dy_sp = recentre
        log.observe(g, Q.NOTEHEAD_RECENTRE, [dx_sp, dy_sp],
                    reader=READERS.CV_NOTEHEAD_RECENTRE,
                    frame=f"cell:{g.cell}", fill=0.9, margin=0.2,
                    runner_up=0.7)
    for value, cand in (bands if bands is not None else
                        ([] if drop_bands else h["band_rows"])):
        log.observe(g, Q.GLYPH_BAND_DISTANCE, value, reader=READERS.GEOMETRY,
                    frame="page", candidate=cand)
    ledgers = list(h["ledgers"]) + list(extra_ledgers)
    for L in ledgers:
        ls = Subject.from_key(L["subject"])
        log.observe(ls, Q.GLYPH_BOX, tuple(L["value"]),
                    reader=READERS.DETECTOR, frame=f"cell:{g.cell}",
                    score=0.7, category="ledger",
                    bbox_page_px=L["bbox_page_px"])
    log.freeze()
    for L in ledgers:
        _verdict(log, Subject.from_key(L["subject"]),
                 Q.LEDGER_IS_NOT_A_LEDGER, bool(L["refused"]),
                 reason=L["reason"] or "ledger_line")
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,))
    return log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)


def _rung_between_head_and_filed(head_key):
    """A ledger box one space off the filed staff's outer line, on the head's
    side, x-overlapping it — the first rung of a real ladder."""
    h = HEADS[head_key]
    staff = "staff/" + "/".join(head_key.split("/")[1:4])
    ys = sorted(FIXTURE["staves"][staff]["staff_lines"])
    sp = FIXTURE["staves"][staff]["staff_spacing"]
    x0, y0, x1, y1 = h["bbox_page_px"]
    y = (y0 + y1) / 2.0
    ry = ys[0] - sp if y < ys[0] else ys[-1] + sp
    parts = head_key.split("/")
    sub = "/".join(parts[:5] + ["999"])
    return {"subject": sub, "value": ["ledgerLine", 0, 0, 10, 2],
            "bbox_page_px": [x0 - 5.0, ry - 2.0, x1 + 5.0, ry + 2.0]}


def _ladder_from_filed(head_key):
    """Every rung from the filed staff's outer line to the head, one staff
    space apart, x-overlapping it — a complete ladder (ROADMAP 2.6c)."""
    from tools.omr.staged.gather import LEDGER_ROUND_UP
    h = HEADS[head_key]
    staff = "staff/" + "/".join(head_key.split("/")[1:4])
    ys = sorted(FIXTURE["staves"][staff]["staff_lines"])
    sp = FIXTURE["staves"][staff]["staff_spacing"]
    x0, y0, x1, y1 = h["bbox_page_px"]
    y = (y0 + y1) / 2.0
    above = y < ys[0]
    edge = ys[0] if above else ys[-1]
    n = int(abs(edge - y) / sp + LEDGER_ROUND_UP)
    parts = head_key.split("/")
    out = []
    for i in range(1, n + 1):
        ry = edge - i * sp if above else edge + i * sp
        out.append({"subject": "/".join(parts[:5] + [str(900 + i)]),
                    "value": ["ledgerLine", 0, 0, 10, 2],
                    "bbox_page_px": [x0 - 5.0, ry - 2.0, x1 + 5.0, ry + 2.0]})
    return out


class TestTheFixtureIsWhatSeanAdjudicated(unittest.TestCase):

    def test_five_decided_wrong_staff_heads_and_eighteen_confirmed(self):
        self.assertEqual(len(FIVE), 5)
        self.assertEqual(len(CONFIRMED), 18)
        crops = sorted(c for k in CONFIRMED for c in HEADS[k]["crops"])
        self.assertEqual(len(crops), 21)
        self.assertEqual(sorted(c for k in FIVE for c in HEADS[k]["crops"]),
                         [4, 13, 20, 23, 26])

    def test_on_the_base_tree_none_of_the_five_was_refused(self):
        """The finding: all five were written, on the wrong staff."""
        for k in FIVE:
            self.assertEqual(HEADS[k]["npv_on_base"],
                             ["decided", False, "notehead"], k)


class TestSeansFiveAreRefusedOnTheStaffTheyWereFiledOn(unittest.TestCase):

    def test_each_of_the_five_is_refused_belongs_to_a_nearer_staff(self):
        for k in sorted(FIVE):
            with self.subTest(head=k, crops=HEADS[k]["crops"]):
                v = _build(k)
                self.assertEqual(v.outcome, Outcome.DECIDED)
                self.assertIs(v.value, True)
                self.assertEqual(v.reason, "belongs_to_a_nearer_staff")
                sig = v.detail["nearer_staff_signal"]
                self.assertGreater(sig["filed_spaces"], 3.0)
                self.assertLessEqual(sig["near_spaces"], 2.75)
                self.assertEqual(sig["kept_rungs_toward_filed"], 0)

    def test_the_near_staff_is_the_one_ABOVE(self):
        """⚠️ Measured, and it inverts the 2.7 ledger's wording: every one of
        the five sits ABOVE its filed staff, on ledger lines UNDER the staff
        above — filed one staff too LOW, not too high."""
        for k in sorted(FIVE):
            v = _build(k)
            filed = int(k.split("/")[3])
            near = int(v.detail["nearer_staff_signal"]["near_staff"]
                       .split("/")[3])
            self.assertEqual(near, filed - 1, k)


class TestNearerStaffUsesTheStandardHeadBox(unittest.TestCase):
    """ROADMAP 2.39 -- the x-window `_belongs_to_a_nearer_staff` hands to
    `ladder_sides_with_discount` (which then searches for a ladder) is the
    STANDARD box for a REGULAR notehead (every head in this fixture is
    `noteheadBlackOnLine`/`noteheadBlackInSpace`/`noteheadHalfInSpace`),
    not the raw detector box CLAUDE.md Sec.10 says a MERGING plate (this
    fixture's own Litolff) inflates. `TestSeansFiveAreRefusedOnTheStaffThey
    WereFiledOn`/`TestTheConfirmedHeadsAreKept` above are the POSITIVE
    CONTROLS this change must not move -- both classes still pass
    unchanged with the standard box wired in.

    ⚠️ RUN RED FIRST: `notehead_precision.ladder_sides_with_discount` was
    called with the raw `bbox_page_px` x0/x1 before this change -- this
    test failed asserting `assertNotEqual` (they WERE equal) against the
    pre-change tree.
    """

    def _filed_x_window(self, head_key):
        import tools.omr.staged.adjudicators.notehead_precision as NP
        calls = []
        real = NP.ladder_sides_with_discount

        def spy(pair):
            calls.append(pair)
            return real(pair)

        NP.ladder_sides_with_discount = spy
        try:
            _build(head_key)
        finally:
            NP.ladder_sides_with_discount = real
        self.assertEqual(len(calls), 1, head_key)
        filed_side = calls[0][0]      # (staff_key, y, x0, x1, ys, sp, rungs)
        return filed_side[2], filed_side[3]

    def test_a_regular_head_gets_the_standard_box_not_the_raw_one(self):
        from tools.omr.staged import geometry as G
        for k in sorted(FIVE):
            with self.subTest(head=k):
                h = HEADS[k]
                self.assertTrue(G.is_regular_notehead(h["value"][0]), k)
                raw_x0, y0, raw_x1, y1 = h["bbox_page_px"]
                x0, x1 = self._filed_x_window(k)
                self.assertNotEqual((x0, x1), (raw_x0, raw_x1))
                staff = "staff/" + "/".join(k.split("/")[1:4])
                sp = FIXTURE["staves"][staff]["staff_spacing"]
                cx = (raw_x0 + raw_x1) / 2.0
                cy = (y0 + y1) / 2.0
                std_x0, std_x1, _, _ = G.standard_head_box(cx, cy, sp)
                self.assertAlmostEqual(x0, std_x0, places=3)
                self.assertAlmostEqual(x1, std_x1, places=3)


class TestTheConfirmedHeadsAreKept(unittest.TestCase):
    """The positive controls, all of them."""

    def test_every_confirmed_head_is_kept(self):
        for k in sorted(CONFIRMED):
            with self.subTest(head=k, crops=HEADS[k]["crops"]):
                v = _build(k)
                self.assertEqual(v.outcome, Outcome.DECIDED)
                self.assertIs(v.value, False)
                self.assertEqual(v.reason, "notehead")

    def test_the_tremolo_slash_keeps_its_OWN_refusal(self):
        """Crop 3's 'head' is too narrow; the shape rule answers first."""
        k = next(h["subject"] for h in FIXTURE["heads"]
                 if h["sean"] == "not_a_head")
        self.assertEqual(_build(k).reason, "too_narrow")


class TestNearerStaffReadsTheRecentre(unittest.TestCase):
    """ROADMAP 2.39b -- the standard box `TestNearerStaffUsesTheStandardHead
    Box` proved is wired is now RE-CENTRED where GATHER's own `Q.NOTEHEAD_
    RECENTRE` row exists for this head.

    ⚠️ RUN RED FIRST: `_build`'s `recentre=` keyword did not exist before
    this round, and `_belongs_to_a_nearer_staff` read no such row --
    `test_a_recentre_row_shifts_the_ladder_x_window` fails asserting
    `assertNotEqual` (the shifted and un-shifted windows were equal)
    against the pre-2.39b tree.
    """

    def _filed_x_window(self, head_key, *, recentre=None):
        import tools.omr.staged.adjudicators.notehead_precision as NP
        calls = []
        real = NP.ladder_sides_with_discount

        def spy(pair):
            calls.append(pair)
            return real(pair)

        NP.ladder_sides_with_discount = spy
        try:
            _build(head_key, recentre=recentre)
        finally:
            NP.ladder_sides_with_discount = real
        self.assertEqual(len(calls), 1, head_key)
        filed_side = calls[0][0]
        return filed_side[2], filed_side[3]

    def test_a_recentre_row_shifts_the_ladder_x_window(self):
        k = sorted(FIVE)[0]
        staff = "staff/" + "/".join(k.split("/")[1:4])
        sp = FIXTURE["staves"][staff]["staff_spacing"]
        baseline = self._filed_x_window(k)
        shifted = self._filed_x_window(k, recentre=(0.25, 0.0))
        self.assertNotEqual(baseline, shifted)
        self.assertAlmostEqual(shifted[0] - baseline[0], 0.25 * sp, places=3)
        self.assertAlmostEqual(shifted[1] - baseline[1], 0.25 * sp, places=3)

    def test_zero_shift_is_the_control(self):
        """⚠️ THE CONTROL: a row that exists but carries no real offset
        must not move the window at all."""
        k = sorted(FIVE)[0]
        baseline = self._filed_x_window(k)
        zero = self._filed_x_window(k, recentre=(0.0, 0.0))
        self.assertEqual(baseline, zero)

    def test_every_confirmed_head_is_still_kept_with_a_small_recentre(self):
        """⚠️ THE OTHER CONTROL, over the whole positive-control set: a
        modest re-centre (well inside the search's own +-0.6/+-0.4 sp
        bound) must not flip a single genuinely-confirmed head."""
        for k in sorted(CONFIRMED):
            with self.subTest(head=k):
                v = _build(k, recentre=(0.1, -0.1))
                self.assertEqual(v.outcome, Outcome.DECIDED)
                self.assertIs(v.value, False)


class TestAKeptRungIsSeansException(unittest.TestCase):

    def test_a_kept_LADDER_toward_the_filed_staff_keeps_the_head(self):
        """⚠️ ROADMAP 2.6c: the exception is a LADDER from the filed staff
        that reaches the note (`ownership.ledger_direction`), not one rung —
        every rung from the filed staff's outer line to the head, kept."""
        k = sorted(FIVE)[0]
        rungs = [dict(r, refused=False, reason=None)
                 for r in _ladder_from_filed(k)]
        v = _build(k, extra_ledgers=rungs)
        self.assertIs(v.value, False)
        sig = v.detail["nearer_staff_signal"]
        self.assertEqual(sig["kept_rungs_toward_filed"], len(rungs))
        self.assertEqual(sig["ledger"]["winner"],
                         "staff/" + "/".join(k.split("/")[1:4]))

    def test_ONE_kept_rung_is_not_a_ladder_and_no_longer_keeps_it(self):
        """⚠️ ROADMAP 2.6c — the 2.7b cut kept a head on ANY kept rung between
        it and the filed staff, and Sean's 2.7b.8 verdicts found three of six
        such keeps wrong (#4, #22 a chord-mate's own ledger; #10 rungs ending
        short of the 'head'). The first rung alone, with the rest of the
        ladder to the head missing, does not name the filed staff. RED on
        8100c9ff (kept, `kept_rungs_toward_filed == 1`)."""
        k = sorted(FIVE)[0]
        rung = dict(_rung_between_head_and_filed(k), refused=False,
                    reason=None)
        v = _build(k, extra_ledgers=[rung])
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "belongs_to_a_nearer_staff")
        self.assertEqual(
            v.detail["nearer_staff_signal"]["kept_rungs_toward_filed"], 1)

    def test_a_REFUSED_rung_there_does_not(self):
        """The same box, refused by 3.4g-2: the VERDICT is read, not the box —
        a staff-line fragment cannot vouch for a note."""
        k = sorted(FIVE)[0]
        rung = dict(_rung_between_head_and_filed(k), refused=True,
                    reason="on_a_staff_line")
        v = _build(k, extra_ledgers=[rung])
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "belongs_to_a_nearer_staff")
        self.assertEqual(v.detail["nearer_staff_signal"]
                         ["refused_rungs_toward_filed"],
                         {"on_a_staff_line": 1})


    def test_the_heads_OWN_ledger_line_is_not_a_rung_toward_either_staff(self):
        """A kept ledger through the head's centre says the note stands on a
        ledger line, not whose — measured: 43 of the 79 far heads the first
        cut kept were kept by exactly that (`probe/kept_rungs.py`)."""
        k = sorted(FIVE)[0]
        h = HEADS[k]
        x0, y0, x1, y1 = h["bbox_page_px"]
        y = (y0 + y1) / 2.0
        parts = k.split("/")
        own = {"subject": "/".join(parts[:5] + ["998"]),
               "value": ["ledgerLine", 0, 0, 10, 2],
               "bbox_page_px": [x0 - 5.0, y - 1.0, x1 + 5.0, y + 3.0],
               "refused": False, "reason": None}
        v = _build(k, extra_ledgers=[own])
        self.assertEqual(v.reason, "belongs_to_a_nearer_staff")
        self.assertEqual(
            v.detail["nearer_staff_signal"]["kept_rungs_toward_filed"], 0)


class TestItYieldsToTheContestWhereTheNearStaffHoldsATwin(unittest.TestCase):

    def test_crop_2_is_in_the_contest_and_this_rule_yields(self):
        """Crop 2's twin was detected on the staff above; `glyph_owner`
        awards it there by ladder and drops this copy. A second refusal
        here would be two answers to one question."""
        self.assertTrue(any(c == "staff/3/0/7"
                            for _v, c in HEADS[CROP_2]["band_rows"]))
        v = _build(CROP_2)
        self.assertIs(v.value, False)
        self.assertTrue(v.detail["nearer_staff_signal"]
                        ["yields_to_glyph_owner"])

    def test_the_same_head_without_its_band_rows_is_refused(self):
        """The positive control in the same class: remove the contest and
        the geometry alone condemns it."""
        v = _build(CROP_2, drop_bands=True)
        self.assertEqual(v.reason, "belongs_to_a_nearer_staff")

    def test_a_contest_with_a_THIRD_staff_does_not_make_it_yield(self):
        k = sorted(FIVE)[0]
        filed = "staff/" + "/".join(k.split("/")[1:4])
        v = _build(k, bands=[[3.6, filed], [9.0, "staff/3/0/10"]])
        self.assertEqual(v.reason, "belongs_to_a_nearer_staff")


class TestItReachesTheFileAsADrop(unittest.TestCase):

    def test_the_refusal_is_counted_under_its_own_name(self):
        from tools.omr.tests.test_staged_notehead_precision import (
            _two_note_page)
        _, rep = E.to_musicxml(_two_note_page(
            flagged=True, reason="belongs_to_a_nearer_staff"))
        self.assertEqual(rep["notes_not_written"].get(
            "not_a_notehead:belongs_to_a_nearer_staff"), 1)
        self.assertEqual(rep["written"]["notes"]
                         + rep["notes_not_written_total"], 2)


# ─────────────────────────────────────────────────────────────────────────────
# The accidental follows its head; a key-signature marker is never in-bar.
# ─────────────────────────────────────────────────────────────────────────────

from tools.omr.tests.test_staged_accidental import (  # noqa: E402
    CELL, STAFF, _acc, _cell_unit, _decide, _head)


class TestTheAccidentalFollowsItsHead(unittest.TestCase):

    def _pair(self, reason):
        log = Log()
        _cell_unit(log)
        acc = _acc(log, 0, 100.0, 4.0)
        near = _head(log, 1, 106.0, 4.0)       # its own head
        far = _head(log, 2, 110.0, 5.0)        # a step below, same column
        _verdict(log, near, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, True, reason=reason)
        return acc, near, far, _decide(log).verdict(Q.ACCIDENTAL_OWNER, acc)

    def test_a_head_refused_for_a_nearer_staff_takes_its_accidental_along(self):
        _acc_, near, _far, v = self._pair("belongs_to_a_nearer_staff")
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "head_belongs_to_a_nearer_staff")
        self.assertEqual(v.detail["head"], near.to_key())

    def test_control_a_head_that_is_no_note_at_all_lets_it_re_pair(self):
        """The 2.7 behaviour, unchanged for the other refusals."""
        _acc_, _near, far, v = self._pair("clipped_fragment")
        self.assertEqual(v.value, far.to_key())

    def test_the_census_counts_it_and_stays_a_partition(self):
        from tools.omr.tests.test_staged_accidental import _durations, _full
        log = Log()
        _cell_unit(log)
        acc = _acc(log, 0, 100.0, 7.0)
        head = _head(log, 1, 106.0, 7.0)
        _durations(log, 1)
        _verdict(log, head, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, True,
                 reason="belongs_to_a_nearer_staff")
        xml, report = E.to_musicxml(_full(_decide(log)))
        c = report["accidental_reading"]
        self.assertEqual(c["head_belongs_to_a_nearer_staff"], 1)
        self.assertEqual(c["unaccounted"], 0)
        self.assertNotIn("<accidental>", xml)


def _marker(log, *, x, y_center, cell=0, shape="keyFlat"):
    log.observe(STAFF, Q.KEYSIG_MARKER, shape, reader=READERS.DETECTOR,
                frame=f"cell:{cell}", score=0.8, x=x, y_center=y_center,
                detector_class="accidentalFlat", detector_role="accidental")


class TestAKeySignatureMarkerIsNeverAnInBarAccidental(unittest.TestCase):
    """Crop 7: *"the glyph is a KEY-SIGNATURE flat"*."""

    def _header_flat(self, **marker):
        log = Log()
        _cell_unit(log)
        acc = _acc(log, 0, 100.0, 4.0, cls="accidentalFlat", alteration="b")
        _head(log, 1, 106.0, 4.0)
        box = log.rows(Q.GLYPH_BOX, acc)[-1].value
        if marker is not None:
            _marker(log, x=marker.get("x", box[1]),
                    y_center=marker.get("y", box[2] + box[4] / 2.0),
                    cell=marker.get("cell", 0))
        return acc, _decide(log).verdict(Q.ACCIDENTAL_OWNER, acc)

    def test_a_glyph_the_marker_run_filed_abstains_by_name(self):
        _a, v = self._header_flat()
        self.assertEqual(v.outcome, "abstained")
        self.assertEqual(v.reason, "is_a_key_signature_marker")
        self.assertEqual(v.detail["marker_role"], "accidental")

    def test_control_a_marker_ELSEWHERE_in_the_header_does_not_touch_it(self):
        _a, v = self._header_flat(x=40.0)
        self.assertEqual(v.reason, "immediately_right_same_position")

    def test_control_a_marker_in_ANOTHER_cell_frame_does_not_touch_it(self):
        _a, v = self._header_flat(cell=1)
        self.assertEqual(v.reason, "immediately_right_same_position")

    def _with_signature(self, *, cls, gap_spaces, kinds=("keyFlat",) * 3):
        """Three signature markers ending `gap_spaces` left of the glyph,
        plus a marker filed on the glyph itself (its class as detected)."""
        log = Log()
        _cell_unit(log)
        acc = _acc(log, 0, 200.0, 4.0, cls=cls,
                   alteration="natural" if "Natural" in cls else "b")
        _head(log, 1, 206.0, 4.0)
        box = log.rows(Q.GLYPH_BOX, acc)[-1].value
        last = box[1] - gap_spaces * 20.0            # SPACE = 20
        for i, kind in enumerate(kinds):
            log.observe(STAFF, Q.KEYSIG_MARKER, kind, reader=READERS.DETECTOR,
                        frame="cell:0", score=0.9,
                        x=last - (len(kinds) - 1 - i) * 20.0, y_center=40.0,
                        detector_class=kind, detector_role="key")
        log.observe(STAFF, Q.KEYSIG_MARKER, "keyFlat", reader=READERS.DETECTOR,
                    frame="cell:0", score=0.8, x=box[1],
                    y_center=box[2] + box[4] / 2.0,
                    detector_class="accidentalFlat",
                    detector_role="accidental")
        return _decide(log).verdict(Q.ACCIDENTAL_OWNER, acc)

    def test_a_flat_INSIDE_the_run_is_a_marker(self):
        v = self._with_signature(cls="accidentalFlat", gap_spaces=1.0)
        self.assertEqual(v.reason, "is_a_key_signature_marker")

    def test_crop_12_a_marker_PAST_the_runs_gap_is_not_one(self):
        """Measured on a fresh Litolff p3 gather: Violino I's in-bar natural
        (Sean's confirmed crop 12) was ALSO boxed `accidentalFlat` and that
        box admitted as a marker 2.8 spaces past the three-flat run. The key
        reader's own run ends at the gap; so does the exclusion."""
        v = self._with_signature(cls="accidentalFlat", gap_spaces=2.8)
        self.assertEqual(v.reason, "immediately_right_same_position")

    def test_crop_12_the_OTHER_class_on_the_same_ink_is_not_joined(self):
        """The natural box of the same ink, at the marker's own point: the
        marker's `detector_class` is the flat, so the natural is not it."""
        v = self._with_signature(cls="accidentalNatural", gap_spaces=1.0)
        self.assertEqual(v.reason, "immediately_right_same_position")

    def test_a_run_the_key_reader_REFUSED_as_mixed_excludes_nothing(self):
        v = self._with_signature(cls="accidentalFlat", gap_spaces=1.0,
                                 kinds=("keyFlat", "keyNatural", "keyFlat"))
        self.assertEqual(v.reason, "immediately_right_same_position")

    def test_the_census_counts_it_and_stays_a_partition(self):
        from tools.omr.tests.test_staged_accidental import _full
        log = Log()
        _cell_unit(log)
        acc = _acc(log, 0, 100.0, 4.0, cls="accidentalFlat", alteration="b")
        box = log.rows(Q.GLYPH_BOX, acc)[-1].value
        _marker(log, x=box[1], y_center=box[2] + box[4] / 2.0)
        _xml, report = E.to_musicxml(_full(_decide(log)))
        c = report["accidental_reading"]
        self.assertEqual(c["is_a_key_signature_marker"], 1)
        self.assertEqual(c["unaccounted"], 0)


if __name__ == "__main__":
    unittest.main()
