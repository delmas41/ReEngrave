"""ROADMAP 2.242 -- ONE ACCIDENTAL, ONE PIECE (flag OMR_ACCIDENTAL_WHOLE, default OFF). STAGED GATHER (stroke map) + the owner's shape."""
import os
import unittest

import numpy as np

from tools.omr.staged import stroke_map as SM
from tools.omr.staged import stroke_owner as SO

SP = 16.0


def piece(kind, x0, y0, w, h):
    return (kind, np.ones((h, w), bool), x0, y0)


def sharp_pieces(x0=100, y0=100):
    """a sharp, cut as the openings cut it: two stems and two bars (about 1.0 x 2.8 sp = 16 x 45 px)."""
    return [piece("vertical", x0 + 3, y0, 2, 45), piece("vertical", x0 + 11, y0 + 3, 2, 45),
            piece("horizontal", x0, y0 + 15, 16, 3), piece("horizontal", x0, y0 + 28, 16, 3)]


class _Flag:
    def __init__(self, v):
        self.v = v

    def __enter__(self):
        self.old = os.environ.get(SM.ACCIDENTAL_WHOLE_ENV)
        if self.v is None:
            os.environ.pop(SM.ACCIDENTAL_WHOLE_ENV, None)
        else:
            os.environ[SM.ACCIDENTAL_WHOLE_ENV] = self.v

    def __exit__(self, *a):
        if self.old is None:
            os.environ.pop(SM.ACCIDENTAL_WHOLE_ENV, None)
        else:
            os.environ[SM.ACCIDENTAL_WHOLE_ENV] = self.old


class TestMerge(unittest.TestCase):
    def test_a_sharp_cut_in_four_is_one_stroke_with_its_parts(self):
        pcs = sharp_pieces()
        box = (99.0, 99.0, 117.0, 150.0)
        out, joins, parts = SM.merge_accidentals(pcs, [], SP, [(box, "accidentalSharp")], [], {})
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0][0], "blob")
        u = np.zeros((200, 200), bool)                                         # the union of the parts is exactly the stroke (synthetic parts overlap)
        for _k, m, x0, y0 in parts[0]:
            u[y0:y0 + m.shape[0], x0:x0 + m.shape[1]] |= m
        self.assertEqual(int(u.sum()), int(out[0][1].sum()))
        self.assertEqual(len(parts[0]), 4)

    def test_a_piece_in_a_head_box_is_never_joined_and_a_false_box_on_a_head_merges_nothing(self):
        pcs = sharp_pieces() + [piece("blob", 118, 120, 14, 12)]          # a head touching the sharp's right edge
        head = (117.0, 118.0, 135.0, 134.0)
        out, _j, parts = SM.merge_accidentals(pcs, [], SP, [((99.0, 99.0, 117.0, 150.0), "accidentalSharp")], [head], {})
        self.assertEqual(len(out), 2)                                          # the sharp whole, the head apart
        self.assertEqual(len(parts[0]), 4)
        # a box standing on the head's own ink: its seed is the head piece, excluded -> nothing merged
        _o2, _j2, parts2 = SM.merge_accidentals([piece("blob", 118, 120, 14, 12)], [], SP, [((117.0, 118.0, 135.0, 134.0), "accidentalDoubleSharp")], [head], {})
        self.assertEqual(parts2, {})

    def test_ink_beyond_the_glyph_size_is_not_joined(self):
        pcs = sharp_pieces() + [piece("horizontal", 80, 100, 70, 3)]            # a 4.4 sp rung touching the sharp's top: wider than the glyph
        out, _j, parts = SM.merge_accidentals(pcs, [], SP, [((99.0, 99.0, 117.0, 150.0), "accidentalSharp")], [], {})
        self.assertEqual(len(out), 2)
        self.assertEqual(len(parts[0]), 4)

    def test_joins_are_renumbered_and_a_join_inside_one_accidental_vanishes(self):
        pcs = sharp_pieces() + [piece("blob", 300, 100, 14, 12)]
        _out, joins, _p = SM.merge_accidentals(pcs, [(1, 0, "x"), (4, 0, "y")], SP, [((99.0, 99.0, 117.0, 150.0), "accidentalSharp")], [], {})
        self.assertEqual(joins, [(1, 0, "y")])

    def test_a_key_class_or_unsized_box_merges_nothing(self):
        out, _j, parts = SM.merge_accidentals(sharp_pieces(), [], SP, [((99.0, 99.0, 117.0, 150.0), "keySharp")], [], {})
        self.assertEqual(parts, {})
        self.assertEqual(len(out), 4)


