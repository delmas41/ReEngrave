"""ROADMAP 2.251 -- a clef read page-wide by its shape (step 1) and the clef in force at a head (step 2). Synthetic pages, twins:
a C clef inside a system is found and named; a barline, a stem with a head beside the barline, and a thick bar with no bowls are not."""
import os
import unittest

import numpy as np

from tools.omr.staged import clef_pagewide as CP

SP = 16.0
TOP = 100.0
LINES = [TOP + i * SP for i in range(5)]


def page(w=400, h=260):
    ink = np.zeros((h, w), dtype=bool)
    for y in LINES:
        ink[int(y) - 1:int(y) + 1, 10:w - 10] = True
    return ink


def c_clef(ink, x, line_from_top):
    """A small C clef centred on the line `line_from_top` (0 = top line): thick bar, thin bar, two bowls."""
    mid = int(LINES[line_from_top])
    h = int(1.85 * SP)
    ink[mid - h:mid + h, x:x + 12] = True                    # thick bar ~0.75 sp
    ink[mid - h:mid + h, x + 16:x + 18] = True               # thin bar
    for sgn in (-1, 1):                                      # two mirrored bowls
        y0, y1 = (mid - h + 2, mid - 3) if sgn < 0 else (mid + 3, mid + h - 2)
        ink[y0:y1, x + 19:x + 34] = True
        ink[y0 + 5:y1 - 5, x + 24:x + 28] = False


class CBarTwins(unittest.TestCase):
    def test_c_clef_inside_a_system_is_found_and_named_tenor(self):
        ink = page()
        c_clef(ink, 200, 1)
        got = [c for c in CP.c_bars(ink, LINES, SP, 20, 380) if c["passed"]]
        self.assertEqual(len(got), 1)
        self.assertEqual(CP.name_c(got[0]["middle_y"], got[0]["lines_local"])[0], "tenor")

    def test_alto_twin(self):
        ink = page()
        c_clef(ink, 200, 2)
        got = [c for c in CP.c_bars(ink, LINES, SP, 20, 380) if c["passed"]]
        self.assertEqual(CP.name_c(got[0]["middle_y"], got[0]["lines_local"])[0], "alto")

    def test_barline_is_not_a_clef(self):
        ink = page()
        ink[int(LINES[0]):int(LINES[4]) + 1, 200:205] = True     # a barline: ~0.3 sp
        self.assertFalse([c for c in CP.c_bars(ink, LINES, SP, 20, 380) if c["passed"]])

    def test_head_and_stem_beside_a_barline_is_not_a_clef(self):
        ink = page()
        ink[int(LINES[0]):int(LINES[4]) + 1, 196:201] = True     # barline
        ink[int(LINES[1]) - 6:int(LINES[1]) + 7, 206:226] = True  # a head ...
        ink[int(LINES[1]) - 56:int(LINES[1]), 224:226] = True     # ... and its stem
        self.assertFalse([c for c in CP.c_bars(ink, LINES, SP, 20, 380) if c["passed"]])

    def test_thick_bar_without_bowls_is_not_a_clef(self):
        ink = page()
        ink[int(LINES[0]) - 8:int(LINES[4]) - 20, 200:212] = True
        got = CP.c_bars(ink, LINES, SP, 20, 380)
        self.assertFalse([c for c in got if c["passed"]])
        self.assertIn("no_bowls", [c["why"] for c in got])

    def test_a_clef_named_on_no_allowed_line_is_claimed_unread(self):
        nm, ln, _res = CP.name_c(LINES[0], LINES)               # soprano/mezzo lines are not READ kinds
        self.assertIsNone(nm)


class Flags(unittest.TestCase):
    def test_default_on_carry_off(self):
        old = os.environ.pop(CP.ENV, None), os.environ.pop(CP.ENV_CARRY, None)
        try:
            self.assertTrue(CP.enabled())
            self.assertFalse(CP.carry_enabled())
            for v in ("0", "false", "no", "off"):
                os.environ[CP.ENV] = v
                self.assertFalse(CP.enabled())
            os.environ[CP.ENV] = "1"
            self.assertTrue(CP.enabled())
        finally:
            os.environ.pop(CP.ENV, None)
            if old[0] is not None:
                os.environ[CP.ENV] = old[0]
            if old[1] is not None:
                os.environ[CP.ENV_CARRY] = old[1]


class Row:
    def __init__(self, x, kind, change=True, source=CP.SOURCE):
        self.value = [x, 0, x + 30, 50]
        self.detail = {"source": source, "change": change, "kind": kind}


class ClefInForce(unittest.TestCase):
    def test_last_printed_before_the_head_governs(self):
        ch = CP.changes_of([Row(300, "bass"), Row(100, "tenor"), Row(50, "alto", change=False), Row(200, None, source="clef_slot")])
        self.assertEqual([c[1] for c in ch], ["tenor", "bass"])
        self.assertIsNone(CP.clef_in_force(90, ch))              # before any change: the header clef
        self.assertEqual(CP.clef_in_force(150, ch)[0], "tenor")
        self.assertEqual(CP.clef_in_force(350, ch)[0], "bass")

    def test_unread_change_governs_as_unread(self):
        ch = CP.changes_of([Row(100, None)])
        got = CP.clef_in_force(150, ch)
        self.assertIsNotNone(got)
        self.assertIsNone(got[0])


if __name__ == "__main__":
    unittest.main()
