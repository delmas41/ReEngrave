"""ROADMAP 2.6f — a rung that is another candidate's own ledger structure
never counts toward a farther one.

FINDINGS §2.6c.3 read all nine Breitkopf `ledger_direction`/`range_veto`
reversals §2.6c.2 left unadjudicated, by eye, against the print: seven share
one shape -- the note stands right at its NEAR candidate's own first ledger,
and a SECOND real `ledgerLine` box exactly one more space out (a chord-mate's
own ledger, or the same shape §2.7b's docstring already named for its own
#4/#22) gets reached by the FAR candidate's own longer walk too, inside
`RUNG_GRID_TOLERANCE_SPACES` (0.5 sp, loose by construction). Because
`ledger_direction` is a HARD gate, that one coincidental match decided the
whole contest.

⚠️ RUN RED FIRST, against the tree BEFORE this lane's `ownership.py` edit
(`42cb4792`, the 2.6c.3 evidence-lane merge): all seven
`test_the_seven_2_6c3_contests_revert_to_base` subtests fail there (the fix
does not exist yet), and the synthetic unit tests of
`_shared_own_structure_exclusions` below have nothing to import. The
positive controls -- `test_staged_ledger_direction.py`'s existing 47 tests,
Litolff #1/#14 and Breitkopf brk-02/#22 among them -- ALREADY pass on
`42cb4792` and must still pass here (this file adds an import-only smoke
check for #14, the sharpest one: a COMPLETE 3-of-3 ladder from the TRUE far
staff whose own outermost rung sits 0.08 px from a different, nearer
candidate's own-line -- the exact shape this fix's guard exists to leave
alone).
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS, Subject
from tools.omr.staged.adjudicators import ownership as O

FIXTURE = json.loads((Path(__file__).parent / "fixtures"
                      / "shared_structure_2_6f.json").read_text())
HEADS = {h["subject"]: h for h in FIXTURE["heads"]}


def _build(head_key):
    """The SAME harness `test_staged_ledger_direction.py._build` uses,
    trimmed to what `glyph_owner` alone needs (no human-box / instrument /
    clef rows -- none of the seven contests carries a range veto)."""
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
    for value, detail in h["band_rows"]:
        log.observe(g, Q.GLYPH_BAND_DISTANCE, value,
                    reader=READERS.GEOMETRY, frame="page", **detail)
    for L in h["ledgers"]:
        ls = Subject.from_key(L["subject"])
        log.observe(ls, Q.GLYPH_BOX, tuple(L["value"]),
                    reader=READERS.DETECTOR, frame=f"cell:{ls.cell}",
                    score=0.7, category="ledger",
                    bbox_page_px=L["bbox_page_px"])
    log.freeze()
    for L in h["ledgers"]:
        if L["verdict"] is None:
            continue
        outcome, value, reason = L["verdict"]
        log.record(R.Verdict(
            id=log._next_id("vrd"), subject=Subject.from_key(L["subject"]),
            quantity=Q.LEDGER_IS_NOT_A_LEDGER, value=value, decider="t",
            reason=reason,
            outcome=(Outcome.DECIDED if outcome == "decided"
                     else Outcome.ABSTAINED)))
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.GLYPH_OWNER,))
    return log, g


class TestTheSevenContestsRevertToBase(unittest.TestCase):
    """RED on `42cb4792`: all seven decide `ledger_direction` onto the FAR
    (wrong) staff, credited by a rung that is really the near staff's own
    second ledger, one space beyond its already-found own line."""

    def test_the_seven_2_6c3_contests_revert_to_base(self):
        self.assertEqual(len(HEADS), 7)
        for key, h in HEADS.items():
            with self.subTest(head=key):
                log, g = _build(key)
                v = log.verdict(Q.GLYPH_OWNER, g)
                self.assertEqual(v.outcome, Outcome.DECIDED, key)
                self.assertEqual(v.value, h["correct_staff"], key)
                # not `range_veto` (2.6f touches none of that term) and not
                # a guess left over from the hard gate's old miscredit
                self.assertNotEqual(v.reason, "range_veto", key)

    def test_one_contest_in_detail_the_far_rung_is_discounted(self):
        """`glyph/10/1/0/1/1`: staff/10/1/0 (far, wrong on `42cb4792`) no
        longer `points` once its one `toward` rung is recognised as
        staff/10/1/1's own second ledger -- and the record says so."""
        log, g = _build("glyph/10/1/0/1/1")
        v = log.verdict(Q.GLYPH_OWNER, g)
        self.assertEqual(v.value, "staff/10/1/1")
        led = (v.detail or {}).get("ledger") or {}
        far = led.get("sides", {}).get("staff/10/1/0")
        self.assertIsNotNone(far)
        self.assertFalse(far["points"])
        self.assertIn("discounted_own_structure", far)


