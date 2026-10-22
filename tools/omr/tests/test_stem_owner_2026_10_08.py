"""ROADMAP 2.58d -- the STEM witness in ownership (lane-stem-owner).

Sean, 2026-10-08, on two mark-group tiles: a head between the Trumpet and the
Timpani belongs to the Trumpet and *"the stem should make it obvious"*; a head
between the Oboe and the Clarinet belongs to the Clarinet (the 2.58c rule gave
the Oboe, off a ledger reading that counted ink that was not a ledger).

THE RULE, stated before any count (see `ownership._stem_owner`): a head
CLEARLY outside every candidate's lines whose stem leaves it `down` or `up`
and whose tip stands in ONE candidate's band (on the stem's side of the head)
belongs to that staff. Toward neither, toward both, a barline (`both`), no stem
(`none`), or a head on/beside the lines: silent. Where the stem and a ledger
witness name different staves the head ABSTAINS (`stem_disagrees`), and the
group rule takes the owner from the copy that did not abstain. A candidate the
written range calls IMPOSSIBLE is not named by a stem.

RUN RED FIRST: against the tree before this item there is no
`gather.measure_head_stem`, no `Q.HEAD_STEM_REACH`, no `STEM_OWNER_ENV`.
Every refusal has a positive control in the same class.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401 -- registers decisions
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.adjudicate import Term
from tools.omr.staged.adjudicators import ownership as OWN
from tools.omr.staged.record import Log, Outcome, Q, READERS, Verdict

# ----------------------------------------------------------------- the raster
SP = 16.0
W, H = 200, 400
HEAD = (90.0, 190.0, 112.0, 206.0)          # x0 y0 x1 y1 : 22 x 16 px, centre y 198


def _page(stem=None, bar=False, lines=True):
    """White page; `stem` = 'down' (3.5 sp, LEFT edge) | 'up' (RIGHT edge) |
    'down_right' (a down stem drawn on the wrong side); a filled head; optional
    barline through everything; staff lines across (they must not make a stem)."""
    img = np.zeros((H, W), bool)
    x0, y0, x1, y1 = (int(v) for v in HEAD)
    img[y0:y1, x0:x1] = True
    L = int(3.5 * SP)
    if stem == "down":
        img[y1 - 4:y1 + L, x0:x0 + 3] = True
    elif stem == "up":
        img[y0 - L:y0 + 4, x1 - 3:x1] = True
    elif stem == "down_right":
        img[y1 - 4:y1 + L, x1 - 3:x1] = True
    if bar:
        img[20:380, 150:153] = True
    if lines:
        for y in (30, 46, 62, 78, 94, 300, 316, 332, 348, 364):
            img[y:y + 2, 10:190] = True
    return img


class TestMeasure(unittest.TestCase):
    def test_a_down_stem_at_the_left_edge_reads_down(self):
        r = G.measure_head_stem(_page("down"), HEAD, SP)
        self.assertEqual(r["direction"], "down", r)
        self.assertGreaterEqual(r["down_ext"], 3.0)
        self.assertGreater(r["down_tip_y"], HEAD[3] + 3 * SP)
        self.assertIsNone(r["up_tip_y"])

    def test_an_up_stem_at_the_right_edge_reads_up(self):
        r = G.measure_head_stem(_page("up"), HEAD, SP)
        self.assertEqual(r["direction"], "up", r)
        self.assertLess(r["up_tip_y"], HEAD[1] - 3 * SP)

    def test_no_stem_reads_none_even_with_staff_lines_across(self):
        """CONTROL that can fail: horizontal staff lines through the stem's
        columns are ink rows, but a space apart -- not a run."""
        r = G.measure_head_stem(_page(None), HEAD, SP)
        self.assertEqual(r["direction"], "none", r)

    def test_right_and_down_does_not_exist(self):
        """CLAUDE.md §10 (96 of 96 against print): a down stem stands at the
        LEFT; ink hanging from the right edge is not read as this head's."""
        r = G.measure_head_stem(_page("down_right"), HEAD, SP)
        self.assertNotEqual(r["direction"], "down", r)

    def test_a_barline_through_the_head_claims_nothing(self):
        img = _page(None, bar=False)
        img[20:380, 92:95] = True            # a barline touching the head's left edge
        r = G.measure_head_stem(img, HEAD, SP)
        self.assertEqual(r["direction"], "both", r)

    def test_a_short_stub_is_not_a_stem(self):
        img = _page(None)
        img[int(HEAD[3]) - 4:int(HEAD[3]) + int(0.5 * SP), 90:93] = True
        r = G.measure_head_stem(img, HEAD, SP)
        self.assertEqual(r["direction"], "none", r)


# ---------------------------------------------------------------- the decision
A_KEY, B_KEY = "staff/0/0/0", "staff/0/0/1"
LINES_A = [200.0 + SP * i for i in range(5)]           # 200..264
LINES_B = [344.0 + SP * i for i in range(5)]           # 344..408 : 5 sp gap
HEAD_CY = 318.4                                        # 1.6 sp above B, 3.4 sp below A