class TestOwnerYields(unittest.TestCase):
    def ink(self, ordinal, kind, w, h, thick, touches=()):
        return SO.Ink(ordinal, kind, (0, 0, w * 16.0, h * 16.0), max(w, h), thick, w * h * thick, 16.0, touches=tuple(touches))

    def test_a_head_body_the_accidental_box_covers_is_the_heads_only_with_the_flag(self):
        """2.241 tile 10: a head with a little ink under it (1.2 x 1.9 sp, 0.8 thick); its head box `could` fit, the accidental `clear`ed."""
        s = self.ink(0, "blob", 1.22, 1.86, 0.79)
        head = SO.Claim("h", "head", "noteheadBlackOnLine", covers=(0,))
        acc = SO.Claim("a", "accidental", "accidentalDoubleSharp", covers=(0,))
        with _Flag(None):
            self.assertEqual(SO.own_strokes([s], [head, acc])[0].family, "accidental")        # the fault, flag OFF
        with _Flag("1"):
            o = SO.own_strokes([s], [head, acc])[0]
            self.assertEqual(o.family, "head")
            self.assertTrue(any(c["why"].startswith("yields_to_a_head_body") for c in o.candidates if c["family"] == "accidental"))

    def test_a_thin_accidental_blob_under_a_head_box_is_not_taken(self):
        s = self.ink(0, "blob", 0.9, 1.3, 0.3)                              # line ink: a flat's bowl beside a head box's edge
        head = SO.Claim("h", "head", "noteheadBlackOnLine", covers=(0,))
        acc = SO.Claim("a", "accidental", "accidentalFlat", covers=(0,))
        with _Flag("1"):
            self.assertNotEqual(SO.own_strokes([s], [head, acc])[0].state, "unclaimed")
            self.assertIn(SO.own_strokes([s], [head, acc])[0].family, ("accidental", None))

    def test_ink_hanging_from_a_long_stem_under_a_flag_box_is_the_flags(self):
        """2.241 tile 3: a flag cut into scraps that chain down from a 4.6 sp stem; an accidental box covers the scraps."""
        stem = self.ink(0, "vertical", 0.3, 4.6, 0.25, touches=[(1, 0.6)])
        a = self.ink(1, "blob", 0.4, 1.2, 0.3, touches=[(0, 0.6), (2, 0.5)])
        b = self.ink(2, "blob", 0.4, 1.0, 0.3, touches=[(1, 0.5)])
        flag = SO.Claim("f", "flag", "flag8thDown", covers=(1, 2))
        acc = SO.Claim("a", "accidental", "accidentalFlat", covers=(1, 2))
        with _Flag(None):
            self.assertEqual(SO.own_strokes([stem, a, b], [flag, acc])[1].family, "accidental")
        with _Flag("1"):
            own = SO.own_strokes([stem, a, b], [flag, acc])
            self.assertFalse(own[1].claimed)                                    # left to the consumers (the flag reader)
            self.assertFalse(own[2].claimed)

    def test_a_flat_beside_its_own_short_stem_is_not_a_flag(self):
        stem = self.ink(0, "vertical", 0.3, 2.4, 0.25, touches=[(1, 0.6)])      # an accidental's own stem, under 3.7 sp
        bowl = self.ink(1, "blob", 0.9, 1.9, 0.3, touches=[(0, 0.6)])
        flag = SO.Claim("f", "flag", "flag8thDown", covers=(0, 1))
        acc = SO.Claim("a", "accidental", "accidentalFlat", covers=(0, 1))
        with _Flag("1"):
            self.assertEqual(SO.own_strokes([stem, bowl], [flag, acc])[1].family, "accidental")


