"""ROADMAP 2.6c, second half — the ledger lines name the owner, as a HARD rule.

Sean, 2026-09-28 (DECISIONS): *"Nearer to the staff is not always going to be
right but ledger lines will be. If it is not working out that way right now
then the tests are off."* The ledger lines are AUTHORITATIVE for which staff a
far note belongs to; nearness is only a hint and never overrides them; where
a ledger answer disagrees with the print the RUNG FINDING is wrong, not the
rule; a far note with no rungs found either way is a reading gap and
ABSTAINS.

Three things are pinned here, on the six heads Sean adjudicated against the
print in 2.7b.8 (`fixtures/ledger_direction_2_6c.json`, cut from the two 27b
arm records by `benchmarks/omr-owner-domain-2026-09/extract_ledger_fixture_
2_6c.py`) and on synthetic contests:

1. ONE helper (`ownership.ledger_direction`) answers "which staff do these
   rungs point to" for BOTH `glyph_owner` and 2.7b's
   `belongs_to_a_nearer_staff`, so the two cannot disagree.
2. The rung-crediting bugs: #4 `glyph/10/1/2/12/6` and #22 `glyph/4/1/2/8/31`
   were kept on the far staff by ONE rung that is a CHORD-MATE's own ledger
   (the near staff's second ledger, beyond the head) with the far staff's own
   inner rungs all absent; #10 `glyph/8/0/6/12/7` (the `s` of *sempre*) was
   kept by two real rungs of the filed staff that END 1.37 spaces short of
   it — they are the rungs of the real note standing on the second one.
3. `glyph_owner` decides `ledger_direction` OUTRIGHT (no additive weight can
   outvote it) and abstains `far_no_rungs` where every candidate needs two or
   more rungs and none was found toward any; export COUNTS such a head under
   `owner_not_read` and never writes it at a guess.

⚠️ RUN RED FIRST against `8100c9ff` (the unrepaired tree): the #4 / #10 /
lone-rung / reach refusals, the three `glyph_owner` real-head flips (#1, #14,
brk-02), the hard-gate pin, `far_no_rungs` and `owner_not_read` fail there;
the positive controls (brk-02 / #1 / #14 kept without a contest, the near
miss, #22's contest, the complete ladder) pass on both trees.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import export as SX
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS, Subject

FIXTURE = json.loads((Path(__file__).parent / "fixtures"
                      / "ledger_direction_2_6c.json").read_text())
HEADS = {h["subject"]: h for h in FIXTURE["heads"]}

H1 = "glyph/16/1/7/14/0"      # Litolff #1  — Sean: the FILED staff (G)
H4 = "glyph/10/1/2/12/6"      # Litolff #4  — Sean: the NEARER staff (O)
H10 = "glyph/8/0/6/12/7"      # Litolff #10 — Sean: not a note (N)
H14 = "glyph/12/0/11/14/1"    # Litolff #14 — Sean: the FILED staff (G)
B02 = "glyph/9/0/11/0/1"      # Breitkopf #18 (brk-02) — the FILED staff (G)
B22 = "glyph/4/1/2/8/31"      # Breitkopf #22 (brk-06) — the NEARER staff (O)


def _staff_of(key: str) -> str:
    return "staff/" + "/".join(key.split("/")[1:4])


def _verdict(log, subject, quantity, value, *, reason="fixture",
             outcome=Outcome.DECIDED):
    return log.record(R.Verdict(
        id=log._next_id("vrd"), subject=subject, quantity=quantity,
        outcome=outcome, value=value, decider="t", reason=reason))


def _build(head_key, *, bands=True):
    """A log holding exactly what the arm record held for this head, its
    staves and the ledger boxes of its cell and the same-index cells of every
    staff near it — then `notehead_is_not_a_notehead` and `glyph_owner`."""
    h = HEADS[head_key]
    g = Subject.from_key(head_key)
    log = Log()
    for key, st in h["staves"].items():
        s = Subject.from_key(key)
        log.observe(s, Q.STAFF_LINES, list(st["staff_lines"]),
                    reader=READERS.GEOMETRY, frame="page")
        log.observe(s, Q.STAFF_SPACING, st["staff_spacing"],
                    reader=READERS.GEOMETRY, frame="page")
    cell = Subject.from_key(h["cell"]["key"])
    css = h["cell"]["cell_staff_space"]
    log.observe(cell, Q.CELL_STAFF_SPACE, css[0], reader=READERS.GEOMETRY,
                frame=f"cell:{g.cell}", **(css[1] or {}))
    log.observe(cell, Q.CELL_BOX, h["cell"]["cell_box"],
                reader=READERS.GEOMETRY, frame=f"cell:{g.cell}")
    gb = h["glyph_box"]
    log.observe(g, Q.GLYPH_BOX, tuple(gb["value"]), reader=READERS.DETECTOR,
                frame=f"cell:{g.cell}", score=0.9, **gb["detail"])
    log.observe(g, Q.NOTEHEAD_CLASS, h["notehead_class"],
                reader=READERS.DETECTOR, frame=f"cell:{g.cell}", score=0.9)
    if bands:
        for value, detail in h["band_rows"]:
            log.observe(g, Q.GLYPH_BAND_DISTANCE, value,
                        reader=READERS.GEOMETRY, frame="page", **detail)
        for value, detail in h["ladder_rows"]:
            log.observe(g, Q.GLYPH_LADDER, value, reader=READERS.DETECTOR,
                        frame="page", **detail)
    for L in h["ledgers"]:
        ls = Subject.from_key(L["subject"])
        log.observe(ls, Q.GLYPH_BOX, tuple(L["value"]),
                    reader=READERS.DETECTOR, frame=f"cell:{ls.cell}",
                    score=0.7, category="ledger",
                    bbox_page_px=L["bbox_page_px"])
    log.freeze()
    for key, st in h["staves"].items():
        s = Subject.from_key(key)
        if st["instrument"] is not None:
            _verdict(log, s, Q.INSTRUMENT, st["instrument"])
        if st["clef"] is not None:
            _verdict(log, s, Q.CLEF, st["clef"])
    for L in h["ledgers"]:
        if L["verdict"] is None:
            continue
        outcome, value, reason = L["verdict"]
        _verdict(log, Subject.from_key(L["subject"]),
                 Q.LEDGER_IS_NOT_A_LEDGER, value, reason=reason,
                 outcome=(Outcome.DECIDED if outcome == "decided"
                          else Outcome.ABSTAINED))
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.GLYPH_OWNER))
    return log, g


class TestTheFixtureIsWhatSeanAdjudicated(unittest.TestCase):

    def test_six_heads_and_what_the_arm_record_did_with_them(self):
        self.assertEqual(len(HEADS), 6)
        self.assertEqual({k: HEADS[k]["sean"] for k in HEADS}, {
            H1: "belongs_to_filed_staff", H4: "belongs_to_the_nearer_staff",
            H10: "not_a_note", H14: "belongs_to_filed_staff",
            B02: "belongs_to_filed_staff", B22: "belongs_to_the_nearer_staff"})
        # the finding: all six KEPT by 2.7b's rung exception on the arm
        for k in HEADS:
            self.assertEqual(
                HEADS[k]["on_the_arm_record"]["notehead_is_not_a_notehead"],
                ["decided", False, "notehead"], k)
        # and the three contests Sean's G contradicts, as the arm decided them
        self.assertEqual(HEADS[H1]["on_the_arm_record"]["glyph_owner"],
                         ["decided", "staff/16/1/8", "distance"])
        self.assertEqual(HEADS[H14]["on_the_arm_record"]["glyph_owner"],
                         ["decided", "staff/12/0/10", "ladder"])
        self.assertEqual(HEADS[B02]["on_the_arm_record"]["glyph_owner"],
                         ["abstained", None, "tied"])


class TestTheRungCreditingBugs(unittest.TestCase):
    """2.7b's `belongs_to_a_nearer_staff`, now asking the ONE helper."""

    def test_4_a_chord_mates_ledger_no_longer_keeps_it(self):
        """RED on 8100c9ff: kept by `glyph/10/1/2/12/4`, the ledger the
        chord-mate `glyph/10/1/2/12/1` stands on (the NEAR staff's 2nd rung,
        2.64 spaces off the filed staff — off its grid — with the filed
        staff's rungs 1 and 2 both absent). GREEN: refused, Sean's O."""
        log, g = _build(H4)
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "belongs_to_a_nearer_staff")
        led = v.detail["nearer_staff_signal"]["ledger"]
        self.assertIsNone(led["winner"])
        filed = led["sides"]["staff/10/1/2"]
        self.assertEqual(filed["expected"], 3)
        self.assertEqual(filed["found"], 1)       # the chord-mate's line
        self.assertFalse(filed["points"])

    def test_10_rungs_that_end_short_of_the_head_do_not_keep_it(self):
        """RED on 8100c9ff: kept by `glyph/8/0/6/12/2` — a real rung of the
        filed staff, but the ladder (rungs 1 and 2) ENDS 1.37 spaces short of
        this 'head' (the `s` of *sempre*): those are the rungs of the real
        note standing on rung 2. GREEN: not credited, so it is dropped —
        Sean's N (not a note) is not written either way."""
        log, g = _build(H10)
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)
        self.assertIs(v.value, True)
        filed = v.detail["nearer_staff_signal"]["ledger"]["sides"][
            "staff/8/0/6"]
        self.assertEqual(filed["found"], 2)
        self.assertFalse(filed["reach"])
        self.assertFalse(filed["points"])

    def test_22_is_not_kept_by_its_chord_mates_rung_and_yields(self):
        """Breitkopf #22: the same chord-mate shape (the near staff's 2nd
        ledger, 4.49 spaces off the filed staff, is the only 'rung' toward
        it). It is contested, so 2.7b YIELDS to `glyph_owner` — which never
        credited that rung and gives it to the near staff on its own complete
        ladder (Sean's O). RED on 8100c9ff: the rung exception answered first
        and the yield was never recorded."""
        log, g = _build(B22)
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)
        sig = v.detail["nearer_staff_signal"]
        self.assertIsNone(sig["ledger"]["winner"])
        self.assertTrue(sig["yields_to_glyph_owner"])
        own = log.verdict(Q.GLYPH_OWNER, g)
        self.assertEqual(own.value, "staff/4/1/3")


