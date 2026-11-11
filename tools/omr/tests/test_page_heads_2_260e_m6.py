"""ROADMAP 2.260e M6b's surviving pure core (the far-head ledger-read trigger and the half-step position) and the M6b head list built on the ONE identity.
ROADMAP 2.290 landing deleted M6a's IoU fold, its `Q.PAGE_HEAD` rows and claims (`file_page_heads`, `head_claims`) and M6c (`OMR_PAGE_HEADS`,
`OMR_PAGE_HEAD_CLAIM`): the one identity and the one claim are `test_page_heads_one_2_290.py`'s."""
import unittest

from tools.omr.staged import page_heads as PH

HEAD = (100.0, 200.0, 120.0, 215.0)          # a head 20 x 15 px


class Trigger(unittest.TestCase):
    def test_tile_9_box_rounds_to_the_first_space_ink_says_the_first_ledger(self):
        # tile 9: box 9.38 -> 9 (first space: today nobody asks); ink centre 10.0 -> outside
        self.assertEqual(PH.far_trigger([9], 10.0, False), "ink")
        self.assertIsNone(PH.far_trigger([9], 9.38, False))        # the OLD rule's answer: no ledger read at all

    def test_a_box_outside_still_asks(self):
        self.assertEqual(PH.far_trigger([11], 11.0, False), "box")
        self.assertEqual(PH.far_trigger([-2], None, False), "box")

    def test_first_space_with_no_ledger_touching_is_on_staff(self):
        self.assertIsNone(PH.far_trigger([9], 9.1, False))
        self.assertIsNone(PH.far_trigger([-1], -1.2, False))

    def test_first_space_with_a_ledger_stub_touching_does_not_ask_alone(self):
        # measured: asking on the stub alone read one end of a tie and not the other (Litolff p2), so the stub is recorded, not a trigger
        self.assertIsNone(PH.far_trigger([9], 9.1, True))

    def test_a_stub_touching_a_middle_head_asks_nothing(self):
        self.assertIsNone(PH.far_trigger([4], 4.0, True))         # a tie's end, a beam: not a ledger


class Positions(unittest.TestCase):
    def test_position_is_half_steps_from_the_top_line(self):
        self.assertAlmostEqual(PH.position_of(100.0 + 8 * 7.0, 100.0, 7.0), 8.0)
        self.assertAlmostEqual(PH.position_of(100.0 + 10 * 7.0, 100.0, 7.0), 10.0)


class GroupsFromTheOneIdentity(unittest.TestCase):
    def test_m6b_groups_are_the_one_identitys(self):
        one = PH.OneHeads()
        one.group_of_key = {"g0": 3, "g1": 3, "g2": 4}
        hb = [dict(key="g0", box=HEAD), dict(key="g1", box=HEAD), dict(key="g2", box=(200.0, 200.0, 220.0, 215.0)), dict(key="g9", box=(300.0, 0, 1, 1))]
        self.assertEqual(PH._groups_from_one(hb, one), [[0, 1], [2], [3]])

    def test_without_the_identity_every_box_stands_alone(self):
        hb = [dict(key="g0", box=HEAD), dict(key="g1", box=HEAD)]
        self.assertEqual(PH._groups_from_one(hb, None), [[0], [1]])


class Flags(unittest.TestCase):
    def test_views_off_by_default_and_the_old_flags_are_gone(self):
        import os
        from unittest import mock
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(PH.views_enabled())
        with mock.patch.dict(os.environ, {PH.VIEWS_ENV: "1"}, clear=True):
            self.assertTrue(PH.views_enabled())
        for gone in ("ENV", "CLAIM_ENV", "fold", "FOLD_IOU", "file_page_heads", "head_claims", "claim_enabled", "enabled"):
            self.assertFalse(hasattr(PH, gone), gone)


if __name__ == "__main__":
    unittest.main()
