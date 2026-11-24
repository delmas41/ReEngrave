"""ROADMAP 2.335 -- THE SLASH CORE MUST NOT LEAVE A STEM STANDING ON A SLASH, NOR A SLASH UNCLAIMED (STAGED GATHER, `page_tremolo`, flag
`OMR_SLASH_STEM_CORE`, default ON).

Rules (as a musician says them):
  * a ledger line a slash touches is a line, not part of the slash: the slash is read without it, as it is read without the staff lines --
    never is ink thicker than a line set aside;
  * a slash joins another stem only where its ink runs into that stem's ink -- never because the other stem's box ends near it.

Every control is REAL page ink (the carved page canvas the page reader reads, `data_tremolo_claim_once_2335.npz`):
  ledger_6_1_8_11   Litolff p6 cell/6/1/8/11: the slash at the tail of a down stem below the staff, touching the ledger line. Read nowhere
                    before (refused `runs_on` / `not_at_an_angle`), so no claim, and detector box 0 (its right-hand piece) was written a C4 half
                    (lane 2.336's trace). Must pass, and its claim box must hold box 0.
  sean_16_0_0_5     Litolff p16 cell/16/0/0/5, Sean 2026-11-22: "A is a half note sitting right above the staff, and B is a tremolo slash".
                    A must never be read as a slash; the slash further down the stem keeps passing.
"""
from __future__ import annotations

import json
import os
import pathlib
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import gather as G
from tools.omr.staged import page_tremolo as PT

DATA = pathlib.Path(__file__).with_name("data_tremolo_claim_once_2335.npz")


def _case(name):
    z = np.load(DATA)
    return z[name], json.loads(str(z["meta"]))[name]


def _read(name, flag):
    ink, m = _case(name)
    stems = [(0, tuple(m["stem"]))] + [(i + 1, tuple(b)) for i, b in enumerate(m["near"])]
    with mock.patch.dict(os.environ, {PT.STEM_CORE_ENV: "1" if flag else "0"}):
        slashes, _reasons = PT.read_page(ink, stems, [], m["sp"], m["line_px"])
    return [s for s in slashes if s["stem"] == 0], m


def _inside(inner, outer):
    ix = min(inner[2], outer[2]) - max(inner[0], outer[0])
    iy = min(inner[3], outer[3]) - max(inner[1], outer[1])
    a = (inner[2] - inner[0]) * (inner[3] - inner[1])
    return 0.0 if ix <= 0 or iy <= 0 else ix * iy / a


class TestLedgerLineAside(unittest.TestCase):
    def test_slash_touching_a_ledger_line_is_read_and_holds_the_false_head(self):
        got, m = _read("ledger_6_1_8_11", True)
        self.assertEqual(len(got), 1, got)
        # the claim box holds the detector box written as a C4 half: the generic claim rule (2.277) refuses it
        self.assertGreaterEqual(_inside(m["box0"], got[0]["box"]), 0.9)

    def test_control_fails_without_the_change(self):
        """Flag off (the old path), and flag on with the ledger line left in: no slash -- the control can fail."""
        self.assertEqual(_read("ledger_6_1_8_11", False)[0], [])
        with mock.patch.object(PT, "lines_aside", lambda ink, line_px, sp: ink):
            self.assertEqual(_read("ledger_6_1_8_11", True)[0], [])

    def test_lines_aside_never_takes_thick_ink(self):
        ink, m = _case("ledger_6_1_8_11")
        out = PT.lines_aside(ink, m["line_px"], m["sp"])
        gone = ink & ~out
        self.assertTrue(gone.any())
        runs = PT._run_lengths(ink)
        self.assertLessEqual(int(runs[gone].max()), int(round(PT.LINE_THIN_FACTOR * m["line_px"])))

    def test_seans_16_0_0_5_unchanged(self):
        for flag in (False, True):
            got, m = _read("sean_16_0_0_5", flag)
            self.assertFalse(any(_inside(m["A"], s["box"]) >= 0.3 for s in got), (flag, got))
            self.assertTrue(any(_inside(m["slash_below"], s["box"]) >= 0.9 for s in got), (flag, got))