class TestSharedOwnStructureExclusions(unittest.TestCase):
    """Direct, synthetic tests of `_shared_own_structure_exclusions` and
    `ladder_sides_with_discount` -- the exact boundary conditions, without
    the fixture's full machinery."""

    SP = 27.5

    def _rung(self, key, y, x0=0.0, x1=100.0, source="detector"):
        return O.Rung(key=key, x0=x0, x1=x1, y=y, source=source)

    def test_a_rung_one_space_beyond_a_nearer_own_line_is_discounted(self):
        """The measured §2.6c.3 shape: near candidate's own line at
        `head_y - 0.03 sp`; far candidate's `toward` rung at
        `own_line_y - 1.0 sp` (well within `OWN_STRUCTURE_TOLERANCE_
        SPACES`) -- discounted, and the far side no longer `points`."""
        head_y = 4057.0
        near_own = head_y - 0.03 * self.SP       # staff/B's own line
        far_extra = near_own - 1.0 * self.SP     # the shared, false credit
        rungs = [self._rung("own", near_own), self._rung("far", far_extra)]
        # staff/A's own 5 lines, bottom (nearest the head) at 3962 -- the
        # note is 3+ spaces above it; staff/B's own 5 lines, top at 4085 --
        # the note is ~1 space above THAT.
        a_lines = [3852.0, 3879.5, 3907.0, 3934.5, 3962.0]
        b_lines = [4085.0, 4112.5, 4140.0, 4167.5, 4195.0]
        specs = [
            ("staff/A", head_y, 0.0, 100.0, a_lines, self.SP, rungs),
            ("staff/B", head_y, 0.0, 100.0, b_lines, self.SP, rungs),
        ]
        a_before = O.ladder_side(*specs[0])
        self.assertTrue(a_before.points)          # RED shape: A wrongly points
        a, b = O.ladder_sides_with_discount(specs)
        self.assertFalse(a.points)
        self.assertEqual(a.discounted, ("far",))
        self.assertFalse(b.points)                # B needs no rung at all

    def test_a_genuinely_complete_far_ladder_is_never_discounted(self):
        """Litolff #14's shape, as a synthetic control: staff/A's ladder is
        COMPLETE (3 of 3, `missing == 0`) even though its own outermost
        rung sits within tolerance of staff/B's own-line -- `missing < 1`
        blocks the discount (2.6f's guard)."""
        head_y = 1862.6
        sp = 15.75
        b_own = 1862.94                            # staff/B's own line
        a1, a2, a3 = 1895.54, 1879.08, 1863.02      # staff/A's OWN 3 rungs
        rungs = [self._rung("b_own", b_own), self._rung("a1", a1),
                self._rung("a2", a2), self._rung("a3", a3)]
        specs = [
            ("staff/A", head_y, 0.0, 100.0, [1912.0, 1927.75, 1943.5,
                                             1959.25, 1975.0], sp, rungs),
            ("staff/B", head_y, 0.0, 100.0, [1783.0, 1798.75, 1814.5,
                                             1830.25, 1846.0], sp, rungs),
        ]
        a, b = O.ladder_sides_with_discount(specs)
        self.assertEqual(a.missing, 0)
        self.assertEqual(a.discounted, ())
        self.assertTrue(a.points)
        self.assertFalse(b.points)

    def test_a_genuine_second_ledger_for_the_SAME_candidate_still_counts(self):
        """Manager's positive control, literally: a candidate whose OWN
        expected count is 2 (not 1) finds both of ITS OWN rungs, one space
        apart. `_shared_own_structure_exclusions` never compares a side
        against its OWN `anchor_y` (only `other.staff != s.staff`), so with
        no OTHER candidate in the contest at all there is nothing to
        discount against -- a single-side contest, the simplest proof of
        that guard."""
        head_y = 4000.0
        sp = 27.5
        edge = 4055.0                                # 2.0 sp beyond head
        a_lines = [edge, edge + 27.5, edge + 55.0, edge + 82.5, edge + 110.0]
        own = edge - 2 * sp - 0.02 * sp              # step 2 (own line)
        second = edge - 1 * sp                       # step 1, genuinely A's
        rungs = [self._rung("own", own), self._rung("second", second)]
        specs = [("staff/A", head_y, 0.0, 100.0, a_lines, sp, rungs)]
        a_direct = O.ladder_side(*specs[0])
        self.assertEqual(a_direct.expected, 2)
        self.assertEqual(a_direct.found, 2)
        self.assertTrue(a_direct.points)
        (a,) = O.ladder_sides_with_discount(specs)
        self.assertEqual(a.discounted, ())
        self.assertEqual(a.found, 2)
        self.assertTrue(a.points)

    def test_the_physical_duplicate_of_a_discounted_rung_is_also_excluded(self):
        """The SAME physical mark boxed twice (`cell_rungs`'s own
        precedent, CLAUDE.md §10's padded cell) must not let the second
        walk re-find the discounted rung's twin under a different key."""
        head_y = 4057.0
        near_own = head_y - 0.03 * self.SP
        far_extra = near_own - 1.0 * self.SP
        twin = far_extra + 1.4                      # < tol/2 (6.875 px)
        rungs = [self._rung("own", near_own),
                self._rung("far", far_extra),
                self._rung("far_twin", twin)]
        a_lines = [3852.0, 3879.5, 3907.0, 3934.5, 3962.0]
        b_lines = [4085.0, 4112.5, 4140.0, 4167.5, 4195.0]
        specs = [
            ("staff/A", head_y, 0.0, 100.0, a_lines, self.SP, rungs),
            ("staff/B", head_y, 0.0, 100.0, b_lines, self.SP, rungs),
        ]
        a, b = O.ladder_sides_with_discount(specs)
        self.assertFalse(a.points)
        self.assertEqual(set(a.discounted), {"far", "far_twin"})


if __name__ == "__main__":
    unittest.main()
