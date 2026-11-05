"""ROADMAP 2.260e M6: the page head list's pure core on SYNTHETIC boxes (no raster): the fold (a planted double box is ONE head; two heads a second apart or a
unison side by side are TWO), the ledger-read trigger (tile 9: box 9.38 rounds 9, ink near 10 -> asked), and the claim order (an earlier owner's stroke is
contested, never taken; the same owner twice is a twin)."""
import unittest

from tools.omr.staged import page_heads as PH

HEAD = (100.0, 200.0, 120.0, 215.0)          # a head 20 x 15 px


def shifted(b, dx=0.0, dy=0.0):
    return (b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy)


class Fold(unittest.TestCase):
    def test_a_planted_double_box_folds_to_one_head(self):
        g = PH.fold([HEAD, shifted(HEAD, 1, 2)], [0, 0])
        self.assertEqual(g, [[0, 1]])

    def test_twin_in_a_neighbour_cell_folds_but_needs_the_same_staff(self):
        self.assertEqual(PH.fold([HEAD, shifted(HEAD, 1, 1)], [0, 1]), [[0], [1]])

    def test_a_second_apart_is_two_heads(self):
        # opposite sides of a stem: one head width across, half a space (7 px) down
        g = PH.fold([HEAD, shifted(HEAD, 21, 7)], [0, 0])
        self.assertEqual(g, [[0], [1]])

    def test_a_unison_side_by_side_is_two_heads(self):
        self.assertEqual(PH.fold([HEAD, shifted(HEAD, 20, 0)], [0, 0]), [[0], [1]])

    def test_the_control_can_fail(self):
        # a threshold of 0.0 folds the second-apart pair too: the fold is the IoU cut, nothing else
        self.assertEqual(PH.fold([HEAD, shifted(HEAD, 10, 7)], [0, 0], min_iou=0.0), [[0, 1]])
        self.assertEqual(PH.fold([HEAD, shifted(HEAD, 10, 7)], [0, 0]), [[0], [1]])

    def test_chain_of_three_boxes_is_one_head(self):
        self.assertEqual(PH.fold([HEAD, shifted(HEAD, 3, 0), shifted(HEAD, 6, 0)], [0, 0, 0]), [[0, 1, 2]])


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


class Claims(unittest.TestCase):
    def test_an_earlier_owner_holds_a_stroke_and_the_head_is_contested_not_given_it(self):
        ph = PH.PageHeads()
        ph.heads = [dict(ordinal=0, blob_strokes=[5, 6], rung_strokes=[9], members=["g0"])]
        got = PH.head_claims(ph, None, held={6: "word"})
        head = [c for c in got if c["owner"] == "head"][0]
        self.assertEqual(head["won"], [5])
        self.assertEqual(head["contested"], [[6, "word"]])

    def test_the_same_owner_twice_is_a_twin_and_a_ledger_stub_is_the_ledgers(self):
        ph = PH.PageHeads()
        ph.heads = [dict(ordinal=0, blob_strokes=[5], rung_strokes=[9], members=["g0"]),
                    dict(ordinal=1, blob_strokes=[5], rung_strokes=[9], members=["g1"])]
        got = PH.head_claims(ph, None)
        self.assertEqual([c["owner"] for c in got], ["head", "head", "ledger", "ledger"])
        self.assertEqual(got[1]["twins"], 1)
        self.assertEqual(got[1]["contested"], [])
        self.assertEqual(got[3]["twins"], 1)

    def test_a_stub_a_head_holds_is_contested_for_the_ledger(self):
        ph = PH.PageHeads()
        ph.heads = [dict(ordinal=0, blob_strokes=[5], rung_strokes=[5], members=["g0"])]
        got = PH.head_claims(ph, None)
        self.assertEqual(got[1]["contested"], [[5, "head"]])


class Flags(unittest.TestCase):
    def test_off_by_default_and_views_need_the_reader(self):
        import os
        from unittest import mock
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(PH.enabled())
            self.assertFalse(PH.views_enabled())
        with mock.patch.dict(os.environ, {PH.VIEWS_ENV: "1"}, clear=True):
            self.assertFalse(PH.views_enabled())
        with mock.patch.dict(os.environ, {PH.ENV: "1", PH.VIEWS_ENV: "1", PH.CLAIM_ENV: "1"}, clear=True):
            self.assertTrue(PH.views_enabled() and PH.claim_enabled())


if __name__ == "__main__":
    unittest.main()