class TestTheLadderStillKeepsARealFarNote(unittest.TestCase):
    """POSITIVE CONTROLS in the same class — Sean's three G heads, with the
    contest REMOVED so the rung exception alone must keep them (a refusal
    battery passes by refusing everything)."""

    def test_brk02_one_missed_rung_still_names_the_filed_staff(self):
        """Rung 1 above the filed staff was never boxed; rung 2 and the
        head's own line were. One miss is tolerated; the ladder reaches."""
        log, g = _build(B02, bands=False)
        v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)
        self.assertIs(v.value, False)
        self.assertEqual(v.detail["nearer_staff_signal"]["ledger"]["winner"],
                         "staff/9/0/11")

    def test_1_and_14_are_kept(self):
        for k in (H1, H14):
            with self.subTest(head=k):
                log, g = _build(k, bands=False)
                v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)
                self.assertIs(v.value, False)
                self.assertEqual(
                    v.detail["nearer_staff_signal"]["ledger"]["winner"],
                    _staff_of(k))


class TestGlyphOwnerTakesTheLedgerAsAHardRule(unittest.TestCase):
    """The contests Sean's G verdicts contradict, rebuilt from the arm rows."""

    def test_1_the_ladder_beats_distance(self):
        """RED on 8100c9ff: `distance` -> staff 8 (2.27 spaces vs 3.13). Two
        rungs run from staff 7 to the head, none toward staff 8."""
        log, g = _build(H1)
        v = log.verdict(Q.GLYPH_OWNER, g)
        self.assertEqual(v.value, "staff/16/1/7")
        self.assertEqual(v.reason, "ledger_direction")

    def test_14_the_heads_own_line_is_no_ones_rung(self):
        """RED on 8100c9ff: `ladder` -> staff 10, both ladders "complete" —
        but staff 10's one rung is the head's own line, which joins it to
        neither staff; staff 11 has two more under it."""
        log, g = _build(H14)
        v = log.verdict(Q.GLYPH_OWNER, g)
        self.assertEqual(v.value, "staff/12/0/11")
        self.assertEqual(v.reason, "ledger_direction")

    def test_brk02_a_tie_is_not_a_tie_when_the_rungs_speak(self):
        """RED on 8100c9ff: abstained `tied`."""
        log, g = _build(B02)
        v = log.verdict(Q.GLYPH_OWNER, g)
        self.assertEqual(v.value, "staff/9/0/11")
        self.assertEqual(v.reason, "ledger_direction")


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic contests: the hard gate, `far_no_rungs`, and the near miss.
# ─────────────────────────────────────────────────────────────────────────────

