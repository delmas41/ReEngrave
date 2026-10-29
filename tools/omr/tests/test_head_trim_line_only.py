"""Head-trim fix (2026-10-29, flag `OMR_HEAD_TRIM_LINE_ONLY`, default OFF; benchmarks/shared-ink-map-2026-10/FINDINGS.md): `head_ink.trim_head`'s
END trim stripped the DILATED line rows (+1 px each way, +1 px more on a ledger opening), shaving a quarter off a head in a space on a
15.75 px/sp plate (Litolff: 245 of 342 in-space heads read `too_small`). With the flag it strips only the line's own rows, at most one
measured line thickness per end. Synthetic page: two 2 px staff lines one space (16 px) apart, a filled head in the space between."""
import os
import unittest

import numpy as np

from tools.omr.staged import head_ink as HI

SP = 16.0


def _page():
    page = np.full((60, 120), 255, np.uint8)
    for y in (20, 36):
        page[y:y + 2, :] = 0
    yy, xx = np.mgrid[0:60, 0:120]
    page[((xx - 60) / 11.0) ** 2 + ((yy - 28.5) / 8.5) ** 2 <= 1.0] = 0
    return page, [48.0, 20.0, 72.0, 38.0]


class HeadTrimLineOnly(unittest.TestCase):
    def tearDown(self):
        os.environ.pop(HI.TRIM_ENV, None)

    def _trim(self, flag):
        page, box = _page()
        if flag:
            os.environ[HI.TRIM_ENV] = "1"
        else:
            os.environ.pop(HI.TRIM_ENV, None)
        return HI.trim_head(page, box, SP)

    def test_default_is_off(self):
        os.environ.pop(HI.TRIM_ENV, None)
        self.assertFalse(HI.trim_line_only())

    def test_head_in_a_space_loses_less_with_the_flag(self):
        off, on = self._trim(False), self._trim(True)
        self.assertIsNotNone(off["trimmed"])
        self.assertIsNotNone(on["trimmed"])
        h_off, h_on = off["extent_sp"][1], on["extent_sp"][1]
        self.assertLess(h_off, h_on)
        self.assertGreaterEqual(h_on, 0.8)
        self.assertIsNone(on["not_one_head"])

    def test_the_cut_is_still_at_most_one_line_thickness_per_end(self):
        on = self._trim(True)
        self.assertGreaterEqual(on["trimmed"][3] - on["trimmed"][1], 17 - 2 * 2)


if __name__ == "__main__":
    unittest.main()
