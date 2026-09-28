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


def _build(head_key, *, extra_ledgers=(), drop_bands=False, bands=None):
    """A log holding exactly what the record held for this head."""
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


class TestAKeptRungIsSeansException(unittest.TestCase):

    def test_a_kept_rung_toward_the_filed_staff_keeps_the_head(self):
        k = sorted(FIVE)[0]
        rung = dict(_rung_between_head_and_filed(k), refused=False,
                    reason=None)
        v = _build(k, extra_ledgers=[rung])
        self.assertIs(v.value, False)
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