UP = R.staff(0, 0, 0)
DOWN = R.staff(0, 0, 1)
G = R.glyph(0, 0, 0, 0, 0)
UP_LINES = [100.0, 110.0, 120.0, 130.0, 140.0]
DOWN_LINES = [200.0, 210.0, 220.0, 230.0, 240.0]
SP = 10.0

#: A range the head's pitch on DOWN (above its top line, treble) cannot be
#: in, so the range veto fires on DOWN.
LOW_ONLY = {"name": "Contrabass", "family": "strings",
            "expected_clef": "treble", "written_range": [28, 60],
            "unpitched": False}


def _synthetic(head_y, *, rungs=(), up_hairpin_y=None, veto_down=False):
    """A notehead between UP (bottom line 140) and DOWN (top line 200),
    detected in both cells, with ledger boxes at `rungs` (page y)."""
    log = Log()
    for st, lines in ((UP, UP_LINES), (DOWN, DOWN_LINES)):
        log.observe(st, Q.STAFF_LINES, list(lines), reader=READERS.GEOMETRY,
                    frame="page")
        log.observe(st, Q.STAFF_SPACING, SP, reader=READERS.GEOMETRY,
                    frame="page")
    log.observe(G, Q.GLYPH_BOX, ("noteheadBlackInSpace", 0, 0, 10, 10),
                reader=READERS.DETECTOR, frame="cell:0", score=0.8,
                bbox_page_px=[500.0, head_y - 5.0, 512.0, head_y + 5.0],
                x_center_page=506.0, y_center_page=head_y)
    for st, lines in ((UP, UP_LINES), (DOWN, DOWN_LINES)):
        top, bottom = min(lines), max(lines)
        gap = (top - head_y) if head_y < top else (head_y - bottom)
        log.observe(G, Q.GLYPH_BAND_DISTANCE, max(0.0, gap / SP),
                    reader=READERS.GEOMETRY, frame="page",
                    candidate=st.to_key(), own=(st == UP),
                    position_in_candidate=(head_y - top) / (SP / 2))
    for i, y in enumerate(rungs):
        log.observe(R.glyph(0, 0, 0, 0, 50 + i), Q.GLYPH_BOX,
                    ("ledgerLine", 0, 0, 14, 2), reader=READERS.DETECTOR,
                    frame="cell:0", score=0.7, category="ledger",
                    bbox_page_px=[497.0, y - 1.0, 515.0, y + 1.0])
    if up_hairpin_y is not None:
        log.observe(R.glyph(0, 0, 0, 3, 0), Q.WEDGE_BOX, "diminuendo",
                    reader=READERS.CV_HAIRPINS, frame="page",
                    bbox_page_px=[480.0, up_hairpin_y - 4, 560.0,
                                  up_hairpin_y + 4],
                    x_center_page=520.0, y_center_page=up_hairpin_y)
    log.freeze()
    if veto_down:
        _verdict(log, DOWN, Q.INSTRUMENT, LOW_ONLY)
        _verdict(log, DOWN, Q.CLEF, "treble")
    adjudicate._ensure_decisions()
    return adjudicate.adjudicate_one(log, adjudicate.REGISTRY[Q.GLYPH_OWNER],
                                     G)