class TestShapeAndSize(unittest.TestCase):
    """2.242 round 2 (Sean's tiles 2, 7, 11, 12: 'Add shape and size'). Sizes are the pieces' measured px on Litolff (16.25 px/sp) and Brahms (27.55)."""

    def ink(self, w_px, h_px, unit, kind="blob", ordinal=0):
        return SO.Ink(ordinal, kind, (0, 0, float(w_px), float(h_px)), max(w_px, h_px) / unit, 0.4, w_px * h_px / unit ** 2 * 0.5, unit)

    def owned(self, s, cls):
        acc = SO.Claim("a", "accidental", cls, covers=(s.ordinal,))
        return SO.own_strokes([s], [acc])[s.ordinal]

    def test_the_three_speck_tiles_and_the_bowl_are_refused_with_the_flag(self):
        cases = [("barline scrap 4x6, Litolff p4 tile 2", self.ink(4, 6, 16.25), "accidentalFlat"),
                 ("tremolo slash 19x12, Litolff p2 tile 7", self.ink(19, 12, 16.25), "accidentalSharp"),
                 ("stem tip 5x10, Litolff p4 tile 11", self.ink(5, 10, 16.25), "accidentalNatural"),
                 ("a flat's bowl alone 29x40, Brahms p25 tile 12", self.ink(29, 40, 27.55), "accidentalFlat")]
        for name, s, cls in cases:
            with _Flag(None):
                self.assertTrue(self.owned(s, cls).claimed, name + ": the fault, flag OFF")
            with _Flag("1"):
                o = self.owned(s, cls)
                self.assertFalse(o.claimed, name)
                self.assertTrue(any(str(c["why"]).startswith("not_glyph_sized") for c in o.candidates), name)

    def test_the_four_real_ones_stay_whole(self):
        real = [("Brahms sharp 33x88 tile 3", self.ink(33, 88, 27.55), "accidentalSharp"),
                ("Brahms natural 27x90 tile 4", self.ink(27, 90, 27.55), "accidentalNatural"),
                ("Brahms natural 29x89 tile 5", self.ink(29, 89, 27.55), "accidentalNatural"),
                ("Litolff natural 10x50 tile 8", self.ink(10, 50, 16.25), "accidentalNatural"),
                ("a Breitkopf natural 10% over the font", self.ink(30, 82, 27.55), "accidentalNatural")]
        for name, s, cls in real:
            with _Flag("1"):
                self.assertEqual(self.owned(s, cls).family, "accidental", name)

    def test_a_box_over_several_pieces_and_a_class_without_a_size_are_not_judged(self):
        a, b = self.ink(4, 6, 16.25, ordinal=0), self.ink(5, 8, 16.25, ordinal=1)
        acc = SO.Claim("a", "accidental", "accidentalFlat", covers=(0, 1))
        key = SO.Claim("k", "accidental", "keyFlat", covers=(0,))
        with _Flag("1"):
            self.assertEqual(SO.accidental_not_whole([a, b], [acc]), {})            # the old fragment case, unchanged
            self.assertEqual(SO.accidental_not_whole([a], [key]), {})               # no glyph size for a key mark

    def test_merged_pieces_still_too_small_for_the_sign_stay_cut(self):
        pcs = [piece("vertical", 100, 100, 2, 14), piece("blob", 102, 108, 12, 14)]       # a bowl and a short stem: 0.9 x 1.4 sp, a flat is 2.5 tall
        refused = {}
        out, _j, parts = SM.merge_accidentals(pcs, [], SP, [((99.0, 99.0, 116.0, 124.0), "accidentalFlat")], [], refused)
        self.assertEqual(parts, {})
        self.assertEqual(len(out), 2)
        self.assertEqual(refused.get("accidental_not_glyph_sized"), 1)


if __name__ == "__main__":
    unittest.main()