class TestClaimReachesItsStrokes(unittest.TestCase):
    def test_the_slash_cell_stroke_lies_inside_the_claim(self):
        """Real numbers from the 2.335 ON gather of Litolff p6: the finder's box for the 6/1/8/11 slash, its owned page stroke 3564, and the cell's
        stroke 375010 linked to 3564. The cell settle (`stroke_owner._layer_claims`) takes a cell stroke only wholly inside the rectangle (+1 px):
        on the finder's box alone it does not (the control can fail), on the claim area it does."""
        finder_box = [2443.0, 3248.0, 2475.0, 3275.0]
        page_stroke_3564 = [2444.0, 3256.0, 2476.0, 3274.0]
        cell_stroke = [2444.3, 3256.1, 2476.6, 3274.3]

        def inside(r):
            return r[0] - 1 <= cell_stroke[0] and cell_stroke[2] <= r[2] + 1 and r[1] - 1 <= cell_stroke[1] and cell_stroke[3] <= r[3] + 1
        self.assertFalse(inside(finder_box))
        self.assertTrue(inside(PT.claim_area(finder_box, [page_stroke_3564])))
        self.assertEqual(PT.claim_area(finder_box, []), finder_box)


class TestJoinByInk(unittest.TestCase):
    def test_a_stem_box_ending_near_the_slash_does_not_join_it(self):
        """6/1/8/11: the neighbouring stem's box ends within half a space of the slash's height but its ink never meets the slash."""
        ink, m = _case("ledger_6_1_8_11")
        ink = PT.lines_aside(ink, m["line_px"], m["sp"])
        near = [tuple(b) for b in m["near"]]
        on = [s.get("reason") for s in G.stem_slashes(ink, tuple(m["stem"]), m["sp"], m["line_px"], near, (), own_rows=True)]
        old = [s.get("reason") for s in G.stem_slashes(ink, tuple(m["stem"]), m["sp"], m["line_px"], near, (), own_rows=False)]
        self.assertIn(None, on)
        self.assertNotIn(None, old)

    def test_a_beam_tracked_through_the_next_stem_joins_it(self):
        """Litolff p1: a beam crossing two stems. With the flag on it must never pass as a slash; with the join test blinded it passes -- the control
        can fail (the first 2.335 ON gather, before the run-through test, claimed it as a slash)."""
        self.assertEqual(_read("beam_p1", True)[0], [])
        orig = G._slash_runs_into_a_stem

        def gap_only(ink, runs, direction, others, space):
            return orig(ink, runs[:-3] if len(runs) > 3 else runs, direction, (), space)
        with mock.patch.object(G, "_slash_runs_into_a_stem", gap_only):
            self.assertEqual(len(_read("beam_p1", True)[0]), 1)

    def test_ink_running_into_a_stem_joins_it(self):
        """The same real slash, with the neighbouring stem moved onto its right-hand end (the stroke's last rows): joined."""
        ink, m = _case("ledger_6_1_8_11")
        ink = PT.lines_aside(ink, m["line_px"], m["sp"])
        got = [s for s in G.stem_slashes(ink, tuple(m["stem"]), m["sp"], m["line_px"], (), (), own_rows=True) if s.get("reason") is None]
        self.assertEqual(len(got), 1)
        x1 = got[0]["box"][2]
        y0, y1 = got[0]["box"][1], got[0]["box"][3]
        planted = ink.copy()
        planted[int(y0):int(y1), int(x1):int(x1) + 4] = True
        stem_b = (x1, y0 - 10, 4.0, (y1 - y0) + 20)
        r = [s.get("reason") for s in G.stem_slashes(planted, tuple(m["stem"]), m["sp"], m["line_px"], [stem_b], (), own_rows=True)]
        self.assertNotIn(None, r)


if __name__ == "__main__":
    unittest.main()
