"""ROADMAP 2.39 -- the standard notehead box, promoted to one shared place.

`tools.omr.staged.geometry` is the general version of what ROADMAP 2.37
built local to `gather._observe_ledger_owner_density`
(`LEDGER_OWNER_HEAD_WIDTH_SPACES`/`_HEIGHT_SPACES`, `_standard_head_box`).
This module asks three things: the shared module computes the SAME box the
2.37 names used to compute directly; `gather.py`'s old names are now
ALIASES onto it (not a second, driftable copy); and `reach.py` accounts for
the new file so `check`/`unaccounted_modules()` do not regress.

⚠️ RUN RED FIRST: `tools.omr.staged.geometry` did not exist before this
round -- every import below failed, and `"geometry.py"` was absent from
`reach.NOT_A_STAGE`.
"""
from __future__ import annotations

import unittest

from tools.omr.staged import gather
from tools.omr.staged import geometry as G
from tools.omr.staged import reach


class TestStandardHeadBoxMath(unittest.TestCase):
    def test_box_centred_on_cx_cy(self):
        x0, x1, y0, y1 = G.standard_head_box(100.0, 200.0, 10.0)
        self.assertAlmostEqual((x0 + x1) / 2.0, 100.0)
        self.assertAlmostEqual((y0 + y1) / 2.0, 200.0)

    def test_box_sized_from_spacing(self):
        x0, x1, y0, y1 = G.standard_head_box(0.0, 0.0, 10.0)
        self.assertAlmostEqual(x1 - x0, G.STANDARD_HEAD_WIDTH_SPACES * 10.0)
        self.assertAlmostEqual(y1 - y0, G.STANDARD_HEAD_HEIGHT_SPACES * 10.0)


class TestGatherAliasesDelegate(unittest.TestCase):
    """`gather.py`'s pre-2.39 names must be a THIN ALIAS, not a second,
    driftable copy -- the control that would fail if a future edit re-forked
    the constant in one file and not the other."""

    def test_gather_constants_equal_geometry_constants(self):
        self.assertEqual(gather.LEDGER_OWNER_HEAD_WIDTH_SPACES,
                        G.STANDARD_HEAD_WIDTH_SPACES)
        self.assertEqual(gather.LEDGER_OWNER_HEAD_HEIGHT_SPACES,
                        G.STANDARD_HEAD_HEIGHT_SPACES)

    def test_gather_box_fn_matches_geometry_box_fn(self):
        a = gather._standard_head_box(12.0, 34.0, 7.0)
        b = G.standard_head_box(12.0, 34.0, 7.0)
        self.assertEqual(a, b)


class TestIsRegularNotehead(unittest.TestCase):
    """ROADMAP 2.39 item 5: only a regular-size black/half head gets the
    standard box. A whole note is a different, wider Bravura shape and a
    `*Small` (grace/cue) head is a real but smaller notehead -- both stay on
    the detector's own box, which this gate is what every consumer must
    ask before calling `standard_head_box`."""

    def test_regular_black_and_half_are_regular(self):
        self.assertTrue(G.is_regular_notehead("noteheadBlack"))
        self.assertTrue(G.is_regular_notehead("noteheadBlackOnLine"))
        self.assertTrue(G.is_regular_notehead("noteheadHalfInSpace"))

    def test_whole_and_double_whole_are_not_regular(self):
        self.assertFalse(G.is_regular_notehead("noteheadWhole"))
        self.assertFalse(G.is_regular_notehead("noteheadWholeOnLine"))
        self.assertFalse(G.is_regular_notehead("noteheadDoubleWhole"))

    def test_small_grace_cue_heads_are_not_regular(self):
        self.assertFalse(G.is_regular_notehead("noteheadBlackSmall"))
        self.assertFalse(G.is_regular_notehead("noteheadHalfSmall"))

    def test_none_and_other_families_are_not_regular(self):
        self.assertFalse(G.is_regular_notehead(None))
        self.assertFalse(G.is_regular_notehead(""))
        self.assertFalse(G.is_regular_notehead("restQuarter"))


class TestReachAccountsForGeometryModule(unittest.TestCase):
    """The guard ROADMAP 1.1b/0.5/1.2b all cite: a new staged `.py` must be
    in `STAGE_OF_FILE` or `NOT_A_STAGE`, or `unaccounted_modules()` (and
    `check`) regress silently."""

    def test_geometry_py_is_registered(self):
        self.assertIn("geometry.py", reach.NOT_A_STAGE)

    def test_unaccounted_modules_is_empty(self):
        self.assertEqual(reach.unaccounted_modules(), [])