def _contest(stem=None, *, cy=HEAD_CY, note_first=None, flag="1", extra=None):
    """A glyph filed on B, contested by A (A is FARTHER). `stem` = (direction,
    tip_y) or None; `note_first` = candidate key the ledger witness names."""
    log = Log()
    for key, lines in ((A_KEY, LINES_A), (B_KEY, LINES_B)):
        s = R.Subject.from_key(key)
        log.observe(s, Q.STAFF_LINES, lines, reader="cv_lines", frame="page")
        log.observe(s, Q.STAFF_SPACING, SP, reader="cv_lines", frame="page")
    g = R.glyph(0, 0, 1, 0, 0)

    def dist(lines):
        return max(min(lines) - cy, cy - max(lines)) / SP

    log.observe(g, Q.GLYPH_BAND_DISTANCE, dist(LINES_B), reader="geometry", frame="page",
                candidate=B_KEY, own=True, position_in_candidate=-3.0)
    log.observe(g, Q.GLYPH_BAND_DISTANCE, dist(LINES_A), reader="geometry", frame="page",
                candidate=A_KEY, own=False, position_in_candidate=13.0)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlackInSpace", 0, 0, 1, 1), reader="detector",
                frame="cell:0", score=0.9, category="notehead",
                bbox_page_px=[90.0, cy - 8.0, 112.0, cy + 8.0], y_center_page=cy)
    if stem is not None:
        way, tip = stem
        log.observe(g, Q.HEAD_STEM_REACH, way, reader=READERS.CV_HEAD_STEM_REACH, frame="page",
                    head_box_page=[90.0, cy - 8.0, 112.0, cy + 8.0], sp=SP,
                    down_ext=(abs(tip - cy) / SP if way == "down" else 0.0),
                    up_ext=(abs(tip - cy) / SP if way == "up" else 0.0),
                    down_tip_y=(tip if way == "down" else None),
                    up_tip_y=(tip if way == "up" else None))
    if note_first is not None:
        log.observe(g, Q.FAR_HEAD_OWNER_LEDGER, -4 if note_first == B_KEY else 12,
                    reader="ledger_owner_note_first", frame="cell:0", candidate=note_first,
                    ledger_reason="x", how="note_first")
        other = A_KEY if note_first == B_KEY else B_KEY
        log.abstain(g, Q.FAR_HEAD_OWNER_LEDGER, reader="ledger_owner_note_first", frame="cell:0",
                    reason="ledger_not_read", candidate=other, unread=False, ledger_reason="x")
    log.freeze()
    with mock.patch.dict(os.environ, {OWN.STEM_OWNER_ENV: flag}):
        return adjudicate.adjudicate_one(log, adjudicate.REGISTRY[Q.GLYPH_OWNER], g)


def _res(v):
    return (v.outcome, v.value, v.reason)


