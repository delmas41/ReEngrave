"""ROADMAP 2.306 batch 2 -- THE STEM A TREMOLO SLASH CROSSES IS READ WHERE IT SHOWS PLAINLY (STAGED GATHER, `page_tremolo`, flag
`OMR_SLASH_STEM_CORE`, default ON).

Rule (as a musician says it): a tremolo slash is a short thick diagonal across a stem; the stem is the thin upright through it, and where
the stem runs is read where it shows plainly above and below the slash -- never on the slash's own rows. Never a slash out of chord heads
standing on one side of their stem, nor out of a letter's bowls.

Every control is REAL page ink (the erased page canvas the page reader reads, cut around one page-map stem, `data_tremolo_stem_core_2306b2.npz`):
  slash_16_0_1_6      Litolff p16 cell 16/0/1/6: the slash under the G5 half the batch-2 ON arm wrote as a C5 half (read `one_sided` before)
  sean_2276r2_3       Sean's judged slash, 2.276 r2 tile 3 (Litolff p16) -- must still pass
  sean_2276r2_8       Sean's judged slash, 2.276 r2 tile 8 (Litolff p6) -- must still pass
  sean_chord_2_0_7_4  Sean's glyph/2/0/7/4, "three quarter notes with a half note on top" (Litolff p2): no slash; a quarter head was taken as one
                      when the stem was read on its plain rows without the crossing test
  letter_B_brahms_p4  a printed letter "B" (Brahms p4): its spine read as a stem, its bowls as slashes without the crossing test
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

DATA = pathlib.Path(__file__).with_name("data_tremolo_stem_core_2306b2.npz")


def _case(name):
    z = np.load(DATA)
    meta = json.loads(str(z["meta"]))[name]
    return z[name], tuple(float(v) for v in meta["stem"]), [tuple(float(v) for v in b) for b in meta["near"]], float(meta["sp"]), float(meta["line_px"])


def _passed(name, own_rows):
    ink, stem, near, sp, line = _case(name)
    return [s for s in G.stem_slashes(ink, stem, sp, line, near, (), own_rows=own_rows) if s.get("reason") is None]


class TestStemCore(unittest.TestCase):
    def test_flag_default_on(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(PT.STEM_CORE_ENV, None)
            self.assertTrue(PT.stem_core_enabled())
        for off in ("0", "false", "no", "off"):
            with mock.patch.dict(os.environ, {PT.STEM_CORE_ENV: off}):
                self.assertFalse(PT.stem_core_enabled())

    def test_slash_on_a_short_stem_is_read(self):
        """16/0/1/6: read on its plain rows the slash passes; the old read (every row) refuses it -- the control fails with the rule off."""
        self.assertEqual(len(_passed("slash_16_0_1_6", True)), 1)
        self.assertEqual(_passed("slash_16_0_1_6", False), [])

    def test_seans_slashes_still_pass(self):
        for name in ("sean_2276r2_3", "sean_2276r2_8"):
            for own in (False, True):
                self.assertEqual(len(_passed(name, own)), 1, (name, own))

    def test_chord_heads_and_a_letter_are_never_slashes(self):
        """Sean's chord and the letter B: nothing passes; with the crossing test off (share 0) they come back -- the control can fail."""
        for name in ("sean_chord_2_0_7_4", "letter_B_brahms_p4"):
            self.assertEqual(_passed(name, True), [], name)
        with mock.patch.object(G, "STEM_CROSSED_ROWS_MIN_SHARE", 0.0):
            back = {name: len(_passed(name, True)) for name in ("sean_chord_2_0_7_4", "letter_B_brahms_p4")}
        self.assertTrue(any(back.values()), back)

    def test_read_page_asks_by_the_flag(self):
        seen = []

        def fake(ink, box, sp, line_px, near, heads, own_rows=False):
            seen.append(own_rows)
            return []
        with mock.patch.object(G, "stem_slashes", fake):
            for v, want in (("0", False), ("1", True)):
                with mock.patch.dict(os.environ, {PT.STEM_CORE_ENV: v}):
                    PT.read_page(np.zeros((10, 10), bool), [(0, (1.0, 1.0, 1.0, 5.0))], [], 16.0, 2.0)
                self.assertEqual(seen[-1], want)


if __name__ == "__main__":
    unittest.main()