class TestTheHardGate(unittest.TestCase):

    def test_no_additive_weight_can_outvote_the_ledger(self):
        """RED on 8100c9ff. The head (176) stands 2.4 spaces above DOWN on
        DOWN's second ledger with DOWN's first ledger found (190), and 3.6
        spaces below UP with no rung toward UP. A hairpin filed under UP
        below the head (+7.0) plus a range veto on DOWN (-6.0) out-scored the
        additive `ledger_direction` (+8.0) there; the ledger now decides
        before any weight is summed."""
        v = _synthetic(176.0, rungs=(190.0, 180.0), up_hairpin_y=185.0,
                       veto_down=True)
        self.assertEqual(v.value, DOWN.to_key())
        self.assertEqual(v.reason, "ledger_direction")

    def test_POSITIVE_CONTROL_the_hairpin_still_speaks_where_the_ledger_is_silent(self):
        """The same hairpin with no rungs and the head near UP (0.9 spaces,
        one rung needed and none found): the ledger is silent, the contest
        is a near miss, and the hairpin decides as 2.6c's first half built
        it."""
        v = _synthetic(149.0, up_hairpin_y=185.0)
        self.assertEqual(v.value, UP.to_key())
        self.assertEqual(v.reason, "hairpin_separates")


class TestAFarNoteWithNoRungsAbstains(unittest.TestCase):

    def test_far_from_both_no_rungs_either_way_abstains(self):
        """RED on 8100c9ff (`distance`). 2.5 and 3.5 spaces: each needs two
        or more rungs, none was found toward either — a reading gap."""
        v = _synthetic(165.0)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "far_no_rungs")

    def test_the_heads_own_line_alone_is_still_no_rungs(self):
        v = _synthetic(170.0, rungs=(170.0,))
        self.assertEqual(v.reason, "far_no_rungs")

    def test_POSITIVE_CONTROL_a_near_miss_keeps_todays_tiers(self):
        """0.9 spaces under UP needs ONE rung: a hint, not a claim, so the
        contest is NOT abstained and distance still breaks it."""
        v = _synthetic(149.0)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, UP.to_key())
        self.assertEqual(v.reason, "distance")

    def test_POSITIVE_CONTROL_a_ladder_toward_one_decides(self):
        """Far from both, rungs 1-2 under UP found and reaching the head."""
        v = _synthetic(166.0, rungs=(150.0, 160.0))
        self.assertEqual(v.value, UP.to_key())
        self.assertEqual(v.reason, "ledger_direction")

    def test_CONTROL_a_lone_rung_is_not_a_ladder(self):
        """#4's shape, synthetic: one rung toward UP a space short of the
        head, UP's rungs 1 and 2 missing — not a ladder, so the ledger stays
        silent and (one rung found, so not `far_no_rungs`) distance decides.
        Passes on both trees; #4 itself is the RED case."""
        v = _synthetic(175.0, rungs=(165.0,))
        self.assertEqual(v.value, DOWN.to_key())
        self.assertEqual(v.reason, "distance")