class TestTheStemWitness(unittest.TestCase):
    UP_TO_A = ("up", HEAD_CY - 3.5 * SP)            # tip 262.4: inside A's lowest space
    DOWN_TO_B = ("down", HEAD_CY + 3.5 * SP)         # tip 374.4: inside B's lines

    def test_the_witness_is_declared_and_default_on(self):
        spec = adjudicate.REGISTRY[Q.GLYPH_OWNER]
        self.assertIn(Q.HEAD_STEM_REACH, spec.wants)
        self.assertIn("stem_toward_staff", spec.reasons)
        self.assertIn("stem_disagrees", spec.reasons)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(OWN.STEM_OWNER_ENV, None)
            self.assertTrue(OWN.stem_owner_enabled())    # default ON since 2026-10-08
            os.environ[OWN.STEM_OWNER_ENV] = "0"
            self.assertFalse(OWN.stem_owner_enabled())

    def test_off_the_nearer_staff_wins_as_before(self):
        """CONTROL that can fail: the same stem, flag OFF, is not read."""
        v = _contest(self.UP_TO_A, flag="0")
        self.assertEqual(_res(v), (Outcome.DECIDED, B_KEY, "distance"))

    def test_a_stem_toward_the_farther_staff_gives_it_the_head(self):
        """THE TILE: nearness says B (1.6 sp), the up stem runs into A's band."""
        v = _contest(self.UP_TO_A)
        self.assertEqual(_res(v), (Outcome.DECIDED, A_KEY, "stem_toward_staff"))

    def test_a_stem_toward_the_nearer_staff_keeps_it(self):
        v = _contest(self.DOWN_TO_B)
        self.assertEqual(_res(v), (Outcome.DECIDED, B_KEY, "stem_toward_staff"))

    def test_toward_neither_is_silent(self):
        """An up stem too short to reach A's band (tip 5 sp below A): silent --
        distance decides."""
        v = _contest(("up", HEAD_CY - 1.0 * SP))
        self.assertEqual(_res(v), (Outcome.DECIDED, B_KEY, "distance"))

    def test_both_and_none_are_silent(self):
        self.assertEqual(_res(_contest(("both", None))), (Outcome.DECIDED, B_KEY, "distance"))
        self.assertEqual(_res(_contest(("none", None))), (Outcome.DECIDED, B_KEY, "distance"))

    def test_a_head_on_the_lines_is_not_read_by_stem(self):
        """The in-staff control: a head on B's own top line (cy 344) is
        `staff_band`'s; an up stem toward A must not move it."""
        v = _contest(("up", 344.0 - 3.5 * SP), cy=344.0)
        self.assertNotEqual(v.reason, "stem_toward_staff")
        self.assertNotEqual(v.value, A_KEY)

    def test_a_head_in_the_first_space_is_not_read_by_stem(self):
        v = _contest(("up", 336.0 - 3.5 * SP), cy=336.0)         # 0.5 sp above B's top line
        self.assertNotEqual(v.reason, "stem_toward_staff")

    def test_a_ledger_witness_that_agrees_is_kept_and_says_so(self):
        v = _contest(self.UP_TO_A, note_first=A_KEY)
        self.assertEqual(_res(v), (Outcome.DECIDED, A_KEY, "ledger_note_first"))
        self.assertTrue(v.detail.get("stem_agrees"))

    def test_a_ledger_witness_that_disagrees_makes_the_head_abstain(self):
        """The tile-7 shape: the ledger reading names B, the stem names A. Neither
        is trusted alone (rule 8) -- the head abstains and says why."""
        v = _contest(self.UP_TO_A, note_first=B_KEY)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "stem_disagrees")
        self.assertEqual(v.detail["stem_owner"], A_KEY)
        self.assertEqual(v.detail["ledger_owner"], B_KEY)

    def test_without_the_stem_the_ledger_witness_decides_as_before(self):
        """CONTROL that can fail: same ledger rows, no stem row -> note_first."""
        v = _contest(None, note_first=B_KEY)
        self.assertEqual(_res(v), (Outcome.DECIDED, B_KEY, "ledger_note_first"))

    def test_a_staff_the_range_calls_impossible_is_not_named_by_a_stem(self):
        def veto(ev, cand_key, row):
            return Term("range_impossible", OWN.W_RANGE_IMPOSSIBLE, (row.id,)) if cand_key == A_KEY else None
        with mock.patch.object(OWN, "_range_veto", veto):
            v = _contest(self.UP_TO_A)
        self.assertNotEqual(v.reason, "stem_toward_staff")
        self.assertEqual(v.value, B_KEY)


# ------------------------------------------------------------------ the group
BOX = (0, 0, 20, 20)


def _group(placements):
    log = Log()
    subs = []
    for i, (staff, cell) in enumerate(placements):
        sub = R.glyph(0, 0, staff, cell, i)
        log.observe(sub, Q.GLYPH_BOX, ("x", 0, 0, 1, 1), reader=READERS.DETECTOR, frame="cell:0",
                    score=0.9 - 0.1 * i, category="notehead",
                    bbox_page_px=[BOX[0] + i, BOX[1], BOX[2] + i, BOX[3]])
        subs.append(sub)
    assert G.mark_groups_from_log(log) == 1
    return log, subs


def _own(log, sub, value, reason, outcome=Outcome.DECIDED):
    return log.record(Verdict(id=log._next_id("vrd"), subject=sub, quantity=Q.GLYPH_OWNER,
                              outcome=outcome, value=value, decider="t", reason=reason))


class TestTheGroup(unittest.TestCase):
    def test_the_copy_that_abstained_on_the_clash_takes_the_stem_copys_owner(self):
        """Tile 7: the Oboe-cell copy abstained (`stem_disagrees`), the
        Clarinet-cell copy decided on the stem -> the mark is the Clarinet's."""
        log, (oboe_copy, clar_copy) = _group([(1, 4), (2, 4)])
        _own(log, oboe_copy, None, "stem_disagrees", Outcome.ABSTAINED)
        _own(log, clar_copy, "staff/0/0/2", "stem_toward_staff")
        census = OWN.reconcile_group_owners(log)
        self.assertEqual(census.get("adopted_after_abstaining"), 1, census)
        v = log.verdict(Q.GLYPH_OWNER, oboe_copy)
        self.assertEqual((v.outcome, v.value, v.reason), (Outcome.DECIDED, "staff/0/0/2", "group_owner"))

    def test_two_copies_that_both_abstained_stay_unowned(self):
        """CONTROL: nothing decided -> nothing is invented."""
        log, (a, b) = _group([(1, 4), (2, 4)])
        _own(log, a, None, "stem_disagrees", Outcome.ABSTAINED)
        _own(log, b, None, "stem_disagrees", Outcome.ABSTAINED)
        census = OWN.reconcile_group_owners(log)
        self.assertEqual(census.get("unowned_abstained"), 1, census)
        self.assertEqual(log.verdict(Q.GLYPH_OWNER, a).outcome, Outcome.ABSTAINED)


if __name__ == "__main__":
    unittest.main()
