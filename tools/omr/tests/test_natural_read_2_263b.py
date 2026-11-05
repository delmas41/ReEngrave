"""ROADMAP 2.263b (flag OMR_NATURAL_READ, default ON, deny-list; Sean 2026-11-04): a natural read from its two staggered stems at stagger margin
>= 0.25 is READ; flats, sharps and `unclear` never are; flag off changes nothing. Every control below can fail."""
import os
import unittest
from unittest import mock

from tools.omr.staged import accidental_family as AF


def _on():
    return mock.patch.dict(os.environ, {AF.NATURAL_READ_ENV: "1"})


def _off():
    return mock.patch.dict(os.environ, {AF.NATURAL_READ_ENV: "0"})


def _unset():
    env = dict(os.environ)
    env.pop(AF.NATURAL_READ_ENV, None)
    return mock.patch.dict(os.environ, env, clear=True)


class NaturalRead(unittest.TestCase):
    def test_natural_at_the_bar_is_read_with_the_flag_on(self):
        with _on():
            self.assertTrue(AF.reads(0.25, "natural"))
            self.assertTrue(AF.reads(0.9, "natural"))
            self.assertFalse(AF.reads(0.2499, "natural"))
            self.assertFalse(AF.reads(None, "natural"))

    def test_flat_sharp_unclear_never_read(self):
        with _on():
            for t in ("flat", "sharp", "unclear", None, "doubleflat"):
                for m in (0.0, 0.25, 0.9, 5.0):
                    self.assertFalse(AF.reads(m, t), (t, m))

    def test_default_is_on_and_deny_list_turns_it_off(self):
        with _unset():
            self.assertTrue(AF.natural_read_enabled())
            self.assertTrue(AF.reads(0.9, "natural"))
        for v in ("0", "false", "no", "off", "OFF"):
            with mock.patch.dict(os.environ, {AF.NATURAL_READ_ENV: v}):
                self.assertFalse(AF.natural_read_enabled(), v)

    def test_explicit_zero_is_off_unchanged(self):
        with _off():
            self.assertFalse(AF.natural_read_enabled())
            for t in ("natural", "flat", "sharp", "unclear", None):
                self.assertFalse(AF.reads(0.9, t))

    def test_unclear_with_a_margin_is_still_guessed(self):
        fam = {"type": "unclear", "margin": 0.9, "candidates": ["natural", "flat"], "detector_class": "accidentalNatural",
               "detector_type": "natural"}
        self.assertIsNotNone(AF.guess_of(fam))
        with _on():
            self.assertFalse(AF.reads(fam["margin"], fam["type"]))

    def test_the_control_can_fail(self):
        # a general bar set low would let a flat through: proves the type check, not the margin, stops it
        with _on(), mock.patch.object(AF, "READ_MARGIN", 0.1):
            self.assertTrue(AF.reads(0.5, "flat"))
            self.assertFalse(AF.reads(0.5, "unclear"))


if __name__ == "__main__":
    unittest.main()