class TestExportCountsAnUnreadOwner(unittest.TestCase):

    def test_an_abstained_far_no_rungs_owner_is_counted_not_written(self):
        """RED on 8100c9ff: an abstained owner was written on its filed
        staff (`is_relocated_copy(None)` is False) — a guess. Now it is
        dropped and counted under `owner_not_read`; the balance holds."""
        from tools.omr.tests.test_staged_notehead_precision import (
            _two_note_page, _vrd)
        page = _two_note_page(flagged=False)
        page["record"]["verdicts"].append(
            _vrd(960, "glyph/0/0/0/0/0", Q.GLYPH_OWNER, None,
                 outcome="abstained", reason="far_no_rungs"))
        _, rep = SX.to_musicxml(page)
        self.assertEqual(rep["notes_not_written"].get("owner_not_read"), 1)
        self.assertEqual(rep["written"]["notes"]
                         + rep["notes_not_written_total"], 2)

    def test_POSITIVE_CONTROL_a_decided_own_staff_owner_is_written(self):
        from tools.omr.tests.test_staged_notehead_precision import (
            _two_note_page, _vrd)
        page = _two_note_page(flagged=False)
        page["record"]["verdicts"].append(
            _vrd(960, "glyph/0/0/0/0/0", Q.GLYPH_OWNER, "staff/0/0/0",
                 reason="ledger_direction"))
        _, rep = SX.to_musicxml(page)
        self.assertEqual(rep["written"]["notes"], 2)
        self.assertNotIn("owner_not_read", rep["notes_not_written"])


if __name__ == "__main__":
    unittest.main()
